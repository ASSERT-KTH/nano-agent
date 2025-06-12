import json
import argparse
from pathlib import Path
from typing import Dict

from datasets import load_dataset, Dataset
from transformers import AutoTokenizer

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
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    
    samples = []
    for row in dataset:
        sample = to_sample(row)
        if len(tokenizer.apply_chat_template(sample["messages"], tokenize=True)) > 1024:
            continue
        samples.append(sample)

    Dataset.from_list(samples).to_parquet("swe_gym_verl.parquet")
    

def main():    
    parser = argparse.ArgumentParser(description="Convert SWE-Gym dataset to VERL format")
    parser.add_argument("--dataset", default="SWE-Gym/SWE-Gym-Lite", help="HuggingFace dataset name (default: SWE-Gym/SWE-Gym-Lite)")
    parser.add_argument("--split", default="train", help="Dataset split (default: train)")
    parser.add_argument("--output", type=Path, default="swe_gym_verl.jsonl", help="Output JSONL file (default: swe_gym_verl.jsonl)")
    args = parser.parse_args()
    
    convert_dataset(args.dataset, args.split, args.output)

if __name__ == "__main__":
    main()
    ds = Dataset.from_parquet("swe_gym_verl.parquet")
    
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")

    lengths = [len(tokenizer.apply_chat_template(sample["messages"], tokenize=True)) for sample in ds]
    print(max(lengths))
    print(min(lengths))
    print(sum(lengths) / len(lengths))

    i_min = lengths.index(min(lengths))
    print("min length sample")
    print(ds[i_min])

    i_max = lengths.index(max(lengths))
    print("max length sample")
    print(ds[i_max])

    print("count more than 1024")
    print(sum(1 for length in lengths if length > 1024))

    print("count more than 2048")
    print(sum(1 for length in lengths if length > 2048))

    print("count more than 4096")
    print(sum(1 for length in lengths if length > 4096))

    print("count more than 8192")