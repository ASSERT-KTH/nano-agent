#SBATCH --job-name=nano-8b-grpo
#SBATCH --output=logs/nano_8b_%j.out
#SBATCH --error=logs/nano_8b_%j.err
#SBATCH --gpus=2
#SBATCH --time=24:00:00
#SBATCH -C "fat"

export WANDB_SSL_VERIFY=false

# --------------------------------------------------------------------
#  Launch GRPO training (Qwen 8-B, LoRA-32, async SGLang roll-outs)
# --------------------------------------------------------------------
apptainer exec --nv nano.sif python -m verl.trainer.main_ppo \
  data.train_files=swe_gym_verl.parquet \
  data.val_files=swe_gym_verl.parquet \
  data.prompt_key=messages \
  data.max_prompt_length=2048 \
  data.max_response_length=7168 \
  data.train_batch_size=16 \
  actor_rollout_ref.model.path=Qwen/Qwen3-8B \
  actor_rollout_ref.model.lora_rank=32 \
  actor_rollout_ref.actor.strategy=fsdp2 \
  actor_rollout_ref.ref.strategy=fsdp2 \
  actor_rollout_ref.hybrid_engine=true \
  actor_rollout_ref.rollout.name=vllm \
  actor_rollout_ref.rollout.tensor_model_parallel_size=2 \
  actor_rollout_ref.rollout.multi_turn.enable=true \
  +actor_rollout_ref.rollout.multi_turn.tool_config_path=tools.yaml \
  actor_rollout_ref.rollout.enable_chunked_prefill=false\
  actor_rollout_ref.rollout.response_length=7168 \
  actor_rollout_ref.rollout.max_num_batched_tokens=4096 \
  actor_rollout_ref.rollout.n=4 \
  actor_rollout_ref.rollout.temperature=0.7 \
  actor_rollout_ref.rollout.top_p=0.9 \
  +actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=4 \
  +actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=4 \
  +actor_rollout_ref.actor.ppo_batch_size=16 \
  actor_rollout_ref.actor.ppo_mini_batch_size=4 \
  algorithm.adv_estimator=grpo \
  +trainer.kl_loss.use_kl_loss=true \
  custom_reward_function.path=reward.py \
  custom_reward_function.name=combined_reward \
  reward_model.enable=false \
  trainer.project_name=nano-8b-grpo \
  trainer.experiment_name=grpo-run \
  trainer.default_local_dir=output/nano8b_grpo \
  trainer.n_gpus_per_node=2 \
  trainer.nnodes=1 \
  trainer.logger=["console"] \
  "$@"
