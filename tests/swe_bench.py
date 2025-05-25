import uuid
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from nano import Agent, __version__
from utils import clone_repo_at_commit, clean_repo_dir, unified_diff_similarity, get_git_commit_hash

# Minimal logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

TEST_DATA_DIR = Path(__file__).parent / "data"
BASELINES_DIR = TEST_DATA_DIR / "baselines"

def run_single_problem(problem: Dict[str, Any], agent_config: Dict[str, Any], repetition: int = 0) -> Dict[str, Any]:
    """Run a single SWE-Bench problem and return results."""
    instance_id = problem["instance_id"]
    logging.info(f"Running {instance_id} (rep {repetition + 1})")
    
    agent = Agent(**agent_config)
    repo_path = None
    
    try:
        # Clone and run
        repo_path = clone_repo_at_commit(
            problem["git_repo_handle"], 
            problem["git_commit"]
        )
        
        generated_diff = agent.run(
            task=problem["problem_description"], 
            repo_root=repo_path
        )
        
        # Calculate similarity
        similarity = unified_diff_similarity(problem["patch"], generated_diff)
        success = similarity > 0.3
        
        result = {
            "instance_id": instance_id,
            "repetition": repetition,
            "success": success,
            "similarity": similarity,
            "token_usage": agent.token_usage,
            "tool_usage": agent.tool_usage,
        }
        
    except Exception as e:
        logging.warning(f"Failed {instance_id} (rep {repetition + 1}): {e}")
        result = {
            "instance_id": instance_id,
            "repetition": repetition,
            "success": False,
            "similarity": 0.0,
            "token_usage": 0,
            "tool_usage": 0,
            "error": str(e)
        }
    
    finally:
        if repo_path:
            clean_repo_dir(repo_path)
    
    return result

def run_problems_parallel(problems: List[Dict], agent_config: Dict, max_workers: int = 2, repetitions: int = 1) -> List[Dict]:
    """Run problems in parallel using ThreadPoolExecutor."""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs (problem x repetition combinations)
        futures = []
        for problem in problems:
            for rep in range(repetitions):
                future = executor.submit(run_single_problem, problem, agent_config, rep)
                futures.append(future)
        
        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logging.error(f"Future failed: {e}")
                results.append({
                    "instance_id": "unknown",
                    "repetition": 0,
                    "success": False,
                    "similarity": 0.0,
                    "token_usage": 0,
                    "tool_usage": 0,
                    "error": str(e)
                })
    
    return results

def compute_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Compute aggregate metrics with support for multiple repetitions."""
    if not results:
        return {}
    
    # Group results by instance_id
    by_instance = {}
    for result in results:
        instance_id = result["instance_id"]
        if instance_id not in by_instance:
            by_instance[instance_id] = []
        by_instance[instance_id].append(result)
    
    # Compute per-problem statistics
    per_problem_stats = {}
    for instance_id, instance_results in by_instance.items():
        successes = [r["success"] for r in instance_results]
        similarities = [r["similarity"] for r in instance_results]
        tokens = [r["token_usage"] for r in instance_results if r["token_usage"] > 0]
        tools = [r["tool_usage"] for r in instance_results if r["tool_usage"] > 0]
        
        per_problem_stats[instance_id] = {
            "repetitions": len(instance_results),
            "success_rate": sum(successes) / len(successes),
            "success_std": statistics.stdev(successes) if len(successes) > 1 else 0.0,
            "avg_similarity": statistics.mean(similarities),
            "similarity_std": statistics.stdev(similarities) if len(similarities) > 1 else 0.0,
            "avg_tokens": statistics.mean(tokens) if tokens else 0,
            "tokens_std": statistics.stdev(tokens) if len(tokens) > 1 else 0.0,
            "avg_tools": statistics.mean(tools) if tools else 0,
            "tools_std": statistics.stdev(tools) if len(tools) > 1 else 0.0,
        }
    
    # Compute global statistics
    # Method 1: Average across all individual runs (traditional)
    all_successes = [r["success"] for r in results]
    all_similarities = [r["similarity"] for r in results]
    all_tokens = [r["token_usage"] for r in results if r["token_usage"] > 0]
    all_tools = [r["tool_usage"] for r in results if r["tool_usage"] > 0]
    
    global_run_based = {
        "success_rate": statistics.mean(all_successes),
        "success_std": statistics.stdev(all_successes) if len(all_successes) > 1 else 0.0,
        "avg_similarity": statistics.mean(all_similarities),
        "similarity_std": statistics.stdev(all_similarities) if len(all_similarities) > 1 else 0.0,
        "avg_tokens": statistics.mean(all_tokens) if all_tokens else 0,
        "tokens_std": statistics.stdev(all_tokens) if len(all_tokens) > 1 else 0.0,
        "avg_tools": statistics.mean(all_tools) if all_tools else 0,
        "tools_std": statistics.stdev(all_tools) if len(all_tools) > 1 else 0.0,
    }
    
    # Method 2: Average across per-problem averages (more robust to repetition imbalance)
    problem_success_rates = [stats["success_rate"] for stats in per_problem_stats.values()]
    problem_similarities = [stats["avg_similarity"] for stats in per_problem_stats.values()]
    problem_tokens = [stats["avg_tokens"] for stats in per_problem_stats.values() if stats["avg_tokens"] > 0]
    problem_tools = [stats["avg_tools"] for stats in per_problem_stats.values() if stats["avg_tools"] > 0]
    
    global_problem_based = {
        "success_rate": statistics.mean(problem_success_rates),
        "success_std": statistics.stdev(problem_success_rates) if len(problem_success_rates) > 1 else 0.0,
        "avg_similarity": statistics.mean(problem_similarities),
        "similarity_std": statistics.stdev(problem_similarities) if len(problem_similarities) > 1 else 0.0,
        "avg_tokens": statistics.mean(problem_tokens) if problem_tokens else 0,
        "tokens_std": statistics.stdev(problem_tokens) if len(problem_tokens) > 1 else 0.0,
        "avg_tools": statistics.mean(problem_tools) if problem_tools else 0,
        "tools_std": statistics.stdev(problem_tools) if len(problem_tools) > 1 else 0.0,
    }
    
    # Determine number of repetitions
    repetitions_per_problem = [len(instance_results) for instance_results in by_instance.values()]
    avg_repetitions = statistics.mean(repetitions_per_problem)
    
    return {
        # Use problem-based as primary metrics (more robust)
        "success_rate": global_problem_based["success_rate"],
        "success_std": global_problem_based["success_std"],
        "avg_similarity": global_problem_based["avg_similarity"],
        "similarity_std": global_problem_based["similarity_std"],
        "avg_tokens": global_problem_based["avg_tokens"],
        "tokens_std": global_problem_based["tokens_std"],
        "avg_tools": global_problem_based["avg_tools"],
        "tools_std": global_problem_based["tools_std"],
        
        # Additional metadata
        "timestamp": time.time(),
        "git_commit": get_git_commit_hash(),
        "nano_version": __version__,
        "total_problems": len(by_instance),
        "total_runs": len(results),
        "avg_repetitions": avg_repetitions,
        
        # Alternative metrics for comparison
        "global_run_based": global_run_based,
        "global_problem_based": global_problem_based,
        "per_problem_stats": per_problem_stats,
    }

def build_config_snapshot(agent_config: Dict, test_set: str, repetitions: int, max_workers: int) -> Dict:
    """Build a comprehensive configuration snapshot for reproducibility."""
    return {
        # Core nano info
        "nano_version": __version__,
        "git_commit": get_git_commit_hash(),
        
        # Test parameters
        "test_set": test_set,
        "repetitions": repetitions,
        "max_workers": max_workers,
        
        # Agent configuration
        "model": agent_config["model"],
        "token_limit": agent_config["token_limit"],
        "tool_limit": agent_config["tool_limit"],
    }

def save_baseline(name: str, results: List[Dict], metrics: Dict, config_snapshot: Dict):
    """Save a baseline."""
    BASELINES_DIR.mkdir(exist_ok=True)
    
    baseline_data = {
        "name": name,
        "created_at": time.time(),
        "metrics": metrics,
        "results": results,
        "config": config_snapshot,
    }
    
    baseline_file = BASELINES_DIR / f"{name}.json"
    baseline_file.write_text(json.dumps(baseline_data, indent=2))
    logging.info(f"Baseline saved: {baseline_file}")

def load_baseline(name: str) -> Dict:
    """Load a baseline."""
    baseline_file = BASELINES_DIR / f"{name}.json"
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline not found: {name}")
    return json.loads(baseline_file.read_text())

def compare_baselines(current: Dict, baseline: Dict, current_config: Dict = None):
    """Compare current metrics to baseline."""
    
    current_m = current
    baseline_m = baseline["metrics"]
    
    print(f"  First:  {baseline_m.get('total_problems', '?')} problems, {baseline_m.get('avg_repetitions', 1):.1f} avg reps")
    print(f"  Second: {current_m.get('total_problems', '?')} problems, {current_m.get('avg_repetitions', 1):.1f} avg reps")
    
    # Compare configurations
    baseline_config = baseline.get("config") or baseline.get("agent_config")
    if current_config and baseline_config:
        print(f"\n  ⚙️  Configuration changes:")
        
        config_params = ["nano_version", "git_commit", "model", "test_set", "repetitions", "token_limit", "tool_limit", "max_workers"]
        
        for param in config_params:
            base_val = baseline_config.get(param, "missing")
            curr_val = current_config.get(param, "missing")
            
            if curr_val != base_val:
                # Show short git hash
                if param == "git_commit":
                    base_val = str(base_val)[:8] if base_val != "missing" else base_val
                    curr_val = str(curr_val)[:8] if curr_val != "missing" else curr_val
                
                print(f"    {param:12}: {base_val} → {curr_val}")
    
    # Show metrics comparison
    print(f"\n  📈 Metrics:")
    has_std = "success_std" in current_m
    
    for metric in ["success_rate", "avg_similarity", "avg_tokens", "avg_tools"]:
        base_val = baseline_m[metric]
        curr_val = current_m[metric]
        diff = curr_val - base_val
        
        base_std = baseline_m.get(f"{metric.replace('avg_', '')}_std", 0)
        if base_std > 0:
            base_str = f"{base_val:.3f}±{base_std:.3f}"
        else:
            base_str = f"{base_val:.3f}"
        
        if has_std:
            curr_std = current_m.get(f"{metric.replace('avg_', '')}_std", 0)
            curr_str = f"{curr_val:.3f}±{curr_std:.3f}"
        else:
            curr_str = f"{curr_val:.3f}"
        
        print(f"    {metric:15}: {base_str} → {curr_str} ({diff:+.3f})")
    
    # Per-problem analysis
    baseline_problems = baseline_m.get("per_problem_stats", {})
    current_problems = current_m.get("per_problem_stats", {})
    
    if baseline_problems and current_problems:
        print(f"\n  🔍 Per-problem analysis:")
        
        differences = []
        for problem_id in baseline_problems.keys():
            if problem_id in current_problems:
                p1 = baseline_problems[problem_id]
                p2 = current_problems[problem_id]
                
                success_diff = p2["success_rate"] - p1["success_rate"]
                similarity_diff = p2["avg_similarity"] - p1["avg_similarity"]
                token_diff = p2["avg_tokens"] - p1["avg_tokens"]
                tool_diff = p2["avg_tools"] - p1["avg_tools"]
                
                differences.append({
                    "problem_id": problem_id,
                    "success_diff": success_diff,
                    "similarity_diff": similarity_diff,
                    "token_diff": token_diff,
                    "tool_diff": tool_diff,
                    "p1": p1,
                    "p2": p2
                })
        
        if differences:
            # Sort by biggest success rate change (absolute)
            differences.sort(key=lambda x: abs(x["success_diff"]), reverse=True)
            
            # Show top 3 biggest changes
            print(f"    Top changes by success rate:")
            for i, diff in enumerate(differences[:3], 1):
                problem_id = diff["problem_id"]
                p1, p2 = diff["p1"], diff["p2"]
                
                print(f"    {i}. {problem_id}")
                print(f"       Success: {p1['success_rate']:.3f} → {p2['success_rate']:.3f} ({diff['success_diff']:+.3f})")
                print(f"       Similarity: {p1['avg_similarity']:.3f} → {p2['avg_similarity']:.3f} ({diff['similarity_diff']:+.3f})")
                print(f"       Tokens: {p1['avg_tokens']:.0f} → {p2['avg_tokens']:.0f} ({diff['token_diff']:+.0f})")
            
            # Find biggest improvements and regressions
            biggest_improvement = max(differences, key=lambda x: x["success_diff"])
            biggest_regression = min(differences, key=lambda x: x["success_diff"])
            
            if biggest_improvement["success_diff"] > 0:
                print(f"\n    📈 Biggest improvement: {biggest_improvement['problem_id']}")
                print(f"       Success: {biggest_improvement['p1']['success_rate']:.3f} → {biggest_improvement['p2']['success_rate']:.3f} (+{biggest_improvement['success_diff']:.3f})")
            
            if biggest_regression["success_diff"] < 0:
                print(f"\n    📉 Biggest regression: {biggest_regression['problem_id']}")
                print(f"       Success: {biggest_regression['p1']['success_rate']:.3f} → {biggest_regression['p2']['success_rate']:.3f} ({biggest_regression['success_diff']:.3f})")
            
            # Token usage extremes
            biggest_token_reduction = min(differences, key=lambda x: x["token_diff"])
            biggest_token_increase = max(differences, key=lambda x: x["token_diff"])
            
            print(f"\n    💰 Token usage:")
            print(f"       Biggest reduction: {biggest_token_reduction['problem_id']} ({biggest_token_reduction['token_diff']:+.0f})")
            print(f"       Biggest increase: {biggest_token_increase['problem_id']} ({biggest_token_increase['token_diff']:+.0f})")

def generate_baseline_name(test_set: str) -> str:
    """Generate a baseline name."""
    id = str(uuid.uuid4())[:8]
    return f"nano_{__version__}_{id}_{test_set}"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Nano on SWE-Bench problems")
    parser.add_argument("--model", default="openrouter/openai/gpt-4.1-mini", help="Model to test")
    parser.add_argument("--verified", action="store_true", help="Use verified (harder) test set")
    parser.add_argument("--quick", action="store_true", help="Run only 3 problems")
    parser.add_argument("--baseline", action="store_true", help="Save results as a new baseline")
    parser.add_argument("--compare", help="Compare to this baseline")
    parser.add_argument("--token-limit", type=int, default=8192, help="Token limit")
    parser.add_argument("--tool-limit", type=int, default=20, help="Tool limit")
    parser.add_argument("--max-workers", type=int, default=8, help="Max parallel workers")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--repetitions", type=int, default=1, help="Number of repetitions per problem")
    
    args = parser.parse_args()
    
    # Load test data
    test_set = "verified" if args.verified else "lite"
    test_file = TEST_DATA_DIR / f"swe_bench_{test_set}_subset.json"
    problems = json.loads(test_file.read_text())
    
    if args.quick:
        problems = problems[:3]
    
    print(f"🧪 Testing Nano on {len(problems)} SWE-Bench {test_set} problems")
    print(f"Model: {args.model}")
    print(f"Max workers: {args.max_workers}")
    print(f"Repetitions: {args.repetitions}")
    
    # Agent configuration
    agent_config = {
        "model": args.model,
        "token_limit": args.token_limit,
        "tool_limit": args.tool_limit,
        "verbose": args.verbose,
        "log": False,  # Disable internal logging for cleaner output
    }
    
    # Load baseline early to catch errors before running tests
    baseline = None
    if args.compare:
        try:
            baseline = load_baseline(args.compare)
        except FileNotFoundError:
            print(f"\n⚠️  Baseline '{args.compare}' not found")
            if BASELINES_DIR.exists():
                available = [f.stem for f in BASELINES_DIR.glob("*.json")]
                print(f"Available baselines: {', '.join(available) if available else 'none'}")
            return
    
    # Run tests
    start_time = time.time()
    results = run_problems_parallel(problems, agent_config, args.max_workers, args.repetitions)
    elapsed = time.time() - start_time
    
    # Compute and display metrics
    metrics = compute_metrics(results)
    
    print(f"\n📈 Results ({elapsed:.1f}s, {metrics['total_runs']} total runs):")
    
    # Show standard deviations if we have repetitions
    if args.repetitions > 1:
        print(f"Success Rate:    {metrics['success_rate']:.3f} ± {metrics['success_std']:.3f}")
        print(f"Avg Similarity:  {metrics['avg_similarity']:.3f} ± {metrics['similarity_std']:.3f}")
        print(f"Avg Tokens:      {metrics['avg_tokens']:.0f} ± {metrics['tokens_std']:.0f}")
        print(f"Avg Tools:       {metrics['avg_tools']:.1f} ± {metrics['tools_std']:.1f}")
    else:
        print(f"Success Rate:    {metrics['success_rate']:.3f}")
        print(f"Avg Similarity:  {metrics['avg_similarity']:.3f}")
        print(f"Avg Tokens:      {metrics['avg_tokens']:.0f}")
        print(f"Avg Tools:       {metrics['avg_tools']:.1f}")
    
    # Handle baseline operations
    if args.baseline:
        auto_name = generate_baseline_name(test_set)
        config_snapshot = build_config_snapshot(agent_config, test_set, args.repetitions, args.max_workers)
        save_baseline(auto_name, results, metrics, config_snapshot)
        print(f"💾 Auto-saved as baseline: {auto_name}")
    
    if baseline:
        config_snapshot = build_config_snapshot(agent_config, test_set, args.repetitions, args.max_workers)
        print(f"\n📊 Comparison to baseline {baseline.get('name')}:")
        compare_baselines(metrics, baseline, config_snapshot)

if __name__ == "__main__":
    main() 