"""Self-contained private browser surface for import and chapter planning."""

PRIVATE_APPLICATION_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Learning Audiobook</title>
  <style>
    :root { color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #f4f0e8; color: #17211c; }
    main { max-width: 760px; margin: 8vh auto; padding: 2rem; }
    section { background: #fffdf8; border: 1px solid #d9d0c2; border-radius: 16px;
      padding: 2rem; box-shadow: 0 18px 50px rgb(51 42 28 / 10%); }
    h1 { font-family: ui-serif, Georgia, serif; font-size: clamp(2rem, 6vw, 3.6rem);
      line-height: 1; margin: 0 0 1rem; }
    p { color: #526057; line-height: 1.6; }
    label { display: block; font-weight: 700; margin: 1.5rem 0 .5rem; }
    input, select, textarea { display: block; width: 100%; box-sizing: border-box; padding: .9rem;
      border: 1px solid #aeb8b0; border-radius: 10px; background: white; }
    input[type="checkbox"] { display: inline-block; width: auto; margin-right: .5rem; }
    button { margin-top: 1rem; border: 0; border-radius: 999px; padding: .8rem 1.4rem;
      background: #145c43; color: white; font: inherit; font-weight: 700; cursor: pointer; }
    button:disabled { cursor: wait; opacity: .55; }
    #status { min-height: 1.5rem; margin-top: 1rem; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #17211c; color: #dce9df;
      padding: 1rem; border-radius: 10px; min-height: 3rem; }
    .planning { margin-top: 1.5rem; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .check { font-weight: 500; }
    [hidden] { display: none !important; }
  </style>
</head>
<body>
  <main>
    <section>
      <h1>Build a trustworthy listening workspace.</h1>
      <p>Select a native-text PDF. The source remains immutable and every import is traced.</p>
      <label for="source-document">Source Document</label>
      <input id="source-document" type="file" accept="application/pdf">
      <label for="source-edition-of">Prior edition (optional)</label>
      <select id="source-edition-of">
        <option value="">Start a new Book Workspace lineage</option>
      </select>
      <button id="import-source-document" type="button">Import Source Document</button>
      <p id="status" role="status" aria-live="polite"></p>
      <pre id="workspace-result" aria-label="Book Workspace result">No workspace imported.</pre>
      <label for="active-workspace">Retained Book Workspace</label>
      <select id="active-workspace">
        <option value="">Choose a retained workspace</option>
      </select>
      <button id="inspect-workspace" type="button">Inspect chapters</button>
    </section>
    <section id="planning" class="planning" hidden>
      <h2>Confirm the next Source Chapter</h2>
      <p>Inspect adjacent evidence, adjust physical-page boundaries, then create a
        provisional Learning Plan.</p>
      <label for="chapter-heading">Detected Source Chapter</label>
      <select id="chapter-heading"></select>
      <pre id="chapter-evidence" aria-label="Chapter boundary evidence">No chapter selected.</pre>
      <div class="row">
        <div><label for="start-page">Start physical page</label>
          <input id="start-page" type="number" min="1"></div>
        <div><label for="end-page">End physical page</label>
          <input id="end-page" type="number" min="1"></div>
      </div>
      <div class="row">
        <div><label for="minimum-minutes">Minimum minutes</label>
          <input id="minimum-minutes" type="number" min="5" max="25" step="0.5"
            value="15"></div>
        <div><label for="maximum-minutes">Maximum minutes</label>
          <input id="maximum-minutes" type="number" min="10" max="30" step="0.5"
            value="25"></div>
      </div>
      <label for="boundary-note">Boundary note (optional)</label>
      <textarea id="boundary-note" rows="2"
        placeholder="Why the detected boundary was adjusted"></textarea>
      <label class="check"><input id="allow-cross-chapter" type="checkbox">
        Allow this span to cross the next detected chapter boundary</label>
      <label class="check"><input id="approve-short-tail" type="checkbox">
        Approve the exact short-tail proposal shown below</label>
      <button id="confirm-chapter" type="button">Confirm span and build plan</button>
      <p id="planning-status" role="status" aria-live="polite"></p>
      <pre id="planning-result" aria-label="Learning Plan result">No plan created.</pre>
    </section>
    <section id="generation" class="planning" hidden>
      <h2>Generate a deterministic verbatim Episode</h2>
      <p>This test path uses no network or paid credit. It retains the complete script,
        transformations, transcript, 24 kHz WAV, validation, provenance, cost, and trace.</p>
      <label for="generation-session">Confirmed Listening Session</label>
      <select id="generation-session"></select>
      <button id="generate-episode" type="button">Generate deterministic Episode</button>
      <p id="generation-status" role="status" aria-live="polite"></p>
      <pre id="generation-result" aria-label="Episode Generation result">No Episode generated.</pre>
      <audio id="episode-audio" controls hidden></audio>
      <h3>Durable FIFO queue</h3>
      <pre id="queue-result" aria-label="Generation queue">Queue not loaded.</pre>
      <button id="refresh-episodes" type="button">Refresh retained Episodes</button>
      <pre id="episode-result" aria-label="Retained Episodes">No retained Episodes loaded.</pre>
    </section>
  </main>
  <script>
    const fileInput = document.querySelector("#source-document");
    const editionInput = document.querySelector("#source-edition-of");
    const importButton = document.querySelector("#import-source-document");
    const status = document.querySelector("#status");
    const result = document.querySelector("#workspace-result");
    const activeWorkspaceInput = document.querySelector("#active-workspace");
    const inspectWorkspaceButton = document.querySelector("#inspect-workspace");
    const planningSection = document.querySelector("#planning");
    const chapterInput = document.querySelector("#chapter-heading");
    const chapterEvidence = document.querySelector("#chapter-evidence");
    const startPageInput = document.querySelector("#start-page");
    const endPageInput = document.querySelector("#end-page");
    const minimumMinutesInput = document.querySelector("#minimum-minutes");
    const maximumMinutesInput = document.querySelector("#maximum-minutes");
    const boundaryNoteInput = document.querySelector("#boundary-note");
    const crossChapterInput = document.querySelector("#allow-cross-chapter");
    const shortTailInput = document.querySelector("#approve-short-tail");
    const confirmChapterButton = document.querySelector("#confirm-chapter");
    const planningStatus = document.querySelector("#planning-status");
    const planningResult = document.querySelector("#planning-result");
    const generationSection = document.querySelector("#generation");
    const generationSessionInput = document.querySelector("#generation-session");
    const generateEpisodeButton = document.querySelector("#generate-episode");
    const generationStatus = document.querySelector("#generation-status");
    const generationResult = document.querySelector("#generation-result");
    const queueResult = document.querySelector("#queue-result");
    const refreshEpisodesButton = document.querySelector("#refresh-episodes");
    const episodeResult = document.querySelector("#episode-result");
    const episodeAudio = document.querySelector("#episode-audio");
    let activeWorkspaceId = null;
    let activePlanId = null;
    let chapterCatalog = [];

    /**
     * Inputs: none; reads no arguments and uses the Book Workspace collection endpoint.
     * Functionality: populates prior-edition and retained-workspace selectors without
     * duplicating options when the collection is refreshed after an import.
     * Outputs: Promise<void> after both selectors are populated.
     * Failures: rejects when the collection request or JSON parsing fails.
     */
    async function refreshWorkspaces() {
      const response = await fetch("/api/book-workspaces");
      const payload = await response.json();
      editionInput.replaceChildren(new Option("Start a new Book Workspace lineage", ""));
      activeWorkspaceInput.replaceChildren(new Option("Choose a retained workspace", ""));
      for (const workspace of payload.workspaces) {
        const label = `${workspace.source_document.filename} — ${workspace.workspace_id}`;
        editionInput.append(new Option(label, workspace.workspace_id));
        activeWorkspaceInput.append(new Option(label, workspace.workspace_id));
      }
    }

    /**
     * Inputs: none; reads the retained Book Workspace selector.
     * Functionality: reopens chapter inspection for an existing workspace after page reload.
     * Outputs: Promise<void> after the chapter catalog is shown.
     * Failures: catches missing selection or catalog failures and reports them in status text.
     */
    async function inspectRetainedWorkspace() {
      if (!activeWorkspaceInput.value) {
        status.textContent = "Choose a retained Book Workspace first.";
        return;
      }
      try {
        await loadChapterCatalog(activeWorkspaceInput.value);
        status.textContent = "Retained Book Workspace ready for chapter planning.";
      } catch (error) {
        status.textContent = `Could not inspect workspace: ${error.message}`;
      }
    }

    /**
     * Inputs: workspaceId, the exact imported Book Workspace hash identifier.
     * Functionality: fetches detected chapters and exposes their adjacent boundary evidence.
     * Outputs: Promise<void> after planning controls are populated and visible.
     * Failures: rejects when the catalog request fails or returns invalid JSON.
     */
    async function loadChapterCatalog(workspaceId) {
      const response = await fetch(`/api/book-workspaces/${workspaceId}/chapters`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error.message);
      activeWorkspaceId = workspaceId;
      chapterCatalog = payload.chapters;
      chapterInput.replaceChildren();
      for (const chapter of chapterCatalog) {
        const option = document.createElement("option");
        option.value = chapter.heading_index;
        option.textContent = `${chapter.title} — physical pp. `
          + `${chapter.suggested_span.start_physical_page}–`
          + `${chapter.suggested_span.end_physical_page}`;
        chapterInput.append(option);
      }
      planningSection.hidden = false;
      renderChapterSelection();
      await loadGenerationContext();
    }

    /**
     * Inputs: none; reads the currently selected chapter catalog entry.
     * Functionality: displays evidence and initializes editable start/end physical pages.
     * Outputs: undefined after synchronously updating the chapter controls.
     * Failures: returns without mutation when no catalog entry is selected.
     */
    function renderChapterSelection() {
      const chapter = chapterCatalog[Number(chapterInput.value)];
      if (!chapter) return;
      startPageInput.value = chapter.suggested_span.start_physical_page;
      endPageInput.value = chapter.suggested_span.end_physical_page;
      chapterEvidence.textContent = JSON.stringify(chapter, null, 2);
    }

    /**
     * Inputs: payload, the JSON response returned by the chapter-planning endpoint.
     * Functionality: reduces a potentially large Source Index and plan into bounded,
     * decision-relevant browser evidence while retaining hashes and artifact references.
     * Outputs: a JSON-compatible summary containing errors or plan/session statistics.
     * Failures: returns the original small error envelope when planning was rejected.
     */
    function summarizePlanPayload(payload) {
      if (payload.error) return {run_id: payload.run_id, error: payload.error};
      const sourceIndex = payload.source_index || {};
      const plan = payload.plan || {};
      const nodes = sourceIndex.nodes || [];
      const nodeTypes = [...new Set(nodes.map((node) => node.type))].sort();
      return {
        run_id: payload.run_id,
        workspace_id: payload.workspace_id,
        source_index: {
          source_index_id: sourceIndex.source_index_id,
          sha256: sourceIndex.sha256,
          artifact_ref: sourceIndex.artifact_ref,
          span: sourceIndex.span,
          node_count: nodes.length,
          node_types: nodeTypes,
          warning_count: (sourceIndex.warnings || []).length
        },
        plan: {
          plan_id: plan.plan_id,
          status: plan.status,
          duration_policy: plan.duration_policy,
          sessions: (plan.listening_sessions || []).map((session) => ({
            session_number: session.session_number,
            node_count: (session.node_ids || []).length,
            start_physical_page: session.start_physical_page,
            end_physical_page: session.end_physical_page,
            estimated_minutes: session.estimated_minutes,
            word_count: session.word_count,
            boundary: session.boundary,
            cuts_atomic_unit: session.cuts_atomic_unit
          })),
          blocked_atomic_unit_count: (plan.blocked_atomic_units || []).length,
          short_tail_approval: plan.short_tail_approval
        }
      };
    }

    /**
     * Inputs: payload, a generation response or retained Episode record.
     * Functionality: presents bounded job, lifecycle, artifact, validation, provider, and cost
     * evidence without duplicating a complete copyrighted script or binary audio in the UI.
     * Outputs: a compact JSON-compatible learner inspection mapping.
     * Failures: returns a small error envelope unchanged when generation was rejected.
     */
    function summarizeEpisodePayload(payload) {
      if (payload.error) return {run_id: payload.run_id, error: payload.error};
      const episode = payload.episode || payload;
      const job = payload.job || {};
      return {
        run_id: payload.run_id,
        episode: {
          episode_id: episode.episode_id,
          status: episode.status,
          plan_id: episode.plan_id,
          session_number: episode.session_number,
          source_span: episode.source_span,
          estimated_listening_minutes: episode.estimated_listening_minutes,
          generated_test_audio_seconds: episode.generated_test_audio_seconds,
          script_segment_count: episode.script_segment_count,
          current_job_id: episode.current_job_id,
          current_job_version: episode.current_job_version,
          artifact_refs: episode.artifact_refs,
          validation_passed: episode.validation?.passed,
          provider_policy_version: episode.provider_provenance?.policy_version,
          network_used: episode.provider_provenance?.network_used,
          paid_usage: episode.provider_provenance?.paid_usage,
          total_cost_usd: episode.cost?.total_usd,
          trace_manifest_ref: episode.trace_manifest_ref
        },
        job: job.job_id ? {
          job_id: job.job_id,
          version: job.version,
          status: job.status,
          compatibility_sha256: job.pins?.compatibility_sha256,
          transitions: (job.transitions || []).map((transition) => transition.to)
        } : undefined
      };
    }

    /**
     * Inputs: plan, one confirmed immutable Learning Plan mapping.
     * Functionality: selects the active plan, populates all available Listening Sessions, and
     * exposes deterministic generation controls.
     * Outputs: undefined after synchronously updating browser state and controls.
     * Failures: hides generation and returns when the plan is missing or not confirmed.
     */
    function configureGeneration(plan) {
      if (!plan || plan.status !== "confirmed") {
        activePlanId = null;
        generationSection.hidden = true;
        return;
      }
      activePlanId = plan.plan_id;
      generationSessionInput.replaceChildren();
      for (const session of plan.listening_sessions) {
        const option = new Option(
          `Session ${session.session_number} — ${session.estimated_minutes.toFixed(2)} minutes`,
          session.session_number
        );
        generationSessionInput.append(option);
      }
      generationSection.hidden = false;
    }

    /**
     * Inputs: none; uses the active Book Workspace set by chapter inspection or import.
     * Functionality: restores the latest confirmed plan after reload and refreshes durable
     * queue and retained Episode evidence even when no generation has run in this page session.
     * Outputs: Promise<void> after all available retained generation state is displayed.
     * Failures: treats missing planning as an empty generation state and propagates other
     * transport or JSON failures.
     */
    async function loadGenerationContext() {
      if (!activeWorkspaceId) return;
      const response = await fetch(`/api/book-workspaces/${activeWorkspaceId}/planning`);
      const payload = await response.json();
      if (response.ok) {
        const confirmed = [...payload.plans].reverse().find((plan) => plan.status === "confirmed");
        configureGeneration(confirmed);
      } else if (payload.error?.code !== "planning_not_started") {
        throw new Error(payload.error.message);
      }
      await refreshGenerationQueue();
      await refreshRetainedEpisodes();
    }

    /**
     * Inputs: none; reads the public single-queue endpoint.
     * Functionality: displays FIFO sequence, active-job identity/count, and durable job states.
     * Outputs: Promise<void> after the bounded queue mapping is rendered.
     * Failures: rejects when the queue request or JSON parsing fails.
     */
    async function refreshGenerationQueue() {
      const response = await fetch("/api/generation-queue");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error.message);
      queueResult.textContent = JSON.stringify(payload.queue, null, 2);
    }

    /**
     * Inputs: none; reads the active workspace and its retained Episode collection endpoint.
     * Functionality: lists bounded ready-Episode evidence and restores the latest audio player
     * source without loading or embedding the audio bytes eagerly.
     * Outputs: Promise<void> after retained Episode summaries and player URL are updated.
     * Failures: rejects for an unavailable workspace collection or invalid JSON.
     */
    async function refreshRetainedEpisodes() {
      if (!activeWorkspaceId) return;
      const response = await fetch(`/api/book-workspaces/${activeWorkspaceId}/episodes`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error.message);
      const summaries = payload.episodes.map((episode) => summarizeEpisodePayload(episode).episode);
      episodeResult.textContent = JSON.stringify(summaries, null, 2);
      const latest = payload.episodes.at(-1);
      if (latest) {
        episodeAudio.src = `/api/book-workspaces/${activeWorkspaceId}/episodes/`
          + `${latest.episode_id}/audio`;
        episodeAudio.hidden = false;
      }
    }

    /**
     * Inputs: none; reads the active plan and selected Listening Session controls.
     * Functionality: starts one deterministic no-network Generation Job, presents bounded
     * ready evidence, and refreshes queue, retained Episode, and audio-player state.
     * Outputs: Promise<void> after success or learner-visible rejection is rendered.
     * Failures: catches transport/JSON failures, reports them, and always re-enables the button.
     */
    async function submitEpisodeGeneration() {
      if (!activeWorkspaceId || !activePlanId) {
        generationStatus.textContent = "Confirm a Learning Plan first.";
        return;
      }
      generateEpisodeButton.disabled = true;
      generationStatus.textContent = "Running the deterministic verbatim pipeline…";
      try {
        const response = await fetch(`/api/book-workspaces/${activeWorkspaceId}/episodes`, {
          method: "POST",
          headers: {"content-type": "application/json"},
          body: JSON.stringify({
            plan_id: activePlanId,
            session_number: Number(generationSessionInput.value)
          })
        });
        const payload = await response.json();
        generationResult.textContent = JSON.stringify(summarizeEpisodePayload(payload), null, 2);
        generationStatus.textContent = response.ok
          ? "Deterministic Episode is ready and retained locally."
          : payload.error.message;
        await refreshGenerationQueue();
        await refreshRetainedEpisodes();
      } catch (error) {
        generationStatus.textContent = `Generation failed: ${error.message}`;
      } finally {
        generateEpisodeButton.disabled = false;
      }
    }

    /**
     * Inputs: none; uses the active workspace selected in the browser.
     * Functionality: refreshes both durable FIFO queue evidence and retained ready Episodes
     * after an explicit learner action.
     * Outputs: Promise<void> after both browser result panels are current.
     * Failures: catches transport or parsing failures and reports them in generation status.
     */
    async function refreshGenerationView() {
      try {
        await refreshGenerationQueue();
        await refreshRetainedEpisodes();
      } catch (error) {
        generationStatus.textContent = `Refresh failed: ${error.message}`;
      }
    }

    /**
     * Inputs: none; reads the visible chapter, page, policy, and approval controls.
     * Functionality: confirms the adjusted span through the Local Orchestrator and presents
     * immutable Source Index and Learning Plan evidence, including any blocking gate.
     * Outputs: Promise<void> after the learner-visible result and status are updated.
     * Failures: catches transport/JSON failures, reports them, and always re-enables the button.
     */
    async function submitChapterPlan() {
      if (!activeWorkspaceId) { planningStatus.textContent = "Import a workspace first."; return; }
      confirmChapterButton.disabled = true;
      planningStatus.textContent = "Extracting only the confirmed span and packing atomic units…";
      try {
        const response = await fetch(`/api/book-workspaces/${activeWorkspaceId}/plans`, {
          method: "POST",
          headers: {"content-type": "application/json"},
          body: JSON.stringify({
            heading_index: Number(chapterInput.value),
            start_physical_page: Number(startPageInput.value),
            end_physical_page: Number(endPageInput.value),
            minimum_minutes: Number(minimumMinutesInput.value),
            maximum_minutes: Number(maximumMinutesInput.value),
            allow_cross_chapter: crossChapterInput.checked,
            approve_short_tail: shortTailInput.checked,
            boundary_note: boundaryNoteInput.value
          })
        });
        const payload = await response.json();
        planningResult.textContent = JSON.stringify(summarizePlanPayload(payload), null, 2);
        if (response.status === 409
            && payload.plan?.status === "awaiting_short_tail_approval") {
          planningStatus.textContent = "Review the short-tail evidence, check approval, "
            + "and submit again.";
        } else if (response.status === 409) {
          planningStatus.textContent = "Source structure must be corrected before this plan "
            + "can proceed.";
        } else {
          planningStatus.textContent = response.ok
            ? "Learning Plan confirmed." : payload.error.message;
          if (response.ok) configureGeneration(payload.plan);
        }
      } catch (error) {
        planningStatus.textContent = `Planning failed: ${error.message}`;
      } finally {
        confirmChapterButton.disabled = false;
      }
    }

    importButton.addEventListener("click", async () => {
      const file = fileInput.files[0];
      if (!file) { status.textContent = "Choose a PDF first."; return; }
      importButton.disabled = true;
      status.textContent = "Validating and scanning the Source Document…";
      try {
        const headers = { "content-type": "application/pdf", "x-source-filename": file.name };
        if (editionInput.value) headers["x-source-edition-of"] = editionInput.value;
        const response = await fetch("/api/book-workspaces/import", {
          method: "POST", headers, body: file
        });
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
        status.textContent = response.ok
          ? (payload.reopened ? "Existing Book Workspace reopened." : "Book Workspace created.")
          : payload.error.message;
        if (response.ok) {
          await refreshWorkspaces();
          activeWorkspaceInput.value = payload.workspace.workspace_id;
          await loadChapterCatalog(payload.workspace.workspace_id);
        }
      } catch (error) {
        status.textContent = `Import failed: ${error.message}`;
      } finally {
        importButton.disabled = false;
      }
    });

    chapterInput.addEventListener("change", renderChapterSelection);
    confirmChapterButton.addEventListener("click", submitChapterPlan);
    inspectWorkspaceButton.addEventListener("click", inspectRetainedWorkspace);
    generateEpisodeButton.addEventListener("click", submitEpisodeGeneration);
    refreshEpisodesButton.addEventListener("click", refreshGenerationView);

    refreshWorkspaces().catch((error) => {
      status.textContent = `Could not list prior editions: ${error.message}`;
    });
  </script>
</body>
</html>"""
