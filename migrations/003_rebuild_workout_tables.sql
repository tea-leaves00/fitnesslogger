-- Rebuild workout_sessions, workout_sets, and custom_exercises tables
-- Dropping auto-increments for performance
-- Renaming columns such as exercise_name and also adding date checks

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ===== workout sessions =====
CREATE TABLE workout_sessions_new (
    id INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,
    session_notes TEXT,
    user_id INTEGER REFERENCES users(id),
    CHECK (date(session_date) IS NOT NULL)
);

INSERT INTO workout_sessions_new (id, session_date, session_notes, user_id)
SELECT id, session_date, session_notes, user_id FROM workout_sessions;

DROP TABLE workout_sessions;
ALTER TABLE workout_sessions_new RENAME TO workout_sessions;

-- ===== workout sets =====
CREATE TABLE workout_sets_new (
    id INTEGER PRIMARY KEY,
    workout_log_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    reps INTEGER NOT NULL, -- houses time (in seconds) as well
    weight REAL,  -- NULL for bodyweight exercises
    FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id) ON DELETE CASCADE
);

INSERT INTO workout_sets_new (id, workout_log_id, set_number, reps, weight)
SELECT id, workout_log_id, set_number, reps, weight FROM workout_sets;

DROP TABLE workout_sets;
ALTER TABLE workout_sets_new RENAME TO workout_sets;

-- ===== custom exercises =====
CREATE TABLE custom_exercises_new (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    exercise TEXT NOT NULL, 
    is_time_based INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO custom_exercises_new (id, user_id, exercise, is_time_based)
SELECT id, user_id, exercise_name, is_time_based FROM custom_exercises;

DROP TABLE custom_exercises;
ALTER TABLE custom_exercises_new RENAME TO custom_exercises;

COMMIT;

PRAGMA foreign_keys = ON;
