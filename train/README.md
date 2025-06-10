# VERL Training for Nano Agent

Minimal setup to train Nano with VERL using exact tool implementations.

## Quick Start

1. **Convert dataset**:
```bash
cd train
python build_dataset.py --dataset princeton-nlp/SWE-bench_Lite --split test
```

2. **Train with VERL**:
```bash
python -m verl.train \
  --config nano_sglang.yaml \
  --dataset swe_bench_verl.jsonl \
  --actor_model qwen/Qwen3-7B-Instruct
```

## Structure

- `verl_tools/` - VERL-wrapped versions of Nano's tools
  - `workspace.py` - Git repo management per rollout
  - `shell.py` - Shell tool (exact match of nano.tools.shell)
  - `patch.py` - Patch tool (exact match of nano.tools.apply_patch)
  - `swe_tools.yaml` - Tool schemas

- `build_dataset.py` - Load SWE-Bench from HuggingFace → VERL JSONL
- `reward.py` - CodeRepairRL-style unified diff reward functions
- `nano_sglang.yaml` - VERL training config

## Reward Functions

- `non_empty_diff` - Binary: 1.0 if any diff generated
- `diff_similarity` - CodeRepairRL unified diff similarity (0-1)
- `file_match` - Fraction of correct files identified (0-1)
- `test_similarity` - Similarity to test patches (0-1)

## Customization

Override config parameters:
```bash
python -m verl.train \
  --config configs/nano_sglang.yaml \
  --dataset data.jsonl \
  --actor_model gpt2 \
  --trainer.reward_fn nano_success \
  --trainer.batch_size 64 \
  --resources.num_gpus 4
```

## Notes

- Tools use Nano's exact feedback/warning messages
- Each rollout gets a fresh git checkout
- Diffs are saved for reward computation
- Uses Nano's unified_diff_similarity metric