#!/usr/bin/env python3
import argparse
from pathlib import Path

from analyze import load_all_baselines, parse_baseline_name


def generate_leaderboard_markdown(test_set: str = "lite") -> str:
    """Generate leaderboard markdown content for a specific test set."""
    baselines_dir = Path(__file__).parent / "data" / "baselines"
    baselines = load_all_baselines(baselines_dir)
    
    # Get all baselines, filtered by test set
    all_results = []
    for name, data in baselines.items():
        parsed = parse_baseline_name(name)
        metrics = data["metrics"]
        config = data["config"]
        
        # Filter by test set - check both config and parsed name
        baseline_test_set = config.get("test_set", parsed.get("test_set", "lite"))
        if baseline_test_set != test_set:
            continue
        
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
    
    if not all_results:
        return ""
    
    # Sort by similarity (most important metric)
    all_results.sort(key=lambda x: x["avg_similarity"], reverse=True)
    
    # Generate HTML table for precise alignment
    title = "## 🏆 SWE-bench Verified Leaderboard" if test_set == "verified" else "## 🏆 Current Leaderboard"
    lines = [
        title,
        "",
        f"Performance on SWE-bench {test_set.title()} subset, ranked by code similarity",
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
    
    for i, result in enumerate(all_results, 1):
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
    
    return "\n".join(lines)


def update_readme_leaderboard() -> bool:
    """Update the leaderboard section in README.md. Returns True if updated."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text()
    
    # Generate both leaderboards
    lite_board = generate_leaderboard_markdown("lite")
    verified_board = generate_leaderboard_markdown("verified")
    
    # Combine with spacing
    result = lite_board + "\n\n" + verified_board
    result = result.strip()
    
    if not result:
        return False
    
    # Add "How it works" section at the end
    how_it_works = """

**How it works:**
- **Input**: A GitHub repository containing a bug with a known ground truth solution
- **Task**: Nano provides models with tools to explore the codebase and generate a fix
- **Output**: Nano produces a unified git diff containing all proposed code changes
- **Evaluation**: We measure how closely the model's solution matches the ground truth using:
  - **Code Similarity**: How well the fix matches the actual bug fix (primary ranking metric)
  - **Test Similarity**: How well any test changes match the ground truth test updates

**Note:** Prone to a lot of noise, small test set with few repetitions."""
    
    result = result + how_it_works
    
    # Find and replace leaderboard sections
    start_marker = "## 🏆 Current Leaderboard"
    start_idx = content.find(start_marker)
    
    if start_idx == -1:
        # Append to end
        content = content.rstrip() + "\n\n" + result + "\n"
    else:
        # Find next non-leaderboard section
        lines = content[start_idx:].split('\n')
        end_line = None
        
        for i, line in enumerate(lines[1:], 1):  # Skip the first line
            if line.startswith("## ") and "Leaderboard" not in line:
                end_line = i
                break
        
        if end_line:
            end_idx = start_idx + sum(len(lines[j]) + 1 for j in range(end_line))
            content = content[:start_idx] + result + "\n" + content[end_idx:]
        else:
            content = content[:start_idx] + result + "\n"
    
    readme_path.write_text(content)
    print(f"✅ Updated leaderboard in {readme_path}")
    return True


def main():    
    parser = argparse.ArgumentParser(description="Update nano-agent leaderboard in README.md")
    parser.add_argument("--dry-run", action="store_true", help="Print leaderboard without updating README")
    
    args = parser.parse_args()
    
    if args.dry_run:
        lite = generate_leaderboard_markdown("lite")
        verified = generate_leaderboard_markdown("verified")
        result = lite + "\n\n" + verified
        print(result.strip())
    else:
        update_readme_leaderboard()


if __name__ == "__main__":
    main()