import argparse
from pathlib import Path
from typing import Dict

from datasets import load_dataset, Dataset

from nano.agent import SYSTEM_PROMPT


def to_sample(row: Dict) -> Dict:
    """Convert a SWE-Gym row to VERL dataset format."""
    return {
        "data_source": "swe-gym",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": row["problem_statement"]},
        ],
        "ability": "coding",
        "reward_model": {
            "style": "rule", 
            "ground_truth": row["patch"]
        },
        "extra_info": {
            "instance_id": row["instance_id"],
            "repo": row["repo"],
            "base_commit": row["base_commit"],
            "test_patch": row.get("test_patch", ""),
            "problem_statement": row["problem_statement"],
        },
    }

def convert_dataset(dataset_name: str, split: str, output_file: Path):
    """Load SWE-Gym from HuggingFace datasets and convert to VERL parquet format."""
    
    dataset = load_dataset(dataset_name, split=split)
    processed_dataset = dataset.map(to_sample)
    
    processed_dataset.to_parquet(output_file)
    processed_dataset.select([0]).to_parquet("dummy.parquet")
    

def main():    
    parser = argparse.ArgumentParser(description="Convert SWE-Gym dataset to VERL format")
    parser.add_argument("--dataset", default="SWE-Gym/SWE-Gym-Lite", help="HuggingFace dataset name (default: SWE-Gym/SWE-Gym-Lite)")
    parser.add_argument("--split", default="train", help="Dataset split (default: train)")
    parser.add_argument("--output", type=Path, default="swe_gym_verl.parquet", help="Output parquet file (default: swe_gym_verl.parquet)")
    args = parser.parse_args()
    
    convert_dataset(args.dataset, args.split, args.output)

if __name__ == "__main__":
    main()