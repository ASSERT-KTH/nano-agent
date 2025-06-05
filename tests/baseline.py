#!/usr/bin/env python3

import argparse
import json
import time
import logging
import uuid
from pathlib import Path

from nano import __version__
from utils import get_git_commit_hash

def load_baseline(name: str) -> dict:
    """Load a baseline."""
    baselines_dir = Path(__file__).parent / "data" / "baselines"
    baseline_file = baselines_dir / f"{name}.json"
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline not found: {name}")
    return json.loads(baseline_file.read_text())

def save_baseline(name: str, results: list[dict], metrics: dict, config_snapshot: dict):
    """Save a baseline."""
    baselines_dir = Path(__file__).parent / "data" / "baselines"
    baselines_dir.mkdir(exist_ok=True)
    
    baseline_data = {
        "name": name,
        "created_at": time.time(),
        "metrics": metrics,
        "results": results,
        "config": config_snapshot,
    }
    
    baseline_file = baselines_dir / f"{name}.json"
    baseline_file.write_text(json.dumps(baseline_data, indent=2))
    logging.info(f"Baseline saved: {baseline_file}")

def generate_baseline_name(test_set: str, model: str) -> str:
    """Generate a baseline name including model info."""
    # Extract the last part of the model name (e.g., "gpt-4.1-mini" from "openrouter/openai/gpt-4.1-mini")
    model_suffix = model.split("/")[-1]
    id = str(uuid.uuid4())[:8]
    return f"nano_{__version__}_{id}_{test_set}_{model_suffix}"

def build_config_snapshot(agent_config: dict, test_set: str, repetitions: int, max_workers: int) -> dict:
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
        "model": agent_config.get("model", "missing"),
        "api_base": agent_config.get("api_base", "missing"),
        "token_limit": agent_config.get("token_limit", "missing"),
        "tool_limit": agent_config.get("tool_limit", "missing"), 
        "thinking": agent_config.get("thinking", "missing"),
        "temperature": agent_config.get("temperature", "missing"),
        "top_k": agent_config.get("top_k", "missing"),
        "top_p": agent_config.get("top_p", "missing"),
        "min_p": agent_config.get("min_p", "missing"),
    }

def compare_baselines(current: dict, baseline: dict, current_config: dict = None):
    """Compare current metrics to baseline."""
    
    current_m = current
    baseline_m = baseline["metrics"]
    
    print(f"  First:  {baseline_m.get('total_problems', '?')} problems, {baseline_m.get('avg_repetitions', 1):.1f} avg reps")
    print(f"  Second: {current_m.get('total_problems', '?')} problems, {current_m.get('avg_repetitions', 1):.1f} avg reps")
    
    # Compare configurations
    baseline_config = baseline.get("config") or baseline.get("agent_config")
    if current_config and baseline_config:
        print(f"\n  ⚙️  Configuration changes:")
        
        config_params = ["nano_version", "git_commit", "model", "test_set", "repetitions", "token_limit", "tool_limit", "max_workers", "api_base", "temperature", "top_k", "top_p", "min_p"]
        
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
    
    for metric in ["success_rate", "avg_similarity", "avg_test_similarity", "avg_tokens", "avg_tools"]:
        base_val = baseline_m.get(metric, 0.0) if metric == "avg_test_similarity" else baseline_m[metric]
        curr_val = current_m.get(metric, 0.0) if metric == "avg_test_similarity" else current_m[metric]
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

def main():
    parser = argparse.ArgumentParser(description="Compare two SWE-Bench baselines")
    parser.add_argument("baseline1", nargs='?', default="nano_1.1.0_70e60379_lite_gpt-4.1-mini", help="First baseline to compare (default: nano_1.1.0_70e60379_lite_gpt-4.1-mini)")
    parser.add_argument("baseline2", nargs='?', default="nano_2.0.0_d79af850_lite_gpt-4.1-mini", help="Second baseline to compare (default: nano_2.0.0_d79af850_lite_gpt-4.1-mini)")
    
    args = parser.parse_args()
    
    try:
        # Load both baselines
        baseline1 = load_baseline(args.baseline1)
        baseline2 = load_baseline(args.baseline2)
        
        print(f"📊 Comparing baselines:")
        print(f"  {baseline1['name']} vs {baseline2['name']}")
        
        # Use the existing compare_baselines function from swe_bench
        # We'll treat baseline2 as "current" and baseline1 as "baseline"
        compare_baselines(baseline2["metrics"], baseline1, baseline2.get("config"))
        
    except FileNotFoundError as e:
        print(f"⚠️  Error: {e}")
        
        # Show available baselines
        baselines_dir = Path(__file__).parent / "data" / "baselines"
        if baselines_dir.exists():
            available = [f.stem for f in baselines_dir.glob("*.json")]
            print(f"Available baselines: {', '.join(available) if available else 'none'}")

if __name__ == "__main__":
    main() 