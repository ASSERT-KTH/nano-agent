import json
import sys
from pathlib import Path
from typing import Dict

# Import Nano's system prompt
sys.path.append(str(Path(__file__).parent.parent))
from nano.agent import SYSTEM_PROMPT

def to_sample(row: Dict) -> Dict:
    """Convert a SWE-Bench row to VERL dataset format."""
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
    """Load SWE-Bench from HuggingFace datasets and convert to VERL JSONL format."""
    from datasets import load_dataset
    
    dataset = load_dataset(dataset_name, split=split)
    
    with open(output_file, 'w') as f:
        for row in dataset:
            sample = to_sample(row)
            f.write(json.dumps(sample) + '\n')
    
    print(f"Converted {len(dataset)} samples from {dataset_name}:{split} to {output_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert SWE-Bench dataset to VERL format")
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite", 
                        help="HuggingFace dataset name (default: princeton-nlp/SWE-bench_Lite)")
    parser.add_argument("--split", default="test", help="Dataset split (default: test)")
    parser.add_argument("--output", type=Path, default="swe_bench_verl.jsonl",
                        help="Output JSONL file (default: swe_bench_verl.jsonl)")
    
    args = parser.parse_args()
    
    convert_dataset(args.dataset, args.split, args.output)

if __name__ == "__main__":
    main()