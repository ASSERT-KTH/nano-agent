import sys
from pathlib import Path

from tools import get_diff

sys.path.append(str(Path(__file__).parent.parent))
from eval.utils import unified_diff_similarity


def compute_score(data_source, solution_str, ground_truth, extra_info):
    """
    VERL-compatible reward function using naive RewardManager.
    
    Args:
        data_source: Dataset name ("swe-gym")
        solution_str: Generated solution text from the model
        ground_truth: Ground truth patch from reward_model
        extra_info: Additional data including instance_id, test_patch, etc.
        
    Returns:
        (float, dict): Main reward score and extra metrics for logging
    """    
    instance_id = extra_info["instance_id"]
    test_patch = extra_info["test_patch"]
    
    generated_diff = get_diff(instance_id)
    patch_similarity = unified_diff_similarity(ground_truth, generated_diff)
    test_similarity = unified_diff_similarity(test_patch, generated_diff)
    
    # Main reward score
    main_score = 0.5 * patch_similarity + 0.5 * test_similarity
    
    # Extra metrics for logging
    extra_metrics = {
        "patch_similarity": patch_similarity,
        "test_similarity": test_similarity,
    }
    
    return main_score, extra_metrics

    
