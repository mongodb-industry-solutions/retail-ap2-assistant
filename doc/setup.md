# Setup Guide

Simple and complete ways to start the project.

---

## Option A: Simple setup with make (recommended)

This is the fastest path. Targets use **`namespace:action`** (for example `model:select`, `run:dev`). Variables use **camelCase** with **no spaces** around `=`: `modelName=phi-2`, `huggingfaceRepo=...`, `fileName=...`, optional `forceDownload=1`.

### Bash / Git Bash / WSL

```bash
make setup
make model:select modelName=phi-2
make dev
```

### Windows Command Prompt (`cmd.exe`)

1. Install **GNU Make** and ensure `make` works in CMD (Chocolatey `make`, MSYS2, or a toolset that ships `make`).
2. Go to the repository root (where `Makefile` is):

```bat
cd /d C:\path\to\mongodb-assistant
```

3. Run the same logical sequence as above (aliases like `setup` and `dev` work):

```bat
make setup
make model:select modelName=phi-2
make run:dev
```

**Useful model commands in CMD:**

```bat
make model:list
make model:download
make model:select modelName=phi-2
make model:select modelName=phi-2 forceDownload=1
make model:custom huggingfaceRepo=TheBloke/phi-2-GGUF fileName=phi-2.Q4_K_M.gguf
make model:remove modelName=phi-2
make model:remove fileName=custom.gguf
make model:clean
make help
```

If a value breaks parsing in CMD, call the CLI directly (from repo root):

```bat
python bin\download.py --list
python bin\download.py --model phi-2
python bin\download.py --force --model phi-2
```

Verify:
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

What `make setup` does (same as `make project:setup`):
- Creates `venv/`
- Installs dependencies inside `venv/`
- Creates `cfg/.env` from `cfg/.env.example` if missing

---

## Option B: Full manual setup without make

Use this path if you want full control.

### 1) Create virtual environment

```bash
python -m venv venv
```

### 2) Activate virtual environment

Windows (PowerShell):
```bash
.\venv\Scripts\Activate.ps1
```

Linux/macOS:
```bash
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Create local environment file

Windows (PowerShell):
```bash
copy cfg\.env.example cfg\.env
```

Linux/macOS:
```bash
cp cfg/.env.example cfg/.env
```

### 5) Download a local model

Implementation: `bin/download.py` (CLI) uses **`ModelDownloadService`** in `src/services/modelDownloadService.py`.

Catalog model (skips download if the file already exists; use `--force` to re-download):

```bash
python bin/download.py --model phi-2
```

Windows CMD:

```bat
python bin\download.py --model phi-2
```

List catalog and on-disk files:

```bash
python bin/download.py --list
```

Remove one catalog model file or clean `models/`:

```bash
python bin/download.py --remove phi-2
python bin/download.py --remove-file custom.gguf
python bin/download.py --clean
```

### 6) Start the API server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Windows CMD (venv active):

```bat
venv\Scripts\uvicorn.exe src.main:app --reload --host 0.0.0.0 --port 8000
```

### 7) Verify

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

### Lint and format (optional)

With **make**: `make lint` (Ruff check), `make format` (Ruff format), `make check` (lint + format check + tests). See [code-quality.md](code-quality.md).

---

## Notes

- If you use Option A, you do not need to manually activate `venv` for project commands.
- If you use Option B, activate `venv` every new terminal session.
- `cfg/.env` controls providers and runtime settings (`LLM_PROVIDER`, `WORKFLOW_PROVIDER`, and model path).
- Static analysis and formatting use **Ruff** (`pyproject.toml`, `requirements.txt`); see [code-quality.md](code-quality.md).
