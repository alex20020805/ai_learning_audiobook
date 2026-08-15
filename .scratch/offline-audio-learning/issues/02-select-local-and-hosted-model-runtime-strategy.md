# Select the local and hosted model runtime strategy

Type: research
Status: resolved
Blocked by: none

## Question

Which supported runtime, authentication, and adapter boundaries should a trusted Local Orchestrator use to invoke ChatGPT-backed Codex, `qwen3.5-9b-local` through llama.cpp, and an explicitly approved paid API fallback? Identify what Codex subscription access can and cannot support, security constraints, structured-output options, and how to keep the stages comparable.

## Answer

Use three provider-neutral adapters behind one Local Orchestrator: direct loopback HTTP to `llama-server` for `qwen3.5-9b-local`, ChatGPT-authenticated `codex exec` for the single hosted pilot candidate, and a disabled-by-default paid API adapter that can run only with a per-job authorization. Codex subscription access is suitable for this trusted personal pilot because `codex exec` officially supports scripts, cached login, JSONL, read-only sandboxing, ephemeral runs, and JSON-schema final output; it is not a general public inference endpoint or a production SLA. Keep llama.cpp bound to loopback with UI/tools/MCP disabled, protect Codex credentials, validate every provider response in the application, and compare providers using identical hashed source/context packets, prompt and schema versions, fresh tool-free runs, and the same blind scoring rubric. Any subscription failure pauses in `awaiting_paid_approval`; it never spends API credit automatically. The exact Qwen GGUF, quantization, chat template, llama.cpp build, and smoke-test result must be pinned before evaluation because the local alias alone does not establish them.

Research: [Local and hosted model runtime strategy](../research/02-local-and-hosted-model-runtime.md)
