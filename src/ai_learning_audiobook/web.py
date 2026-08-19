"""Self-contained private browser surface for Source Document import."""

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
    input, select { display: block; width: 100%; box-sizing: border-box; padding: .9rem;
      border: 1px solid #aeb8b0; border-radius: 10px; background: white; }
    button { margin-top: 1rem; border: 0; border-radius: 999px; padding: .8rem 1.4rem;
      background: #145c43; color: white; font: inherit; font-weight: 700; cursor: pointer; }
    button:disabled { cursor: wait; opacity: .55; }
    #status { min-height: 1.5rem; margin-top: 1rem; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #17211c; color: #dce9df;
      padding: 1rem; border-radius: 10px; min-height: 3rem; }
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
    </section>
  </main>
  <script>
    const fileInput = document.querySelector("#source-document");
    const editionInput = document.querySelector("#source-edition-of");
    const importButton = document.querySelector("#import-source-document");
    const status = document.querySelector("#status");
    const result = document.querySelector("#workspace-result");

    /**
     * Inputs: none; reads no arguments and uses the Book Workspace collection endpoint.
     * Functionality: adds every retained Book Workspace as an explicit prior-edition option.
     * Outputs: Promise<void> after the selector is populated.
     * Failures: rejects when the collection request or JSON parsing fails.
     */
    async function refreshEditions() {
      const response = await fetch("/api/book-workspaces");
      const payload = await response.json();
      for (const workspace of payload.workspaces) {
        const option = document.createElement("option");
        option.value = workspace.workspace_id;
        option.textContent = `${workspace.source_document.filename} — ${workspace.workspace_id}`;
        editionInput.append(option);
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
      } catch (error) {
        status.textContent = `Import failed: ${error.message}`;
      } finally {
        importButton.disabled = false;
      }
    });

    refreshEditions().catch((error) => {
      status.textContent = `Could not list prior editions: ${error.message}`;
    });
  </script>
</body>
</html>"""
