# Local LLM Runtime: In-Process vs External Server

This note explains how a Python app using **LangChain** can run a language model: either **inside the same process** as your application or via a **separate service**. LangChain only orchestrates calls; the **integration you choose** decides whether another process is required.

---

## Short Answer

- You do **not** need Ollama or a standalone `llama.cpp` server to run a local GGUF model from Python if you use **`llama-cpp-python`**. The library loads native `llama.cpp` code into your process and keeps weights in that process memory.
- You **do** need an external process if you point LangChain at **HTTP APIs** (for example **Ollama**’s REST API, or a self-hosted inference server). Your app then behaves like a **client**, similar to talking to a database over the network.

---

## Analogy: SQLite vs MongoDB

| Pattern | Database analogy | Local LLM analogy |
|--------|-------------------|-------------------|
| **Embedded / in-process** | **SQLite**: library runs inside your app; no separate server | **`llama-cpp-python`**: inference runs in the Python process (native code loaded via bindings) |
| **Client / server** | **MongoDB**: server process; app connects over the network | **Ollama**, **vLLM**, **TGI**, etc.: model lives in another process; app uses HTTP or gRPC |

The SQLite comparison is about **deployment shape** (one process vs two), not about identical APIs or resource usage. Models are large; in-process still means **your Python process** holds the weights and pays RAM and CPU (or GPU) cost.

---

## What LangChain Does

LangChain provides **wrappers and chains**. It does not, by itself, define whether the model is local or remote. For each backend you pick a concrete integration, for example:

- **`LlamaCpp`** (`langchain-community`): uses `llama-cpp-python` → typically **in-process** with a path to a `.gguf` file.
- **`ChatOllama` / Ollama integrations**: talk to a **running Ollama daemon** → **external process**.
- **`ChatGoogleGenerativeAI`** (Gemini / Vertex), OpenAI-compatible clients, etc.: **remote API** (cloud or another host).

So the question “must I run Ollama?” is really “which LangChain integration and which runtime did I configure?”

---

## Prompt format: `text` vs `json`

`LlmService` builds the workflow prompt using `LLM_PROMPT_FORMAT` in `cfg/.env`:

| Value | Behaviour |
|--------|------------|
| `text` (default) | Prose sections: workflow description, goals, policies, steps (bullets), then conversation lines, then output rules. Often easier for smaller local models. |
| `json` | One JSON document with `instruction`, `workflow` (description, goals, policies, steps), `conversation`, and `maxAnswers` (camelCase). Suited to models that follow structured context well (e.g. remote Gemini). |

Both modes require the model to reply with a **single JSON object** (`stepId` + `answers`, or `error`). Parsing and sanity checks are unchanged.

---

## In-Process Local Inference (No Separate Model Server)

**How it works:** `llama-cpp-python` loads a shared library that implements `llama.cpp`. When you construct the LangChain `LlamaCpp` object with `model_path=...`, the model file is mapped/loaded into **your application process**. Predictions run when you invoke the chain or LLM; no extra HTTP hop to a local daemon is required for that stack.

**Typical traits:**

- Single OS process (your FastAPI or script) owns the model.
- Startup loads the GGUF once (this project loads the local model at service init; see `tmp/agent.md` §4.2).
- Simpler deployment when you want one binary/process on a machine or container.

**Other in-process options** (not used by default in this repo) include running **PyTorch / `transformers`** fully inside Python. Trade-offs differ (dependencies, RAM, GPU use).

---

## External Model Server

**How it works:** A dedicated program loads the model and exposes an API. Your Python app sends prompts and receives tokens over **HTTP** (or similar).

**Examples:** Ollama, LM Studio server mode, text-generation-inference, vLLM.

**Typical traits:**

- Multiple clients can share one GPU server.
- You can restart or upgrade the model service without rebuilding the app (if the API stays stable).
- You must **install, start, and monitor** the extra service.

---

## Summary Table

| Setup | Separate model process? | LangChain direction |
|--------|---------------------------|---------------------|
| `llama-cpp-python` + `LlamaCpp` + local `.gguf` | **No** | File path → in-process native runtime |
| Ollama (REST) | **Yes** (Ollama) | Client to local HTTP API |
| Vertex AI / Gemini | **No local model server** | Client to Google’s API |
| Self-hosted HTTP inference | **Yes** | Client to that server |

---

## This Project (`LlmLocalService`)

With `LLM_PROVIDER=LOCAL`, the stack matches the **in-process** row: **`LlmLocalService`** uses LangChain **`LlamaCpp`** backed by **`llama-cpp-python`**. You need the GGUF on disk and Python dependencies; you do **not** need Ollama running for that configuration.

If you switched to an Ollama-based LangChain integration, you would add the **external** requirement explicitly.

---

## Related Documentation

- Architecture and providers: [doc/README.md](README.md)
