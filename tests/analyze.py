#!/usr/bin/env python3

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


def load_all_baselines(baselines_dir: Path) -> Dict[str, dict]:
    """Load all baseline files from the directory."""
    baselines = {}
    for baseline_file in baselines_dir.glob("*.json"):
        try:
            data = json.loads(baseline_file.read_text())
            baselines[baseline_file.stem] = data
        except Exception as e:
            print(f"⚠️  Skipping {baseline_file.name}: {e}")
    return baselines


def parse_baseline_name(name: str) -> Dict[str, str]:
    """Parse baseline name into components."""
    # Expected format: nano_3.1.1_47721852_lite_gpt-4.1-mini
    pattern = r"nano_([^_]+)_([^_]+)_([^_]+)_(.+)"
    match = re.match(pattern, name)
    
    if match:
        version, commit_id, test_set, model = match.groups()
        return {
            "version": version,
            "commit_id": commit_id,
            "test_set": test_set,
            "model": model,
            "provider": model.split("-")[0] if "-" in model else "unknown"
        }
    else:
        # Fallback parsing
        parts = name.split("_")
        return {
            "version": parts[1] if len(parts) > 1 else "unknown",
            "commit_id": parts[2] if len(parts) > 2 else "unknown", 
            "test_set": parts[3] if len(parts) > 3 else "unknown",
            "model": "_".join(parts[4:]) if len(parts) > 4 else "unknown",
            "provider": "unknown"
        }


def group_baselines(baselines: Dict[str, dict]) -> Dict[Tuple[str, str], List[Tuple[str, dict]]]:
    """Group baselines by (version, model) tuple."""
    groups = defaultdict(list)
    
    for name, data in baselines.items():
        parsed = parse_baseline_name(name)
        key = (parsed["version"], parsed["model"])
        groups[key].append((name, data))
    
    # Sort within each group by creation time
    for key in groups:
        groups[key].sort(key=lambda x: x[1].get("created_at", 0))
    
    return dict(groups)


def format_timestamp(timestamp: float) -> str:
    """Format timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def print_group_summary(groups: Dict[Tuple[str, str], List[Tuple[str, dict]]], 
                       show_details: bool = False, 
                       sort_by: str = "version") -> None:
    """Print summary of baseline groups."""
    
    # Sort groups
    if sort_by == "version":
        sorted_groups = sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))
    elif sort_by == "model":
        sorted_groups = sorted(groups.items(), key=lambda x: (x[0][1], x[0][0]))
    elif sort_by == "performance":
        sorted_groups = sorted(groups.items(), 
                             key=lambda x: max(baseline_data["metrics"]["success_rate"] for _, baseline_data in x[1]), 
                             reverse=True)
    else:
        sorted_groups = list(groups.items())
    
    print(f"📊 Found {len(groups)} baseline groups across {sum(len(baselines) for baselines in groups.values())} total baselines\n")
    
    for (version, model), baselines in sorted_groups:
        latest = baselines[-1][1]  # Most recent baseline in group
        metrics = latest["metrics"]
        
        print(f"🔸 nano v{version} + {model}")
        print(f"   📈 Success: {metrics['success_rate']:.3f} | Similarity: {metrics['avg_similarity']:.3f} ({metrics.get('total_problems', '?')} problems)")
        print(f"   💰 Tokens: {metrics['avg_tokens']:.0f}±{metrics.get('tokens_std', 0):.0f}")
        print(f"   🔧 Tools: {metrics['avg_tools']:.1f}±{metrics.get('tools_std', 0):.1f}")
        print(f"   📅 Count: {len(baselines)} baseline{'s' if len(baselines) > 1 else ''}")
        
        if show_details and len(baselines) > 1:
            print(f"   📜 History:")
            for name, data in baselines:
                parsed = parse_baseline_name(name)
                m = data["metrics"]
                timestamp = format_timestamp(data.get("created_at", 0))
                print(f"      {parsed['commit_id'][:8]} {timestamp} → {m['success_rate']:.3f} success, {m['avg_similarity']:.3f} similarity")
        
        print()


def compare_across_models(groups: Dict[Tuple[str, str], List[Tuple[str, dict]]], 
                         version: str) -> None:
    """Compare performance across different models for a specific version."""
    version_groups = {k: v for k, v in groups.items() if k[0] == version}
    
    if not version_groups:
        print(f"❌ No baselines found for version {version}")
        return
    
    print(f"🏆 Model comparison for nano v{version}")
    print()
    
    model_scores = []
    for (_, model), baselines in version_groups.items():
        latest = baselines[-1][1]
        metrics = latest["metrics"]
        model_scores.append((
            model,
            metrics["success_rate"],
            metrics["avg_similarity"],
            metrics["avg_tokens"],
            metrics["avg_tools"],
            len(baselines)
        ))
    
    # Sort by success rate
    model_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'Model':<25} {'Success':<7} {'Similar':<7} {'Tokens':<7} {'Tools':<5} {'Count':<5}")
    print("-" * 65)
    
    for model, success, similarity, tokens, tools, count in model_scores:
        print(f"{model:<25} {success:.3f}   {similarity:.3f}   {tokens:>5.0f}   {tools:>3.1f}   {count:>3}")


def show_version_evolution(groups: Dict[Tuple[str, str], List[Tuple[str, dict]]], 
                          model: str) -> None:
    """Show how performance evolved across versions for a specific model."""
    model_groups = {k: v for k, v in groups.items() if k[1] == model}
    
    if not model_groups:
        print(f"❌ No baselines found for model {model}")
        return
    
    print(f"📈 Version evolution for {model}")
    print()
    
    version_scores = []
    for (version, _), baselines in model_groups.items():
        latest = baselines[-1][1]
        metrics = latest["metrics"]
        version_scores.append((
            version,
            metrics["success_rate"],
            metrics["avg_similarity"],
            metrics["avg_tokens"],
            metrics["avg_tools"],
            latest.get("created_at", 0)
        ))
    
    # Sort by version (semantic sort would be better but this works for most cases)
    version_scores.sort(key=lambda x: x[0])
    
    print(f"{'Version':<8} {'Success':<7} {'Similar':<7} {'Tokens':<7} {'Tools':<5} {'Date':<10}")
    print("-" * 55)
    
    for version, success, similarity, tokens, tools, timestamp in version_scores:
        date_str = format_timestamp(timestamp)[:10]  # Just date part
        print(f"{version:<8} {success:.3f}   {similarity:.3f}   {tokens:>5.0f}   {tools:>3.1f}   {date_str}")


def find_top_performers(groups: Dict[Tuple[str, str], List[Tuple[str, dict]]], 
                       metric: str = "success_rate", 
                       direction: str = "highest") -> None:
    """Find top performing baselines by specified metric."""
    all_baselines = []
    
    for (version, model), baselines in groups.items():
        for name, data in baselines:
            metrics = data["metrics"]
            all_baselines.append((
                name,
                version,
                model,
                metrics.get(metric, 0),
                metrics["success_rate"],
                metrics["avg_similarity"],
                metrics["avg_tokens"],
                metrics["avg_tools"]
            ))
    
    # Sort by the specified metric
    reverse_sort = (direction == "highest")
    all_baselines.sort(key=lambda x: x[3], reverse=reverse_sort)
    
    direction_emoji = "🔝" if direction == "highest" else "🔻"
    print(f"{direction_emoji} Top 10 {direction} by {metric}")
    print()
    print(f"{'Baseline':<35} {'Ver':<5} {metric.title():<8} {'Success':<7} {'Similar':<7} {'Tokens':<7} {'Tools':<5}")
    print("-" * 85)
    
    for name, version, model, metric_val, success, similarity, tokens, tools in all_baselines[:10]:
        display_name = name[:32] + "..." if len(name) > 35 else name
        print(f"{display_name:<35} v{version:<4} {metric_val:>7.3f}   {success:.3f}   {similarity:.3f}   {tokens:>5.0f}   {tools:>3.1f}")


def search_baselines(baselines: Dict[str, dict], query: str) -> List[Tuple[str, dict]]:
    """Search baselines by name pattern."""
    pattern = re.compile(query, re.IGNORECASE)
    matches = []
    
    for name, data in baselines.items():
        if pattern.search(name):
            matches.append((name, data))
    
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Analyze nano-agent baseline performance across versions and models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                            # Show summary of all baselines
  %(prog)s --details                  # Show detailed history for each group
  %(prog)s --compare-models 3.1.1     # Compare models for specific version
  %(prog)s --evolution gpt-4.1-mini   # Show version evolution for model
  %(prog)s --highest success_rate      # Show highest success rates
  %(prog)s --highest avg_similarity    # Show highest similarity scores
  %(prog)s --lowest avg_tokens         # Show most token-efficient baselines
  %(prog)s --lowest avg_tools          # Show least tool usage
  %(prog)s --search "deepseek"         # Search baselines by pattern
  %(prog)s --sort performance          # Sort groups by performance
        """
    )
    
    parser.add_argument("--details", action="store_true", 
                       help="Show detailed history for each baseline group")
    parser.add_argument("--compare-models", metavar="VERSION",
                       help="Compare performance across models for specific version")
    parser.add_argument("--evolution", metavar="MODEL", 
                       help="Show version evolution for specific model")
    parser.add_argument("--highest", metavar="METRIC", 
                       help="Show top 10 highest by metric (success_rate, avg_similarity, avg_tokens, avg_tools)")
    parser.add_argument("--lowest", metavar="METRIC", 
                       help="Show top 10 lowest by metric (success_rate, avg_similarity, avg_tokens, avg_tools)")
    parser.add_argument("--search", metavar="PATTERN",
                       help="Search baselines by name pattern (regex)")
    parser.add_argument("--sort", choices=["version", "model", "performance"], 
                       default="version", help="Sort groups by criteria")
    parser.add_argument("--baselines-dir", type=Path, 
                       default=Path(__file__).parent / "data" / "baselines",
                       help="Directory containing baseline files")
    
    args = parser.parse_args()
    
    if not args.baselines_dir.exists():
        print(f"❌ Baselines directory not found: {args.baselines_dir}")
        return
    
    # Load all baselines
    baselines = load_all_baselines(args.baselines_dir)
    if not baselines:
        print(f"❌ No baseline files found in {args.baselines_dir}")
        return
    
    # Handle search
    if args.search:
        matches = search_baselines(baselines, args.search)
        if matches:
            print(f"🔍 Found {len(matches)} baselines matching '{args.search}':")
            print()
            for name, data in matches:
                parsed = parse_baseline_name(name)
                metrics = data["metrics"]
                timestamp = format_timestamp(data.get("created_at", 0))
                print(f"  {name}")
                print(f"    📈 {metrics['success_rate']:.3f} success, {metrics['avg_tokens']:.0f} tokens")
                print(f"    📅 {timestamp} (nano v{parsed['version']})")
                print()
        else:
            print(f"❌ No baselines found matching '{args.search}'")
        return
    
    # Group baselines
    groups = group_baselines(baselines)
    
    # Handle specific analysis modes
    if args.compare_models:
        compare_across_models(groups, args.compare_models)
    elif args.evolution:
        show_version_evolution(groups, args.evolution)
    elif args.highest:
        find_top_performers(groups, args.highest, "highest")
    elif args.lowest:
        find_top_performers(groups, args.lowest, "lowest")
    else:
        # Default: show group summary
        print_group_summary(groups, args.details, args.sort)


if __name__ == "__main__":
    main()