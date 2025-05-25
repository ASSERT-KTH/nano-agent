#!/usr/bin/env python3

import json
import argparse
from pathlib import Path

def load_baseline(name):
    """Load a baseline file."""
    baseline_file = Path(__file__).parent / "data" / "baselines" / f"{name}.json"
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline not found: {name}")
    return json.loads(baseline_file.read_text())

def compare_baselines(baseline1_name, baseline2_name):
    """Compare two baselines and show biggest differences."""
    
    # Load both baselines
    baseline1 = load_baseline(baseline1_name)
    baseline2 = load_baseline(baseline2_name)
    
    print("🔍 Baseline Comparison")
    print("=" * 50)
    print(f"Baseline 1: {baseline1['name']}")
    print(f"Baseline 2: {baseline2['name']}")
    print()
    
    # Overall metrics comparison
    m1 = baseline1["metrics"]
    m2 = baseline2["metrics"]
    
    print("📊 Overall Metrics:")
    print(f"Success Rate:    {m1['success_rate']:.3f} → {m2['success_rate']:.3f} ({m2['success_rate'] - m1['success_rate']:+.3f})")
    print(f"Avg Similarity:  {m1['avg_similarity']:.3f} → {m2['avg_similarity']:.3f} ({m2['avg_similarity'] - m1['avg_similarity']:+.3f})")
    print(f"Avg Tokens:      {m1['avg_tokens']:.0f} → {m2['avg_tokens']:.0f} ({m2['avg_tokens'] - m1['avg_tokens']:+.0f})")
    print(f"Avg Tools:       {m1['avg_tools']:.1f} → {m2['avg_tools']:.1f} ({m2['avg_tools'] - m1['avg_tools']:+.1f})")
    print()
    
    # Per-problem comparison
    problems1 = baseline1["metrics"]["per_problem_stats"]
    problems2 = baseline2["metrics"]["per_problem_stats"]
    
    print("🔍 Per-Problem Analysis:")
    print("-" * 80)
    
    differences = []
    
    for problem_id in problems1.keys():
        if problem_id in problems2:
            p1 = problems1[problem_id]
            p2 = problems2[problem_id]
            
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
    
    # Sort by biggest success rate change (absolute)
    differences.sort(key=lambda x: abs(x["success_diff"]), reverse=True)
    
    print("Ranked by Success Rate Change:")
    print()
    
    for i, diff in enumerate(differences, 1):
        problem_id = diff["problem_id"]
        p1, p2 = diff["p1"], diff["p2"]
        
        print(f"{i}. {problem_id}")
        print(f"   Success Rate:  {p1['success_rate']:.3f} → {p2['success_rate']:.3f} ({diff['success_diff']:+.3f})")
        print(f"   Similarity:    {p1['avg_similarity']:.3f} → {p2['avg_similarity']:.3f} ({diff['similarity_diff']:+.3f})")
        print(f"   Tokens:        {p1['avg_tokens']:.0f} → {p2['avg_tokens']:.0f} ({diff['token_diff']:+.0f})")
        print(f"   Tools:         {p1['avg_tools']:.1f} → {p2['avg_tools']:.1f} ({diff['tool_diff']:+.1f})")
        print()
    
    # Find biggest improvements and regressions
    print("🎯 Biggest Changes:")
    print("-" * 40)
    
    biggest_improvement = max(differences, key=lambda x: x["success_diff"])
    biggest_regression = min(differences, key=lambda x: x["success_diff"])
    
    if biggest_improvement["success_diff"] > 0:
        print(f"📈 Biggest Improvement: {biggest_improvement['problem_id']}")
        print(f"   Success: {biggest_improvement['p1']['success_rate']:.3f} → {biggest_improvement['p2']['success_rate']:.3f} (+{biggest_improvement['success_diff']:.3f})")
        print()
    
    if biggest_regression["success_diff"] < 0:
        print(f"📉 Biggest Regression: {biggest_regression['problem_id']}")
        print(f"   Success: {biggest_regression['p1']['success_rate']:.3f} → {biggest_regression['p2']['success_rate']:.3f} ({biggest_regression['success_diff']:.3f})")
        print()
    
    # Token usage analysis
    print("💰 Token Usage Changes:")
    print("-" * 30)
    biggest_token_reduction = min(differences, key=lambda x: x["token_diff"])
    biggest_token_increase = max(differences, key=lambda x: x["token_diff"])
    
    print(f"Biggest Token Reduction: {biggest_token_reduction['problem_id']}")
    print(f"   {biggest_token_reduction['p1']['avg_tokens']:.0f} → {biggest_token_reduction['p2']['avg_tokens']:.0f} ({biggest_token_reduction['token_diff']:+.0f})")
    print()
    
    print(f"Biggest Token Increase: {biggest_token_increase['problem_id']}")
    print(f"   {biggest_token_increase['p1']['avg_tokens']:.0f} → {biggest_token_increase['p2']['avg_tokens']:.0f} ({biggest_token_increase['token_diff']:+.0f})")

def main():
    parser = argparse.ArgumentParser(description="Compare two SWE-Bench baselines")
    parser.add_argument("--baseline1", default="nano_1.1.0_70e60379_lite", 
                       help="First baseline to compare (default: nano_1.1.0_70e60379_lite)")
    parser.add_argument("--baseline2", default="nano_2.0.0_d79af850_lite",
                       help="Second baseline to compare (default: nano_2.0.0_d79af850_lite)")
    
    args = parser.parse_args()
    
    try:
        compare_baselines(args.baseline1, args.baseline2)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        
        # Show available baselines
        baselines_dir = Path(__file__).parent / "data" / "baselines"
        if baselines_dir.exists():
            available = [f.stem for f in baselines_dir.glob("*.json")]
            print(f"Available baselines: {', '.join(available) if available else 'none'}")

if __name__ == "__main__":
    main() 