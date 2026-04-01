# Code quality (Ruff)

The project uses **[Ruff](https://docs.astral.sh/ruff/)** for static analysis and formatting. Ruff replaces separate tools such as Flake8, isort, and Black for day-to-day use: one fast binary, one configuration file.

## Configuration

- **`pyproject.toml`** — `[tool.ruff]`, `[tool.ruff.lint]`, and `[tool.ruff.format]` define target Python version (3.10), rules (`E`, `W`, `F`, `I`, `UP`, `B`), and format options.
- **`requirements.txt`** includes `ruff` so a normal `make setup` / `pip install -r requirements.txt` installs it in the virtual environment.

## Make targets

| Target | Purpose |
|--------|---------|
| `make quality:lint` | `ruff check` on `src/` and `tests/` (errors only exit non-zero). |
| `make quality:format` | `ruff format` — rewrite files in place. |
| `make quality:formatCheck` | `ruff format --check` — CI-friendly; fails if anything would change. |
| `make quality:check` | Lint + format check + `pytest` (same as `make check`). |

Aliases: `make lint`, `make format`, `make check`.

## Command line (without Make)

From the repo root, with `venv` active:

```bash
python -m ruff check src tests
python -m ruff check src tests --fix
python -m ruff format src tests
python -m ruff format --check src tests
```

## Editor integration

Install the **Ruff** extension for VS Code / Cursor to get diagnostics and format-on-save using the repo’s `pyproject.toml`. Alternatively, run `make quality:format` before committing.

## CI suggestion

Run `make quality:check` (or `ruff check`, `ruff format --check`, then `pytest`) on every push or pull request.
