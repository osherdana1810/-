# CLAUDE.md - אחריותי (Warranty Manager)

## What this project is
"אחריותי" is a warranty and receipt manager for young families. Users upload receipts or warranty cards, an AI reads product name, purchase date, warranty period and price, the user confirms, and the app tracks expiry dates and shows reminders. The full product spec is in `אפיון חדש.md` (Hebrew). Treat it as the source of truth for product behavior.

## Stack
- Python 3.12, Streamlit UI (`app.py`), SQLite (`core/db.py`).
- Claude API via the `anthropic` SDK for extraction and Q&A. Default model in `core/ai_extract.py`, overridable with `CLAUDE_MODEL`.
- Tests: pytest (`pytest.ini` sets `pythonpath = .`).

## Layout
- `app.py` - Streamlit entry point and all screens. Run: `streamlit run app.py`.
- `core/` - logic with no Streamlit imports: `warranty.py` (date math/status), `db.py`, `storage.py`, `ai_extract.py`, `ai_assistant.py`, `letters.py`, `reminders.py`.
- `tests/` - unit tests for core logic.
- `data/` - runtime SQLite file and uploads. Gitignored, never commit.
- `.env` - secrets (`ANTHROPIC_API_KEY`). Gitignored. Template in `.env.example`.

## Commands
- Install: `python -m pip install -r requirements.txt`
- Test: `python -m pytest -q`
- Run app: `python -m streamlit run app.py`

## Conventions
- Keep UI text in Hebrew (RTL). Code comments and identifiers in English.
- Put business logic in `core/`, keep `app.py` as thin UI wiring.
- AI output is untrusted: parse it defensively, treat missing values as `None`, and never guess warranty coverage. The assistant must say when it cannot determine an answer and always show the disclaimer.
- Letters are drafts only. The app must never send anything to a store or service center without explicit user action.
- Uploaded files get random names. Do not log file contents or API keys.
- Add or update a test for any change to `core/`.

## Git workflow
- `main` - stable releases only.
- `dev` - integration branch; feature work merges here first.
- Create feature branches from `dev` and merge back into `dev` through a pull request. Merge `dev` into `main` when a version is ready.
- Never commit `.env`, `data/`, or uploaded documents.

## Privacy
This app handles family purchase records. Do not add analytics or third-party calls beyond the Claude API without updating the privacy text in the Settings screen and the spec.
