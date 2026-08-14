# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FitnessLogger is a Flask + SQLite web app for logging weightlifting workouts and cardio sessions. No frontend framework — server-rendered Jinja templates, vanilla CSS/HTML. No test suite exists yet.

## Running the app

```bash
source venv/bin/activate
pip install -r requirements.txt
FLASK_ENV=development python app.py    # runs on http://127.0.0.1:5000, debug=True
```

`FLASK_ENV` selects config and database:
- Unset or `production` → `ProdConfig`, `fitnesslogger.db`
- Anything else (e.g. `development`) → `DevConfig`, `dev.db`

`app.py` is the only place `FLASK_ENV` is read; it resolves `DevConfig`/`ProdConfig` once via `app.config.from_object(...)`. Everything else (including `sql_functions.py`) reads resolved values off Flask's `current_app.config` at call time rather than re-deriving them — don't reintroduce a second `FLASK_ENV` branch elsewhere.

Secrets (`SECRET_KEY`, `RESEND_API_KEY`) load from `.env` via `config.py`. Transactional email (verification, password reset, forgot-username) goes through Resend.

## Architecture

**Everything routes through three files:**
- `app.py` — all Flask routes (auth, weightlifting, cardio), each `@login_required` except auth/landing routes. No blueprints; one flat file.
- `sql_functions.py` — every DB access function, imported into `app.py` with `from sql_functions import *`. This is also where email-sending and token-verification logic lives.
- `config.py` — `DevConfig`/`ProdConfig` pick DB path, base URL, and cookie security settings.

**DB connection pattern:** every `sql_functions.py` function that touches the DB calls `establish_connection()` (reads `DB_PATH` off `current_app.config`, opens a new sqlite3 connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`, and raises `FileNotFoundError` if the db file is missing) and must call `conn.close()` itself when done — there's no connection pooling or app-level teardown hook. Since `establish_connection()` always returns a valid connection or raises, callers don't need to check for `None`. When a route needs several queries in one request, it calls `establish_connection()` once and passes `c`/`conn` down into helper functions rather than each helper opening its own connection (see `log_workout`/`finish_workout` in `app.py`).

**Multi-step logging flow via Flask session:** Logging a workout or cardio session is a multi-request wizard, not a single form post. `log_workout`/`log_cardio` accumulate entries into `session['current_sets']` / `session['current_logs']` across POSTs (`add_set`/`add_log`), then persist everything to the DB on `finish_workout`/`finish_session`, clearing session state afterward via `clear_workout_session()`/`clear_cardio_session()` etc. When editing these routes, keep the session-key names in `app.py` and the corresponding `clear_*` functions in `sql_functions.py` in sync — an unpruned session key silently reappears on the next visit.

**Standard vs. custom entities:** Exercises and cardio types each have a global table (`exercises`, `cardio_types`) and a per-user table (`custom_exercises`, `custom_cardio`). Logs reference one or the other via nullable FK pairs (`exercise_id`/`custom_exercise_id`, `cardio_type_id`/`custom_cardio_id`) enforced by CHECK constraints requiring exactly one to be set. Queries that display logs `LEFT JOIN` both tables and `COALESCE` the name (see `display_workout`, `display_cardio_session`).

**Schema:** `schema.sql` is the current schema reference (gitignored — not tracked, so don't assume it reflects what's actually in `main`/prod). Actual schema history lives in `migrations/`, applied as sequential numbered files. `migrationsbestpractices.txt` documents the required workflow for schema changes:
- Structural changes (renames, type changes, constraints, dropping `AUTOINCREMENT`) require a full table rebuild: create new table → `INSERT...SELECT` with explicit column mapping → drop old → rename into place. SQLite can't do these in place.
- Wrap each migration in `BEGIN TRANSACTION`/`COMMIT`; toggle `PRAGMA foreign_keys = OFF/ON` outside that transaction, bracketing it.
- Rebuild the parent table and every child table whose FK names a renamed column, in dependency order.
- Test on a copy of `dev.db` first (`PRAGMA foreign_key_check`, row-count comparisons, `.bail on`) before touching prod, and back up prod's DB before running migrations there.

**Backup:** `scripts/backup.py` uses SQLite's online backup API to snapshot the prod DB to a timestamped file; paths are hardcoded to a specific deploy host, not portable as-is.

## Known rough edges (from notes.txt / in-code TODOs)

- `edit_workout` in `app.py` has a large dead/commented-out block for exercise-name editing left mid-refactor — don't assume it's live code.
- Several `sql_functions.py` functions catch bare `sqlite3.Error` broadly rather than the specific error; `notes.txt` flags this as intentional cleanup debt ("no Base Errors ... should always be as specific as needed"), so prefer narrowing exception handling over adding more broad catches when editing nearby code.
- The eventual direction (per `notes.txt`) is toward an app-factory + Blueprints structure and a normalized-from-scratch DB rewrite — don't assume the current flat single-file layout is the intended end state, but don't restructure unprompted either.
