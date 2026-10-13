# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FitnessLogger is a Flask + SQLite web app for logging weightlifting workouts and cardio sessions. No frontend framework — server-rendered Jinja templates, vanilla CSS/HTML. No test suite exists yet.

## Running the app

```bash
source venv/bin/activate
pip install -r requirements.txt
FLASK_ENV=development python app.py    # runs on http://127.0.0.1:5000, debug=True
# or: FLASK_ENV=development flask run --debug
```

Plain `flask run` (no `--debug`) skips the `app.run(debug=True)` block, so templates and code are cached and edits won't show until restart.

`FLASK_ENV` selects config and database:
- Unset or `production` → `ProdConfig`, `fitnesslogger.db`
- Anything else (e.g. `development`) → `DevConfig`, `dev.db`

`app.py` is the only place `FLASK_ENV` is read; it resolves `DevConfig`/`ProdConfig` once via `app.config.from_object(...)`. Everything else (including `utils/db.py`) reads resolved values off Flask's `current_app.config` at call time rather than re-deriving them — don't reintroduce a second `FLASK_ENV` branch elsewhere.

Secrets (`SECRET_KEY`, `RESEND_API_KEY`) load from `.env` via `config.py`. Transactional email (verification, password reset, forgot-username) goes through Resend.

## Architecture

**File layout** (non-route modules live in the `utils/` package):
- `app.py` — all Flask routes (auth, weightlifting, cardio), each `@login_required` except auth/landing routes. No blueprints; one flat file.
- `utils/db.py` — every DB access function (including auth-token save/verify), imported into `app.py` with `from utils.db import *`.
- `utils/email_service.py` — Resend calls for verification, password-reset, and forgot-username emails.
- `utils/session_helpers.py` — non-DB helpers: token generation, duration math, grouping session data for inserts (`group_sets`/`group_logs`), and the `clear_*` session-pruning functions.
- `utils/user_class.py` — Flask-Login `User` model.
- `config.py` — `DevConfig`/`ProdConfig` pick DB path, base URL, and cookie security settings.

**DB connection pattern:** `db_connection()` in `utils/db.py` is a context manager used as `with db_connection() as (conn, c):`. It reads `DB_PATH` off `current_app.config` (raising `FileNotFoundError` if the file is missing), opens a sqlite3 connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`, commits on clean exit (including an early `return`), rolls back on exception, and always closes. Each helper opens its own connection this way and never commits/closes manually; multi-statement writes that must be atomic (e.g. `create_workout`, `update_password` clearing the reset token) happen inside one helper's `with` block. No pooling or app-level teardown hook. Read helpers return `sqlite3.Row` (or lists of them); write helpers that target a single row return `c.rowcount == 1`. A few routes (`edit_workout`, `edit_cardio_session`) still use `db_connection()` directly for inline SQL.

**Multi-step logging flow via Flask session:** Logging a workout or cardio session is a multi-request wizard, not a single form post. `log_workout`/`log_cardio` accumulate entries into `session['current_sets']` / `session['current_logs']` across POSTs (`add_set`/`add_log`), then persist everything to the DB on `finish_workout`/`finish_session`, clearing session state afterward via `clear_workout_session()`/`clear_cardio_session()` etc. When editing these routes, keep the session-key names in `app.py` and the corresponding `clear_*` functions in `utils/session_helpers.py` in sync — an unpruned session key silently reappears on the next visit.

**Standard vs. custom entities:** Exercises and cardio types each have a global table (`exercises`, `cardio_types`) and a per-user table (`custom_exercises`, `custom_cardio`). Logs reference one or the other via nullable FK pairs (`exercise_id`/`custom_exercise_id`, `cardio_type_id`/`custom_cardio_id`) enforced by CHECK constraints requiring exactly one to be set. Queries that display logs `LEFT JOIN` both tables and `COALESCE` the name (see `get_workout`, `get_cardio_session`).

**Schema:** `schema.sql` is the current schema reference (gitignored — not tracked, so don't assume it reflects what's actually in `main`/prod). Actual schema history lives in `migrations/`, applied as sequential numbered files. `migrationsbestpractices.txt` documents the required workflow for schema changes:
- Structural changes (renames, type changes, constraints, dropping `AUTOINCREMENT`) require a full table rebuild: create new table → `INSERT...SELECT` with explicit column mapping → drop old → rename into place. SQLite can't do these in place.
- Wrap each migration in `BEGIN TRANSACTION`/`COMMIT`; toggle `PRAGMA foreign_keys = OFF/ON` outside that transaction, bracketing it.
- Rebuild the parent table and every child table whose FK names a renamed column, in dependency order.
- Test on a copy of `dev.db` first (`PRAGMA foreign_key_check`, row-count comparisons, `.bail on`) before touching prod, and back up prod's DB before running migrations there.

**Backup:** `scripts/backup.py` uses SQLite's online backup API to snapshot the prod DB to a timestamped file; paths are hardcoded to a specific deploy host, not portable as-is.

## Known rough edges (from TODO.md / in-code TODOs)

`TODO.md` (Refactors / Features / Bugs) is the parking lot for deferred work.

- `edit_workout` in `app.py` has a large dead/commented-out block for exercise-name editing left mid-refactor — don't assume it's live code. It and `edit_cardio_session` also do raw SQL inline instead of going through `utils/db.py`.
- Prefer catching specific exceptions (e.g. `sqlite3.IntegrityError`) over broad `sqlite3.Error`/`Exception` catches; `edit_workout` still has a broad one.
- The eventual direction is toward an app-factory + Blueprints structure — don't assume the current flat single-file layout is the intended end state, but don't restructure unprompted either.
