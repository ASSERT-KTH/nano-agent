import sys
from pathlib import Path

from tools import get_diff

sys.path.append(str(Path(__file__).parent.parent))
from eval.utils import unified_diff_similarity


def diff_similarity_reward(rollout):
    """Reward based on similarity to ground truth patch."""
    instance_id = rollout.extra.get("instance_id", "")
    ground_truth_patch = rollout.extra.get("patch", "")
    
    if not instance_id or not ground_truth_patch:
        print(f"No instance_id or patch for rollout: {rollout}")
        return 0.0
    
    return unified_diff_similarity(ground_truth_patch, get_diff(instance_id))

def test_similarity_reward(rollout):
    """Reward based on similarity to test patch."""
    instance_id = rollout.extra.get("instance_id", "")
    test_patch = rollout.extra.get("test_patch", "")
    
    if not instance_id or not test_patch:
        print(f"No instance_id or test_patch for rollout: {rollout}")
        return 0.0
    
    return unified_diff_similarity(test_patch, get_diff(instance_id))

def combined_reward(rollout):
    """Combined reward for training: weighted sum of all metrics."""
    
    similarity = diff_similarity_reward(rollout)
    test_sim = test_similarity_reward(rollout)
    
    return 0.5 * similarity + 0.5 * test_sim, {
        "similarity": similarity,
        "test_sim": test_sim,
        **tool_counts(rollout),
    }

def tool_counts(rollout):
    if not rollout.extra.get("instance_id"):
        return
    
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

    return {
        "shell_calls": shell_calls,
        "patch_calls": patch_calls,
    }
    
