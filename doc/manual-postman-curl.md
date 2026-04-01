# Manual API tests (Postman and curl)

Use these examples once the API is running (for example `make dev`). Default URL and port match the project Makefile: **`http://localhost:8000`**. Override the host or port if you set `APP_PORT` or use another binding.

---

## Health check (GET)

No JSON body. Confirms the process is up.

**curl (Git Bash, macOS, Linux):**

```bash
curl -sS "http://localhost:8000/health"
```

**curl (Windows PowerShell, from repo root):**

```powershell
curl.exe -sS "http://localhost:8000/health"
```

Expected response:

```json
{"status":"ok"}
```

---

## List workflows (GET `/api/workflows`)

Returns all available workflows as lightweight summaries (`workflowId` + `description`). The source depends on `WORKFLOW_PROVIDER` (`JSON` files or MongoDB).

**curl:**

```bash
curl -sS "http://localhost:8000/api/workflows"
```

**PowerShell:**

```powershell
curl.exe -sS "http://localhost:8000/api/workflows"
```

Expected response:

```json
[
  { "workflowId": "happy_path", "description": "..." },
  { "workflowId": "straightforward", "description": "This workflow defines a guided purchase interaction..." }
]
```

Also available via Make: `make workflow:list`.

---

## Process workflow (POST `/api/process`)

| Field | Type | Notes |
|--------|------|--------|
| `workflowId` | string | Must match a file `cfg/workflows/{workflowId}.json` (e.g. `straightforward`). |
| `conversation` | array | Each item: `role` (`user` \| `agent`), `message` (string). Optional `step` (string) is accepted but usually omitted from clients. |
| `maxAnswers` | integer | Optional; default `2`. Minimum `1`. |

```json
{
  "workflowId": "straightforward",
  "conversation": [
    {
      "role": "user",
      "message": "Hey, I want to purchase something today!"
    },
    {
      "role": "agent",
      "message": "Hello! I can help you with that. To start, please tell me what item you are looking for."
    }
  ],
  "maxAnswers": 2
}

```
The workflow definition expects the **last** message in `conversation` to be from the **`agent`**, so the model can classify the step and suggest user replies.

Response shape:

```json
{
  "workflowId": "straightforward",
  "stepId": "shopping-agent-introduction",
  "answers": ["…", "…"]
}
```

### Example 1 — Opening turn (minimal)

Body file: [requests/example-process-opening.json](requests/example-process-opening.json)

**curl (from repository root):**

```bash
curl -sS -X POST "http://localhost:8000/api/process" \
  -H "Content-Type: application/json" \
  --data-binary "@doc/requests/example-process-opening.json"
```

**One-line curl with inline JSON** (same payload, useful if you do not rely on files):

```bash
curl -sS -X POST "http://localhost:8000/api/process" -H "Content-Type: application/json" -d "{\"workflowId\":\"straightforward\",\"conversation\":[{\"role\":\"user\",\"message\":\"Hey, I want to purchase something today!\"},{\"role\":\"agent\",\"message\":\"Hello! I can help you with that. To start, please tell me what item you are looking for.\"}],\"maxAnswers\":2}"
```

### Example 2 — Mid-flow (after product choice, agent asks wallet vs address)

Body file: [requests/example-process-mid-flow.json](requests/example-process-mid-flow.json)  
Derived from the supervised conversation in `cfg/conversations/straightforward.json` (prefix through the agent turn after the user picks option 2; `step` fields removed). The last message is the agent asking whether to use a digital wallet or enter the shipping address manually.

**curl (from repository root):**

```bash
curl -sS -X POST "http://localhost:8000/api/process" \
  -H "Content-Type: application/json" \
  --data-binary "@doc/requests/example-process-mid-flow.json"
```

---

## Postman

1. **Import from cURL:** **Import** → **Raw text** → paste one of the `curl` commands above → continue. Postman will create a request with URL, method, headers, and body (for `--data-binary @file`, either paste the JSON from the matching file under `doc/requests/` into **Body → raw → JSON**, or use **Import** after replacing `@doc/requests/...` with the file contents).
2. **Manual:** **POST** `http://localhost:8000/api/process` → **Headers** `Content-Type: application/json` → **Body** → **raw** → **JSON** → paste the contents of `example-process-opening.json` or `example-process-mid-flow.json`.

---

## Common HTTP outcomes

| Status | Typical cause |
|--------|----------------|
| **200** | Success; body is `ProcessResponse`. |
| **404** | Unknown `workflowId` (no matching workflow file or provider error). |
| **422** | Invalid JSON body, validation error (`maxAnswers` below 1, missing `workflowId`, etc.), or LLM output could not be parsed (`ValueError` from the LLM service). |
| **500** | Unexpected server error. |

Interactive docs: `http://localhost:8000/docs`.
