#!/usr/bin/env python3

from pathlib import Path

from analyze import load_all_baselines, parse_baseline_name, format_timestamp


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
        config = data["config"]
        
        all_results.append({
            "version": parsed["version"],
            "model": parsed["model"],
            "name": name,
            "success_rate": metrics["success_rate"],
            "avg_similarity": metrics["avg_similarity"],
            "avg_test_similarity": metrics["avg_test_similarity"],
            "avg_tokens": metrics["avg_tokens"],
            "token_limit": config["token_limit"],
            "avg_tools": metrics["avg_tools"],
            "tool_limit": config["tool_limit"],
            "created_at": data["created_at"]
        })
    
    # Sort by similarity (most important metric)
    all_results.sort(key=lambda x: x["avg_similarity"], reverse=True)
    
    # Generate HTML table for precise alignment
    lines = [
        "## 🏆 Current Leaderboard",
        "",
        "All baseline runs ranked by similarity score:",
        "",
        "<table>",
        "<thead>",
        "<tr>",
        "<th>#</th>",
        "<th>Ver</th>", 
        "<th>Model</th>",
        "<th>Code Sim</th>",
        "<th>Test Sim</th>",
        "<th style='text-align: right !important' align='right'>Tokens</th>",
        "<th style='text-align: right !important' align='right'>Tools</th>",
        "</tr>",
        "</thead>",
        "<tbody>"
    ]
    
    for i, result in enumerate(all_results[:10], 1):
        # Format date
        date_str = format_timestamp(result["created_at"])[:10] if result["created_at"] else "N/A"
        
        # Normalize model name
        model_display = result["model"].lower()
        
        # Format numbers
        tokens_used = int(result['avg_tokens'])
        tokens_limit = result['token_limit']
        tools_used = result['avg_tools']
        
        lines.append("<tr>")
        lines.append(f"<td>{i}</td>")
        lines.append(f"<td>v{result['version']}</td>")
        lines.append(f"<td>{model_display}</td>")
        lines.append(f"<td>{result['avg_similarity']:.3f}</td>")
        lines.append(f"<td>{result['avg_test_similarity']:.3f}</td>")
        lines.append(f"<td style='text-align: right !important' align='right'>{tokens_used:,} / {tokens_limit:,}</td>")
        lines.append(f"<td style='text-align: right !important' align='right'>{tools_used:.1f} / {result['tool_limit']}</td>")
        lines.append("</tr>")
    
    lines.extend([
        "</tbody>",
        "</table>"
    ])
    
    lines.extend([
        "",
        f"*Updated automatically - showing top 10 of {len(all_results)} total runs*",
        "",
        "**Note:** Prone to a lot of noise, small test set with few repetitions.",
        "",
        "**Key Metrics:**",
        "- **Code Sim**: Average patch similarity score (ranked by this)",
        "- **Test Sim**: Average test patch similarity score",
        "- **Tokens**: Average tokens used per problem / limit", 
        "- **Tools**: Average tool calls per problem / limit",
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