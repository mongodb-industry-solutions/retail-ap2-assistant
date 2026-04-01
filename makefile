# ============================================================================
# Conversational Assistance System - Project Commands
# ============================================================================
# Targets use namespace:action (colon). Example: make model:select modelName=phi-2
# Short aliases: setup, dev, test, install (see bottom).
# ============================================================================

.DEFAULT_GOAL := help
BASE_PYTHON := python3
VENV_DIR := venv
ifeq ($(OS),Windows_NT)
VENV_BIN := $(VENV_DIR)/Scripts
VENV_PYTHON := $(VENV_BIN)/python.exe
VENV_PIP := $(VENV_BIN)/pip.exe
VENV_UVICORN := $(VENV_BIN)/uvicorn.exe
VENV_PYTEST := $(VENV_BIN)/pytest.exe
else
VENV_BIN := $(VENV_DIR)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip
VENV_UVICORN := $(VENV_BIN)/uvicorn
VENV_PYTEST := $(VENV_BIN)/pytest
endif
PYTHON := $(VENV_PYTHON)
PIP := $(VENV_PIP)
UVICORN := $(VENV_UVICORN)
PYTEST := $(VENV_PYTEST)
APP_MODULE := src.main:app
APP_PORT := 8000
ENV_FILE := cfg/.env
ENV_EXAMPLE := cfg/.env.example

# ---- Dependencies ---------------------------------------------------------

.PHONY: deps\:venv
deps\:venv: ## Create Python virtual environment
	$(BASE_PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment ready in $(VENV_DIR)"

.PHONY: deps\:install
deps\:install: deps\:venv ## Install dependencies into venv
	$(PIP) install -r requirements.txt

.PHONY: deps\:installDev
deps\:installDev: deps\:install ## Same as deps:install (pytest and ruff are in requirements.txt)
	@echo "Dev tooling is listed in requirements.txt (no extra pip step)."

# ---- Project --------------------------------------------------------------

.PHONY: project\:env
project\:env: ## Create cfg/.env from example if it does not exist
	@$(BASE_PYTHON) -c "from pathlib import Path; import shutil; env=Path(r'$(ENV_FILE)'); ex=Path(r'$(ENV_EXAMPLE)'); exists=env.exists(); (print(f'{env} already exists, skipping.') if exists else (shutil.copyfile(ex, env), print(f'Created {env} from {ex}')))"

.PHONY: project\:setup
project\:setup: deps\:install project\:env ## Full setup: venv, deps, and .env
	@echo "Setup complete. Edit cfg/.env with your settings."

.PHONY: project\:info
project\:info: ## Print cfg/.env (non-comments), models dir, Python version
	@echo "=== Environment ==="
	@$(BASE_PYTHON) -c "from pathlib import Path; p=Path(r'$(ENV_FILE)'); print(''.join(l+'\n' for l in p.read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')) if p.exists() else 'No cfg/.env. Run make project:env.\n')"
	@echo ""
	@echo "=== Models ==="
	@$(BASE_PYTHON) -c "import os, pathlib as P; d=P.Path('models'); f=sorted([p for p in d.glob('*') if p.is_file() and p.suffix.lower() in ('.gguf','.bin')]) if d.exists() else []; print(os.linesep.join('  %%s  (%%s MB)'%%(p.name,p.stat().st_size//1024//1024) for p in f) if f else '  No models. Run make model:download.')"
	@echo ""
	@echo "=== Python ==="
	@$(PYTHON) --version

.PHONY: project\:clean
project\:clean: ## Remove __pycache__, .pytest_cache, and *.pyc under project
	@$(BASE_PYTHON) -c "import shutil; from pathlib import Path; r=Path('.'); [shutil.rmtree(p,ignore_errors=True) for p in r.rglob('__pycache__') if p.is_dir()]; [shutil.rmtree(p,ignore_errors=True) for p in r.rglob('.pytest_cache') if p.is_dir()]; [p.unlink(missing_ok=True) for p in r.rglob('*.pyc')]"
	@echo "Cleaned Python caches."

# ---- Run ------------------------------------------------------------------

.PHONY: run\:dev
run\:dev: ## Start API in development mode (auto-reload); port from APP_PORT (default 8000)
	$(UVICORN) $(APP_MODULE) --reload --host 0.0.0.0 --port $(APP_PORT)

.PHONY: run\:start
run\:start: ## Start API in production mode; port from APP_PORT (default 8000)
	$(UVICORN) $(APP_MODULE) --host 0.0.0.0 --port $(APP_PORT)

.PHONY: run\:health
run\:health: ## Check GET /health (requires curl); port from APP_PORT
	@curl -s http://localhost:$(APP_PORT)/health | $(PYTHON) -m json.tool 2>/dev/null || echo "Server is not running."

# ---- Models ---------------------------------------------------------------

.PHONY: model\:download
model\:download: ## Download default catalog model (skips if already on disk)
	$(BASE_PYTHON) bin/download.py

.PHONY: model\:list
model\:list: ## List catalog entries and files in models/
	$(BASE_PYTHON) bin/download.py --list

.PHONY: model\:select
model\:select: ## Download catalog model: make model:select modelName=phi-2
ifndef modelName
	$(error Usage: make model:select modelName=<catalog-key> - see make model:list)
endif
	$(BASE_PYTHON) bin/download.py --model "$(modelName)" $(if $(strip $(forceDownload)),--force,)

.PHONY: model\:custom
model\:custom: ## Download custom Hugging Face file: huggingfaceRepo=... fileName=...
ifndef huggingfaceRepo
	$(error Usage: make model:custom huggingfaceRepo=TheBloke/Model-GGUF fileName=model.Q4_K_M.gguf)
endif
ifndef fileName
	$(error Usage: make model:custom huggingfaceRepo=TheBloke/Model-GGUF fileName=model.Q4_K_M.gguf)
endif
	$(BASE_PYTHON) bin/download.py --repo "$(huggingfaceRepo)" --file "$(fileName)" $(if $(strip $(forceDownload)),--force,)

.PHONY: model\:remove
model\:remove: ## Remove one file: modelName=<catalog> OR fileName=<basename>
ifdef modelName
	$(BASE_PYTHON) bin/download.py --remove "$(modelName)"
else
ifdef fileName
	$(BASE_PYTHON) bin/download.py --remove-file "$(fileName)"
else
	$(error Usage: make model:remove modelName=<catalog-key> OR fileName=<file.gguf>)
endif
endif

.PHONY: model\:clean
model\:clean: ## Delete all .gguf and .bin files under models/
	$(BASE_PYTHON) bin/download.py --clean

# ---- Workflows --------------------------------------------------------------

.PHONY: workflow\:import
workflow\:import: ## Import cfg/workflows/*.json into MongoDB (uses MDB_* from cfg/.env)
	$(PYTHON) bin/import_workflows.py

.PHONY: workflow\:importDryRun
workflow\:importDryRun: ## Show which workflows would be imported (no DB write)
	$(PYTHON) bin/import_workflows.py --dry-run

.PHONY: workflow\:list
workflow\:list: ## List workflows via GET /api/workflows (requires running server)
	@curl -s http://localhost:$(APP_PORT)/api/workflows | $(PYTHON) -m json.tool 2>/dev/null || echo "Server is not running."

# ---- Test ------------------------------------------------------------------

.PHONY: test\:run
test\:run: ## Run pytest on tests/
	$(PYTEST) tests/ -v

.PHONY: test\:cov
test\:cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=src --cov-report=term-missing

.PHONY: test\:watch
test\:watch: ## Run tests in watch mode (requires pytest-watch)
	ptw tests/ -- -v

# ---- Quality ----------------------------------------------------------------

.PHONY: quality\:lint
quality\:lint: ## Static analysis: ruff check on src/ and tests/
	$(PYTHON) -m ruff check src/ tests/

.PHONY: quality\:format
quality\:format: ## Auto-format with ruff format
	$(PYTHON) -m ruff format src/ tests/

.PHONY: quality\:formatCheck
quality\:formatCheck: ## Fail if code is not formatted (CI-friendly)
	$(PYTHON) -m ruff format --check src/ tests/

.PHONY: quality\:check
quality\:check: quality\:lint quality\:formatCheck test\:run ## Lint + format check + tests

# ---- Help & aliases ---------------------------------------------------------

.PHONY: help
help: ## Show main targets (type colons as shown; GNU Make uses model\:name in the file)
	@echo ""
	@echo "Examples:"
	@echo "  make project:setup"
	@echo "  make model:select modelName=phi-2   (optional: forceDownload=1 to re-download)"
	@echo "  make model:custom huggingfaceRepo=TheBloke/phi-2-GGUF fileName=phi-2.Q4_K_M.gguf"
	@echo "  make model:remove modelName=phi-2   OR   make model:remove fileName=foo.gguf"
	@echo "  make model:clean"
	@echo "  make run:dev    (default port $(APP_PORT); override: make run:dev APP_PORT=8080)"
	@echo "  make test:run"
	@echo ""
	@echo "Groups:  deps:venv deps:install deps:installDev"
	@echo "         project:setup project:env project:info project:clean"
	@echo "         run:dev run:start run:health"
	@echo "         model:download model:list model:select model:custom model:remove model:clean"
	@echo "         workflow:import workflow:importDryRun workflow:list"
	@echo "         test:run test:cov test:watch"
	@echo "         quality:lint quality:format quality:formatCheck quality:check"
	@echo ""
	@echo "Aliases: setup install dev start test check lint format clean health"
	@echo ""

.PHONY: install setup dev start test check lint format test-cov clean-models
install: deps\:install
setup: project\:setup
dev: run\:dev
start: run\:start
test: test\:run
test-cov: test\:cov
check: quality\:check
lint: quality\:lint
format: quality\:format

.PHONY: clean
clean: project\:clean

clean-models: model\:clean

.PHONY: health
health: run\:health
