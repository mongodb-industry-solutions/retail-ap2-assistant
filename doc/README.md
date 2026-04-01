# Documentation

Detailed documentation for the Conversational Assistance System.

---

## 🚀 Get Started (Simple)

1) Prepare the project:

```bash
make setup
```

2) Download one model and run the server:

```bash
make model:select modelName=phi-2
make dev
```

(`make run:dev` is the same as `make dev`. On **Windows CMD**, run these from the repo root with GNU Make on your `PATH`; see [setup.md](setup.md) for `cmd.exe` examples.)

3) Verify the API:
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

Need manual setup without `make`? See [setup.md](setup.md).

---

## Guides

| Document | Description |
|----------|-------------|
| [setup.md](setup.md) | Complete setup guide: simple path with `make` and full manual path without `make` |
| [llm.md](llm.md) | Local LLM deployment: **in-process** (`llama-cpp-python`) vs **external servers** (e.g. Ollama); how this relates to LangChain |
| [manual-postman-curl.md](manual-postman-curl.md) | Manual tests: **curl** and Postman for `/health`, `/api/workflows`, and `/api/process`, with JSON examples under [requests/](requests/) |
| [code-quality.md](code-quality.md) | **Ruff**: lint, format, `pyproject.toml`, and Make targets (`quality:lint`, `quality:format`, `quality:check`) |

---

## Architecture Overview

The system follows a layered architecture with Dependency Injection (DI):

```
Controllers (HTTP) -> Services (Business Logic) -> Providers (Data/LLM)
```

All components are class-based (OOP). Abstract interfaces define contracts; concrete implementations are resolved at runtime by `ServiceFactory`.

## Workflow Providers

### JSON Provider (LOCAL)

- **Class**: `WorkflowJsonService`
- **Source**: JSON files in `cfg/workflows/`
- **Config**: `WORKFLOW_PROVIDER=JSON`, `WORKFLOW_DIR=cfg/workflows`
- **Usage**: Default provider. Each workflow is a `.json` file named by its `workflowId`.

### MongoDB Provider (REMOTE)

- **Class**: `WorkflowMdbService`
- **Source**: MongoDB collection
- **Config**: `WORKFLOW_PROVIDER=MDB`, `MDB_URI`, `MDB_DATABASE_NAME`, `MDB_COLLECTION_NAME`
- **Usage**: Documents must have a `workflowId` field matching the requested ID.
- **Import**: `make workflow:import` upserts `cfg/workflows/*.json` into MongoDB (`bin/import_workflows.py`). Use `make workflow:importDryRun` to preview.

## LLM Providers

| Provider | Class | SDK | JSON enforced |
|----------|-------|-----|---------------|
| `LOCAL` (default) | `LlmLocalService` | `llama-cpp-python` + LangChain | No |
| `REMOTE` | `LlmRemoteService` | LangChain `ChatGoogleGenerativeAI` | No |
| `VERTEXAI` | `LlmVertexAiService` | `google-genai` (direct) | Yes (`response_mime_type`) |

### Google Generative AI / Vertex via LangChain (REMOTE)

- **Class**: `LlmRemoteService`
- **Model**: `ChatGoogleGenerativeAI` from `langchain-google-genai` (default model `gemini-2.5-flash`, overridable with `GOOGLE_MODEL_ID`)
- **Config**: `LLM_PROVIDER=REMOTE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` (default `us-central1`). Without project: developer API using `GOOGLE_API_KEY` (see LangChain docs).
- **Auth**: ADC for Vertex; API key env vars for developer API

### Google Generative AI / Vertex via direct SDK (VERTEXAI)

- **Class**: `LlmVertexAiService`
- **SDK**: `google-genai` (`genai.Client`) — no LangChain wrapper
- **Model**: default `gemini-2.5-flash`, overridable with `GOOGLE_MODEL_ID`
- **Config**: `LLM_PROVIDER=VERTEXAI` plus either `GOOGLE_API_KEY` (API key mode) or `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` (Vertex AI / ADC mode)
- **Key advantage**: sets `response_mime_type="application/json"` so the model is forced to return valid JSON — no markdown fences, no extra text, no post-processing

### Local Model (LOCAL)

- **Class**: `LlmLocalService`
- **Model**: `mistral-7b-instruct-v0.2.Q4_K_M.gguf` (quantized GGUF)
- **Runtime**: `llama-cpp-python` + LangChain `LlamaCpp`
- **Config**: `LLM_PROVIDER=LOCAL`, `LLM_LOCAL_MODEL_PATH`, `LLM_LOCAL_MODEL_N_CTX`, `LLM_LOCAL_MODEL_N_THREADS`, `LLM_LOCAL_MODEL_TEMPERATURE`, `LLM_PROMPT_FORMAT` (`text` default, or `json` to send workflow + conversation as structured JSON in the prompt)
- **Storage**: Place the `.gguf` file in the `models/` directory

### Downloading Models

Models are managed through `cfg/models.json` (catalog), **`bin/download.py`** (CLI), and **`ModelDownloadService`** in `src/services/modelDownloadService.py`.

**Automated download with Make (bash or CMD):**
```bash
make model:download
make model:list
make model:select modelName=phi-2
make model:remove modelName=phi-2
make model:clean
```

Optional: `make model:select modelName=phi-2 forceDownload=1` to re-download. See [setup.md](setup.md) for **Windows CMD** one-liners and quoting tips.

**Manual download:**
1. Download from Hugging Face (e.g. `https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF`)
2. Choose the `Q4_K_M` quantization for best balance of quality and performance.
3. Place the file in `models/` directory.
4. Update `LLM_LOCAL_MODEL_PATH` in `cfg/.env`.

**Custom model from any Hugging Face repo:**
```bash
make model:custom huggingfaceRepo=TheBloke/Model-GGUF fileName=model.Q4_K_M.gguf
```

The download script automatically updates `cfg/.env` with the correct model path.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workflows` | List all available workflows (summaries: `workflowId` + `description`) |
| `POST` | `/api/process` | Analyse conversation against a workflow; returns `stepId` + suggested user replies |
| `GET` | `/health` | Health check |
| `GET` | `/` | Redirects to `/docs` (Swagger UI) |

## Workflow JSON Schema

Each workflow file must follow this structure:

```json
{
  "workflowId": "string",
  "description": "string",
  "goals": ["string"],
  "policies": ["string"],
  "steps": [
    { "id": "string", "description": "string" }
  ]
}
```

## Design Patterns Used

| Pattern | Where | Purpose |
|---|---|---|
| **Abstract Factory** | `ServiceFactory` | Resolves concrete providers from env config |
| **Strategy** | `WorkflowService` / `LlmService` | Same interface, different implementations |
| **Singleton** | LLM model loading | Load expensive model once at init |
| **Composition** | `WorkflowController` | Injects services via constructor |
