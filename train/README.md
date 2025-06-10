# VERL Training for Nano Agent

VERL-compatible training setup for Nano using exact tool implementations. This directory contains VERL-wrapped versions of Nano's tools and configs for distributed RL training.

## Quick Start

### 1. Prepare Dataset
```bash
cd train
python build_dataset.py --dataset princeton-nlp/SWE-bench_Lite --split test
```

### 2. Build Container
```bash
apptainer build nano-verl.sif container.def
```

### 3. Allocate SLURM Resources
```bash
salloc --gpus 4 -c fat  # (adjust to your own slurm server setup)
```

### 4. Launch Training
Example with 8B model using GRPO:
```bash
apptainer exec --nv nano-verl.sif python -m verl.train \
  --config verl_config/nano_8b_grpo.yaml \
  --dataset swe_bench_verl.jsonl \
  --actor_model Qwen/Qwen3-8B
```

**Available configs:**
- `nano_8b_ppo.yaml` - 8B model, PPO, 4 GPUs
- `nano_8b_grpo.yaml` - 8B model, GRPO, 4 GPUs  
- `nano_32b_ppo.yaml` - 32B model, PPO, 8 GPUs
- `nano_32b_grpo.yaml` - 32B model, GRPO, 8 GPUs

## Structure

**Tool Implementation:**
- `verl_tools/` - Nano's tools made VERL-compatible
  - `workspace.py` - Git repo management using nano.utils
  - `shell.py` - Exact match of nano.tools.shell
  - `patch.py` - Exact match of nano.tools.apply_patch  
  - `nano_tools.yaml` - Tool schemas for VERL

**Training Pipeline:**
- `build_dataset.py` - Convert SWE-Bench → VERL JSONL format
- `reward.py` - Combined reward function + individual metrics logging
- `container.def` - Apptainer container with VERL + Nano
- `verl_config/` - Training configurations for different model sizes

## Reward Function

**Combined Training Signal:** `0.5 × similarity + 0.5 × test_similarity`

**Individual Metrics (logged separately):**
- `reward_diff_similarity` - Unified diff similarity to ground truth
- `reward_test_similarity` - Similarity to test patches
- `reward_combined` - The actual training signal
- Tool usage counts (`shell_calls`, `patch_calls`)
