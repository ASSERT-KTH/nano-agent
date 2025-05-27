import json
import time
import logging
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from nano import Agent, __version__
from utils import clone_repo_at_commit, clean_repo_dir, unified_diff_similarity, get_git_commit_hash
from baseline import load_baseline, save_baseline, generate_baseline_name, build_config_snapshot, compare_baselines

# Minimal logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

TEST_DATA_DIR = Path(__file__).parent / "data"

def run_single_problem(problem: dict, agent_config: dict, repetition: int = 0) -> dict:
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
            "tool_usage": agent.tool_limit - agent.remaining_tool_calls, #agent.tool_usage,
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

def run_problems_parallel(problems: list, agent_config: dict, max_workers: int = 2, repetitions: int = 1) -> list:
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

def compute_metrics(results: list) -> dict:
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

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Nano on SWE-Bench problems")
    parser.add_argument("--model", default=None, help="Model to test (if None, uses localhost)")
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
    
    # Handle nullable model - default to localhost setup
    if args.model is None:
        # Auto-detect model from local vLLM server
        api_base = "http://localhost:8000/v1"
        model = requests.get(f"{api_base}/models").json()["data"][0]["id"]
        print(f"🏠 No model specified, queried localhost and using {model}")
        model = f"hosted_vllm/{model}"
    else:
        model = args.model
        api_base = None
    
    # Load test data
    test_set = "verified" if args.verified else "lite"
    test_file = TEST_DATA_DIR / f"swe_bench_{test_set}_subset.json"
    problems = json.loads(test_file.read_text())
    
    if args.quick:
        problems = problems[:3]
    
    print(f"🧪 Testing Nano on {len(problems)} SWE-Bench {test_set} problems")
    print(f"Model: {model}")
    print(f"Max workers: {args.max_workers}")
    print(f"Repetitions: {args.repetitions}")
    
    # Agent configuration
    agent_config = {
        "model": model,
        "api_base": api_base,
        "token_limit": args.token_limit,
        "tool_limit": args.tool_limit,
        "verbose": args.verbose,
        "thinking": True,
        "temperature": 0.6,   
        "top_k": 20,
        "top_p": 0.95,
        # "min_p": 0.05
        # temp / top_k etc.
    }
    
    # Load baseline early to catch errors before running tests
    baseline = None
    if args.compare:
        try:
            baseline = load_baseline(args.compare)
        except FileNotFoundError:
            print(f"\n⚠️  Baseline '{args.compare}' not found")
            baselines_dir = TEST_DATA_DIR / "baselines"
            if baselines_dir.exists():
                available = [f.stem for f in baselines_dir.glob("*.json")]
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
        auto_name = generate_baseline_name(test_set, model)
        config_snapshot = build_config_snapshot(agent_config, test_set, args.repetitions, args.max_workers)
        save_baseline(auto_name, results, metrics, config_snapshot)
        print(f"💾 Auto-saved as baseline: {auto_name}")
    
    if baseline:
        config_snapshot = build_config_snapshot(agent_config, test_set, args.repetitions, args.max_workers)
        print(f"\n📊 Comparison to baseline {baseline.get('name')}:")
        compare_baselines(metrics, baseline, config_snapshot)

if __name__ == "__main__":
    main() 