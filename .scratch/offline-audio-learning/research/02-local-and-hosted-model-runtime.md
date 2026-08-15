# Local and hosted model runtime strategy

Research date: 2026-08-15

## Decision

Use a trusted, Mac-hosted **Local Orchestrator** with three adapters behind one task contract:

1. **`local_llama`** — direct HTTP calls to `llama-server` for the installed `qwen3.5-9b-local` model.
2. **`hosted_codex_subscription`** — `codex exec` authenticated with the user's ChatGPT account, used only on the trusted Mac for the pilot.
3. **`paid_api`** — a direct hosted-model API adapter that is disabled until the user approves the estimated charge for that specific job.

For the pilot, compare exactly one hosted candidate (the ChatGPT-backed Codex lane) with the one local Qwen candidate. Do not add Anthropic or a second hosted model yet. Keep text generation separate from TTS: these adapters produce validated transcript/planning data; a speech adapter converts the accepted transcript to audio.

The verbatim MVP should not call any language model for source wording when deterministic extraction is sufficient. These adapters become relevant for structural judgment, difficult visual narration, later listening-oriented rewriting, guided explanations, quiz generation, and learner-evidence interpretation.

## Why this boundary

### ChatGPT-backed Codex is viable for a personal local pilot

Codex supports both ChatGPT sign-in for subscription access and API-key sign-in for usage-based access. The desktop app, CLI, and IDE extension support both methods for local work; `codex login` starts the ChatGPT browser flow. The selected sign-in method also determines the applicable workspace and data-handling controls. [OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth)

`codex exec` is an officially documented non-interactive surface for scripts, scheduled jobs, and pipelines. It can emit JSONL events, write the final message to a file, and constrain the final response with `--output-schema`. It reuses saved CLI authentication by default. [OpenAI non-interactive mode documentation](https://learn.chatgpt.com/docs/non-interactive-mode)

Therefore an event triggered by the user's typed check-in can safely invoke a ChatGPT-authenticated local CLI process for this personal pilot. This is not the same thing as a general hosted inference API: the adapter depends on an interactive user's Codex entitlement, local cached credentials, product rate limits, and the CLI's agent runtime. Treat it as a pilot convenience, not a production SLA or a multi-user backend.

OpenAI documents API keys as the default for general automation and describes ChatGPT-managed automation as an advanced path for trusted runners. The personal pilot can deliberately accept the subscription-backed tradeoff because generation occurs on the user's Mac after a user event. If the subscription lane is unavailable or needs sign-in, the job must pause; it must not silently switch to metered usage. [OpenAI non-interactive authentication guidance](https://learn.chatgpt.com/docs/non-interactive-mode#authenticate-in-automation)

The Codex SDK can start, continue, and resume local Codex threads and is intended for server-side integration, but OpenAI describes it primarily for coding-focused threads. The CLI already supplies the pilot's needed subprocess, JSONL, sandbox, ephemeral-session, and output-schema controls, so `codex exec` is the smaller first integration. Reconsider the SDK only if thread lifecycle or richer event streaming becomes a concrete requirement. [OpenAI Codex SDK documentation](https://learn.chatgpt.com/docs/codex-sdk)

### llama.cpp should be called directly

`llama-server` exposes OpenAI-compatible chat-completion, response, and embedding routes and supports schema-constrained JSON. It is explicitly an HTTP inference server, so the Local Orchestrator can use a small direct client rather than wrapping Qwen in an agent runtime. [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

Qwen's first-party local-running guide describes llama.cpp as a multi-platform local runtime, shows `llama-server`, recommends the embedded Jinja chat template, and documents GGUF use. That page currently establishes Qwen3 support, not the exact `Qwen3.5-9B` alias available on this machine. The alias must therefore be treated as a local deployment fact and qualified with a startup smoke test rather than assumed from the name. [Qwen llama.cpp guide](https://github.com/QwenLM/Qwen3/blob/main/docs/source/run_locally/llama.cpp.md)

Before evaluation, record:

- llama.cpp version and build commit;
- model response from `/v1/models`;
- GGUF filename, quantization, size, and SHA-256;
- embedded chat-template identity or hash;
- configured context size and hardware/backend;
- a schema-output smoke test and a short representative generation.

If any of these change, treat the runtime as a new candidate and rerun the relevant evaluation. llama.cpp changes frequently, and Qwen itself warns that new builds can introduce regressions. [Qwen llama.cpp installation guidance](https://github.com/QwenLM/Qwen3/blob/main/docs/source/run_locally/llama.cpp.md#getting-the-program)

## Canonical adapter contract

Every model-backed stage receives the same provider-neutral request:

```text
GenerationRequest
  task_kind
  source_packet[]          # exact text/figure descriptions and page/span IDs
  learner_context[]        # only explicitly retrieved, stage-allowed evidence
  prompt_template_version
  output_schema_version
  output_schema
  max_output_tokens
  deadline
  run_mode                 # production | evaluation
  paid_authorization_id?   # required only for paid_api
```

Every adapter returns one normalized result:

```text
GenerationResult
  validated_output
  raw_output_location
  provider_kind
  requested_model
  reported_model
  runtime_version
  input_hash
  prompt_template_version
  output_schema_version
  started_at / finished_at
  input_tokens? / output_tokens?
  estimated_cost / actual_cost?
  validation_attempts
  warnings[]
```

The UI and learning-plan code depend only on this contract. Provider-specific request bodies, credentials, reasoning fields, token accounting, and errors remain inside the adapter.

## Structured outputs

Use one deliberately conservative JSON Schema for both lanes:

- objects, arrays, strings, numbers, booleans, and nulls;
- `required` fields;
- enums where useful;
- `additionalProperties: false`;
- no complex regex patterns, recursive references, or provider-specific extensions.

For Codex, pass that schema with `codex exec --output-schema` and capture the final response separately from the `--json` event stream. The CLI documents both capabilities. [OpenAI non-interactive mode documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)

For llama.cpp, pass the portable schema through the server's `response_format`/JSON-schema mechanism. llama.cpp documents that it converts a subset of JSON Schema to a GBNF grammar and notes that the schema constrains output but is not itself shown to the model, so the prompt must also describe the expected structure. [llama.cpp grammar documentation](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

For a future direct OpenAI API adapter, Structured Outputs can enforce a supplied JSON Schema on supported models. [OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs)

Regardless of provider claims, the application must parse and validate every response itself before committing it as a learning artifact. On validation failure, allow one schema-focused retry with the same source packet, then fail visibly. Never accept malformed output through a permissive parser, and never let a schema retry add source material or learner context.

## Security profile

### Local Qwen process

- Bind `llama-server` to `127.0.0.1` (its documented default), not the LAN. The web backend, not the iPhone browser, is the only caller. [llama.cpp server options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Disable the llama.cpp web UI, built-in tools, agent mode, MCP proxy, and local-media access. Those capabilities are unnecessary for transcript work and increase the attack surface.
- Set a random API key even on loopback, restrict CORS to the application origin, and keep the model port out of logs and UI. llama.cpp supports API-key files and TLS, but loopback isolation is simpler for the pilot. [llama.cpp authentication and TLS options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Run under the user's account with access only to the job packet and output directory. The model receives normalized text, not arbitrary filesystem paths.

### ChatGPT-backed Codex process

- Run from a dedicated per-job directory containing only the input packet, schema, and output target.
- Use `--ephemeral`, `--sandbox read-only`, and `--output-schema`; do not use `danger-full-access`. The documented default is already read-only, and OpenAI recommends least privilege for automation. [OpenAI non-interactive permissions guidance](https://learn.chatgpt.com/docs/non-interactive-mode#permissions-and-safety)
- Do not expose `codex exec`, the Codex SDK, or cached auth through an HTTP route. The application invokes it as a fixed subprocess with no user-controlled flags or shell interpolation.
- Treat extracted book text as untrusted data that may contain instruction-like content. Delimit source payloads, forbid tools and outside retrieval in the task prompt, and never place secrets in the job directory or process environment.
- Protect `~/.codex/auth.json` like a password. OpenAI says CLI/IDE credentials may be cached there in plaintext or in the OS credential store and explicitly warns against committing or sharing the file. [OpenAI login caching guidance](https://learn.chatgpt.com/docs/auth#login-caching)

### Paid API process

- Keep keys server-side in the OS credential store or a secrets manager; never send them to the browser, store them in the database, or write them into job artifacts. OpenAI recommends secure storage rather than source code or public repositories. [OpenAI production guidance](https://developers.openai.com/api/docs/guides/production-best-practices#api-keys)
- Use a dedicated project with tracked usage and hard spend limits. OpenAI documents per-project rate/spend controls and hard spend limits. [OpenAI production guidance](https://developers.openai.com/api/docs/guides/production-best-practices#managing-billing-limits)
- Materialize the secret only in the provider adapter and redact request headers and raw errors.

## Explicit paid-fallback state machine

The routing engine must never interpret a subscription error as consent to spend money:

```text
requested
  -> local attempt, when stage policy selects local
  -> subscription attempt, when stage policy selects hosted Codex

subscription unavailable / rate-limited / signed out
  -> awaiting_paid_approval
  -> show provider, model, estimated maximum charge, episode total,
     and remaining $1-per-Episode / $25-per-book pilot budget

user declines or does not answer
  -> paused (no paid request)

user approves this job
  -> create single-use paid_authorization_id
  -> paid_api may run within the approved maximum

estimate rises above approval or a retry is needed
  -> awaiting_paid_approval again
```

Do not persist a global "always pay" toggle in the pilot. The existing budget consent establishes ceilings, not permission for an arbitrary future request. Log approval metadata separately from content, and show actual charge when the provider reports usage.

## Making the hosted and local runs comparable

Comparability is an orchestration property, not a promise that two runtimes expose identical sampling knobs.

For every evaluation pair:

1. Freeze the same source packet, learner-context packet, prompt-template version, output schema, and output limit; identify the packet by hash.
2. Give neither lane tools, web access, filesystem retrieval, prior thread history, or hidden Obsidian context. Use a fresh ephemeral Codex run and a fresh llama request.
3. Ask both lanes for the same final artifact, not their reasoning traces. Reasoning formats are provider-specific and must not be scored or fed to TTS.
4. Validate with the same application validator and deterministic source-grounding checks.
5. Store raw provider output, validated output, warnings, latency, tokens when reported, and marginal cost. Record any control the runtime could not honor instead of pretending it was matched.
6. Randomize provider labels for the user's manual review. Score fidelity, omissions, unsupported additions, listening usefulness, technical correctness, latency, and cost against the same rubric.

Do not force common temperature or seed if one runtime does not expose an equivalent control. Pin what can be pinned, record what cannot, and compare multiple representative source spans. The decision should be stage-specific: Qwen may pass structural detection but fail faithful rewriting, while Codex may justify its hosted lane only for the harder stage.

## Recommended pilot commands and requests

The implementation should construct arguments without a shell. Conceptually, the hosted lane is:

```text
codex exec -
  --ephemeral
  --sandbox read-only
  --json
  --output-schema <schema-file>
  --output-last-message <result-file>
  --cd <isolated-job-dir>
```

The prompt and source packet arrive on stdin. The adapter verifies `codex login status` during health checking but never reads or copies the cached credential.

The local lane uses an HTTP client against a loopback-only `llama-server` and sends messages plus the same portable response schema. Pin the local model alias only after `/v1/models` and the runtime smoke test establish what `qwen3.5-9b-local` actually refers to.

## Consequences for later tickets

- The model-comparison ticket should test stage-specific quality, not select a universal winner.
- The architecture ticket can depend on the three-adapter contract and explicit `awaiting_paid_approval` state.
- The workflow ticket should expose hosted-auth health and local-model health before generation starts.
- The learner-memory ticket must produce an explicit retrieval packet; adapters must never scan Obsidian or the full learning store.
- The speech comparison remains independent. A text model produces an accepted transcript; a TTS model voices it.

## Remaining implementation checks

These are acceptance checks, not unresolved architecture decisions:

- Confirm the installed Codex CLI version supports `--ephemeral`, `--json`, and `--output-schema` and run one subscription-authenticated schema smoke test.
- Confirm `qwen3.5-9b-local` model identity, quantization, chat template, context size, and llama.cpp build.
- Confirm loopback binding, API-key enforcement, disabled UI/tools/MCP, and application-only access to llama.cpp.
- Confirm a failed subscription call enters `awaiting_paid_approval` without touching an API key.
- Confirm both adapters reject the same intentionally malformed response and preserve the same provenance fields.
