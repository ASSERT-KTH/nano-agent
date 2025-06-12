#!/bin/bash
#SBATCH --job-name=nano-32b-grpo
#SBATCH --output=logs/nano_32b_%j.out
#SBATCH --error=logs/nano_32b_%j.err
#SBATCH --gpus=8
#SBATCH --time=24:00:00
#SBATCH -C "fat"

# Export environment variables
export WANDB_SSL_VERIFY=false

# Create logs directory if it doesn't exist
mkdir -p logs

# --------------------------------------------------------------------
#  Launch GRPO training using YAML configuration
# --------------------------------------------------------------------
apptainer exec --nv nano.sif python -m verl.trainer.main_ppo \
  --config-name $(pwd)/configs/nano_32b_grpo.yaml \
  trainer.experiment_name=qwen3-32b-grpo-${SLURM_JOB_ID} \
  "$@"