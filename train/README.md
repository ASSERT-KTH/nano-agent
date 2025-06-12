# VERL Training for Nano Agent

VERL-compatible training setup for Nano using exact tool implementations. This directory contains VERL-wrapped versions of Nano's tools and SLURM scripts for distributed RL training.

## Quick Start

### 1. Prepare Dataset
```bash
cd train
python build_dataset.py
```

### 2. Build Container
```bash
apptainer build --fakeroot nano.sif scripts/container.def
```

### 3. Submit SLURM Job

For 8B model with GRPO (2 GPUs):
```bash
sbatch scripts/nano_8b_grpo.sh
```

For 32B model with GRPO (8 GPUs):
```bash
sbatch scripts/nano_32b_grpo.sh
```

The SLURM scripts will automatically:
- Create logs directory if needed
- Build the container if it doesn't exist
- Generate the dataset if needed
- Launch VERL training with appropriate configurations

**Available SLURM scripts:**
- `scripts/nano_8b_grpo.sh` - 8B model, GRPO, 2 GPUs
- `scripts/nano_32b_grpo.sh` - 32B model, GRPO, 8 GPUs

## Structure

**Tool Implementation:**
- `tools.py` - VERL-compatible implementations of Nano's tools (ShellTool and ApplyPatchTool)

**Training Pipeline:**
- `build_dataset.py` - Convert SWE-Bench → VERL JSONL format
- `reward.py` - Combined reward function + individual metrics logging
- `container.def` - Apptainer container with VERL + Nano
- `scripts/nano_8b_grpo.sh` - SLURM script for 8B model GRPO training
- `scripts/nano_32b_grpo.sh` - SLURM script for 32B model GRPO training

## Reward Function

**Combined Training Signal:** `0.5 × similarity + 0.5 × test_similarity`

**Individual Metrics (logged separately):**
- `reward_diff_similarity` - Unified diff similarity to ground truth
- `reward_test_similarity` - Similarity to test patches
- `reward_combined` - The actual training signal
- Tool usage counts (`shell_calls`, `patch_calls`)
