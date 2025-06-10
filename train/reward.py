import re
import sys
from pathlib import Path

from verl.core_algos import register_reward_fn, register_post_processor

from verl_tools.workspace import get_diff

# Import shared utilities 
sys.path.append(str(Path(__file__).parent.parent))
from test.utils import unified_diff_similarity

def split_diff_by_files(diff_text):
    """Split unified diff into individual file diffs."""
    # Split on "diff --git" but keep the delimiter
    parts = re.split(r'(?=^diff --git)', diff_text, flags=re.MULTILINE)
    return [part.strip() for part in parts if part.strip()]

def extract_filename_from_diff(file_diff):
    """Extract filename from a file diff."""
    lines = file_diff.splitlines()
    match = re.search(r'diff --git a/(.*) b/', lines[0]) if lines else None
    return match.group(1) if match else ""

def unified_diff_file_match(patch, generated_diff):
    """Return the fraction of patch files correctly identified in generated diff."""
    if not patch or not generated_diff:
        return 0.0
    
    # Split into individual file diffs and extract filenames
    oracle_file_diffs = split_diff_by_files(patch)
    gen_file_diffs = split_diff_by_files(generated_diff)
    
    oracle_filenames = {extract_filename_from_diff(diff) for diff in oracle_file_diffs}
    gen_filenames = {extract_filename_from_diff(diff) for diff in gen_file_diffs}
    
    if not oracle_filenames:
        return 1.0 if not gen_filenames else 0.0
    else:
        return len(oracle_filenames & gen_filenames) / len(oracle_filenames)


def diff_similarity_reward(rollout):
    """Reward based on similarity to ground truth patch."""
    instance_id = rollout.extra.get("instance_id")
    ground_truth_patch = rollout.extra.get("patch", "")
    
    if not instance_id or not ground_truth_patch:
        return 0.0
    
    generated_diff = get_diff(instance_id)
    if not generated_diff:
        return 0.0
    
    return unified_diff_similarity(ground_truth_patch, generated_diff)

def test_similarity_reward(rollout):
    """Reward based on similarity to test patch."""
    instance_id = rollout.extra.get("instance_id")
    test_patch = rollout.extra.get("test_patch", "")
    
    if not instance_id or not test_patch:
        return 0.0
    
    generated_diff = get_diff(instance_id)
    return unified_diff_similarity(test_patch, generated_diff)

def file_match_reward(rollout):
    """Reward based on fraction of correct files identified."""
    instance_id = rollout.extra.get("instance_id")
    ground_truth_patch = rollout.extra.get("patch", "")
    
    if not instance_id or not ground_truth_patch:
        return 0.0
    
    generated_diff = get_diff(instance_id)
    return unified_diff_file_match(ground_truth_patch, generated_diff)

@register_reward_fn("combined_reward")
def combined_reward(rollout):
    """Combined reward for training: weighted sum of all metrics."""
    instance_id = rollout.extra.get("instance_id")
    
    if not instance_id:
        return 0.0
    
    generated_diff = get_diff(instance_id)
    if not generated_diff:
        return 0.0
    
    # Individual components
    similarity = diff_similarity_reward(rollout)
    file_match = file_match_reward(rollout)
    test_sim = test_similarity_reward(rollout)
    
    # Weighted combination: main patch similarity + file matching + test similarity
    return 0.5 * similarity + 0.3 * file_match + 0.2 * test_sim


@register_post_processor("attach_diff")
def attach_diff_processor(rollout):
    """Attach the generated diff and all reward metrics for logging/analysis."""
    instance_id = rollout.extra.get("instance_id")
    if not instance_id:
        return
    
    # Attach generated diff
    rollout.extra["generated_diff"] = get_diff(instance_id)
    
    # Compute and log all individual reward metrics
    rollout.extra["reward_diff_similarity"] = diff_similarity_reward(rollout)
    rollout.extra["reward_file_match"] = file_match_reward(rollout)
    rollout.extra["reward_test_similarity"] = test_similarity_reward(rollout)
    rollout.extra["reward_combined"] = combined_reward(rollout)

@register_post_processor("cleanup_metrics")
def cleanup_metrics_processor(rollout):
    """Add Nano-style metrics to rollout."""
    # Count tool uses
    shell_calls = 0
    patch_calls = 0
    
    for msg in rollout.messages:
        if msg.get("tool_calls"):
            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                if name == "shell":
                    shell_calls += 1
                elif name == "apply_patch":
                    patch_calls += 1
    
    rollout.extra["shell_calls"] = shell_calls
    rollout.extra["patch_calls"] = patch_calls
    rollout.extra["total_tool_calls"] = shell_calls + patch_calls