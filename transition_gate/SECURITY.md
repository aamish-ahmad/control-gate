# Security and disclosure boundaries

- The controller makes recommendations, never tool calls. Consumers MUST enforce authorization again at dispatch.
- Treat model outputs and user-supplied goals as untrusted observations. Do not let an agent write `permissions`, `human_approved`, hard deadline verification, or final closure on its own authority.
- The state revision and TTL protect against **some** stale-snapshot mistakes. They do not solve races: use atomic compare-and-swap or a fresh permission check at execution.
- This implementation has no calibration evidence and no security certification. Synthetic unit tests only establish local logical behavior.
- Do not publish private agent traces, personal documents, provider tokens, or actual credentials. The included cases are entirely fictional.
- `input_sha256` is a deterministic identifier, not an authenticity signature. Attach independently verified provenance if needed.
