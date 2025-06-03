#!/usr/bin/env python3

import re
from pathlib import Path
from typing import Dict, List, Tuple

from analyze import load_all_baselines, group_baselines, parse_baseline_name, format_timestamp


def generate_leaderboard_markdown() -> str:
    """Generate leaderboard markdown content."""
    baselines_dir = Path(__file__).parent / "data" / "baselines"
    
    if not baselines_dir.exists():
        return "<!-- No baselines found -->"
    
    baselines = load_all_baselines(baselines_dir)
    if not baselines:
        return "<!-- No baseline files found -->"
    
    # Get all baselines, not grouped
    all_results = []
    for name, data in baselines.items():
        parsed = parse_baseline_name(name)
        metrics = data["metrics"]
        all_results.append({
            "version": parsed["version"],
            "model": parsed["model"],
            "name": name,
            "success_rate": metrics["success_rate"],
            "avg_similarity": metrics["avg_similarity"],
            "avg_test_similarity": metrics.get("avg_test_similarity", 0.0),
            "avg_tokens": metrics["avg_tokens"],
            "avg_tools": metrics["avg_tools"],
            "created_at": data.get("created_at", 0)
        })
    
    # Sort by similarity (most important metric)
    all_results.sort(key=lambda x: x["avg_similarity"], reverse=True)
    
    # Generate markdown
    lines = [
        "## 🏆 Current Leaderboard",
        "",
        "All baseline runs ranked by similarity score:",
        "",
        "| Rank | Version | Model | Similarity | Test Similarity | Tokens | Tools | Date |",
        "|------|---------|-------|------------|-----------------|--------|-------|------|"
    ]
    
    for i, result in enumerate(all_results[:10], 1):
        # Format date
        date_str = format_timestamp(result["created_at"])[:10] if result["created_at"] else "N/A"
        
        # Normalize model name
        model_display = result["model"].lower()
        
        lines.append(
            f"| {i} | v{result['version']} | {model_display} | "
            f"{result['avg_similarity']:.3f} | "
            f"{result['avg_test_similarity']:.3f} | "
            f"{result['avg_tokens']:.0f} | {result['avg_tools']:.1f} | {date_str} |"
        )
    
    lines.extend([
        "",
        f"*Updated automatically - showing top 10 of {len(all_results)} total runs*",
        "",
        "**Key Metrics:**",
        "- **Similarity**: Average patch similarity score (ranked by this)",
        "- **Test Similarity**: Average test patch similarity score (0.000 for older baselines)",
        "- **Tokens**: Average token usage per problem", 
        "- **Tools**: Average tool calls per problem",
        ""
    ])
    
    return "\n".join(lines)


def update_readme_leaderboard() -> bool:
    """Update the leaderboard section in README.md. Returns True if updated."""
    readme_path = Path(__file__).parent.parent / "README.md"
    
    if not readme_path.exists():
        print(f"⚠️  README.md not found at {readme_path}")
        return False
    
    # Read current README
    content = readme_path.read_text()
    
    # Generate new leaderboard
    new_leaderboard = generate_leaderboard_markdown()
    
    # Define markers
    start_marker = "## 🏆 Current Leaderboard"
    end_marker = "## "  # Next section starts with ##
    
    # Find existing leaderboard section
    start_idx = content.find(start_marker)
    
    if start_idx == -1:
        # No existing leaderboard, append to end
        if not content.endswith('\n'):
            content += '\n'
        content += '\n' + new_leaderboard + '\n'
    else:
        # Find end of leaderboard section
        # Look for next ## heading after the leaderboard
        search_from = start_idx + len(start_marker)
        end_idx = content.find(end_marker, search_from)
        
        if end_idx == -1:
            # Leaderboard is at the end of file
            content = content[:start_idx] + new_leaderboard + '\n'
        else:
            # Replace existing leaderboard section
            content = content[:start_idx] + new_leaderboard + '\n' + content[end_idx:]
    
    # Write back to README
    readme_path.write_text(content)
    print(f"✅ Updated leaderboard in {readme_path}")
    return True


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update nano-agent leaderboard in README.md")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Print leaderboard without updating README")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print(generate_leaderboard_markdown())
    else:
        update_readme_leaderboard()


if __name__ == "__main__":
    main()