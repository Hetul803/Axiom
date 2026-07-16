# Required Kaggle inputs and settings

- Competition data: `arc-prize-2026-arc-agi-3`
- Offline vLLM wheelhouse: `driessmit1/arc3-vllm-h100-wheelhouse-v3`
- Local model snapshot: `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot`
- Internet: disabled
- Accelerator: NVIDIA RTX Pro 6000
- Language: Python

The notebook serves `vrfai/Qwen3.6-27B-FP8` once at `127.0.0.1:1234`, enables prefix caching, and performs a smoke completion. If startup or smoke inference fails, `AXIOM_V3_LLM=0` activates deterministic V2-derived frontier exploration.

