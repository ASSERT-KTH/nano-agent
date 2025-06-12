import argparse
from pathlib import Path
from typing import Dict

from datasets import load_dataset, Dataset

from nano.agent import SYSTEM_PROMPT

def to_sample(row: Dict) -> Dict:
    """Convert a SWE-Gym esque row to VERL dataset format."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": row["problem_statement"]},
        ],
        "repo": row["repo"],
        "base_commit": row["base_commit"], 
        "instance_id": row["instance_id"],
        "patch": row["patch"],
        "test_patch": row.get("test_patch", ""),
    }

def convert_dataset(dataset_name: str, split: str, output_file: Path):
    """Load SWE-Gym from HuggingFace datasets and convert to VERL JSONL format."""
    
    dataset = load_dataset(dataset_name, split=split)
    samples = [to_sample(row) for row in dataset]

    Dataset.from_list(samples).to_parquet(output_file)
    Dataset.from_list(samples[:1]).to_parquet("dummy.parquet")
    

def main():    
    parser = argparse.ArgumentParser(description="Convert SWE-Gym dataset to VERL format")
    parser.add_argument("--dataset", default="SWE-Gym/SWE-Gym-Lite", help="HuggingFace dataset name (default: SWE-Gym/SWE-Gym-Lite)")
    parser.add_argument("--split", default="train", help="Dataset split (default: train)")
    parser.add_argument("--output", type=Path, default="swe_gym_verl.jsonl", help="Output JSONL file (default: swe_gym_verl.jsonl)")
    args = parser.parse_args()
    
    convert_dataset(args.dataset, args.split, args.output)

if __name__ == "__main__":
    main()