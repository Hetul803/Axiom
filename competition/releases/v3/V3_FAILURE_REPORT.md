# V3 failure report

Official public ARC-AGI-3 environments and the specified 27B snapshot were unavailable locally, so no official result is claimed. On the 12 synthetic permutation holdouts, 6 failures remained. They arise because no-LLM V3 deliberately has no generated dynamics or goal model and therefore performs systematic exploration rather than target planning. This evaluation establishes fallback safety, not expected hybrid performance.

The highest unverified risks are generated-model quality, vLLM startup/runtime on the attached RTX Pro 6000 environment, subprocess overhead under the official harness, and context quality after long games. Hidden V3 score is unknown and no prediction is made.
