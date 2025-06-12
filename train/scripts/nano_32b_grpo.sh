#!/bin/bash
#SBATCH --job-name=nano-32b-grpo
#SBATCH --output=logs/nano_32b_%j.out
#SBATCH --error=logs/nano_32b_%j.err
#SBATCH --gpus 8
#SBATCH --time=24:00:00
#SBATCH -C "fat"

# WIP

# Launch VERL training with GRPO for 32B model
apptainer exec --nv nano.sif python -m verl.trainer.main_ppo \
    # ── data ───────────────────────────────────────────────
    data.train_files=swe_bench_verl.jsonl \
    data.train_batch_size=12 \
    data.max_prompt_length=1024 \
    data.max_response_length=7168 \
    # ── model / back-prop engine ───────────────────────────
    actor_rollout_ref.model.path=Qwen/Qwen3-32B \
    actor_rollout_ref.model.lora_rank=32 \
    actor_rollout_ref.actor.strategy=fsdp2 \
    actor_rollout_ref.ref.strategy=fsdp2 \
    actor_rollout_ref.hybrid_engine=true \
    # ── rollout engine (async multi-turn + tools) ──────────
    actor_rollout_ref.rollout.name=sglang_async \
    actor_rollout_ref.rollout.multi_turn=true \
    actor_rollout_ref.rollout.response_length=7168 \
    actor_rollout_ref.rollout.n=4 \
    actor_rollout_ref.rollout.temperature=0.7 \
    actor_rollout_ref.rollout.top_p=0.9 \
    actor_rollout_ref.rollout.tool_kwargs.tools_config_file=verl_config/nano_tools.yaml \
    # ── GRPO toggles (defaults are fine, no PPO flags) ─────
    algorithm.adv_estimator=grpo \
    algorithm.use_kl_loss=true \        # default, explicit for clarity
    # ── reward hook ────────────────────────────────────────
    custom_reward_function.path=reward.py \
    custom_reward_function.name=combined_reward \
    reward_model.enable=false \
    # ── trainer bookkeeping ────────────────────────────────
    trainer.batch_size=12 \
    trainer.gradient_accumulation_steps=4 \
    trainer.total_training_steps=1000 \
    trainer.checkpoint.save_every_n_steps=100 \
    trainer.eval_every_n_steps=50 \
    trainer.project_name=nano-8b-grpo \
    trainer.experiment_name=grpo-run-$SLURM_JOB_ID \
    trainer.default_local_dir=output/nano8b_grpo \
    # ── wandb logging ─────────────────────────────────────────
    loggers.wandb.enable=true \
    loggers.wandb.project=Nano-VERL \
    loggers.wandb.name=${trainer.experiment_name} \
    loggers.wandb.tags="[grpo,qwen32b]" \
    # ── resources ──────────────────────────────────────────
    resources.num_gpus=8 \
    resources.num_rollout_workers=0 \
    "$@"