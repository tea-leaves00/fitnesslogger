-- Rebuilds exercises + muscle_groups (renames, drop AUTOINCREMENT), 
-- and dependent tables exercise_muscle_groups + workout_logs so
-- FK references stay valid after the renames.

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ===== exercises =====
CREATE TABLE exercises_new (
    id INTEGER PRIMARY KEY,
    exercise TEXT NOT NULL,
    is_time_based INTEGER DEFAULT 0
);

INSERT INTO exercises_new (id, exercise, is_time_based)
SELECT exercise_id, exercise_name, is_time_based FROM exercises;

DROP TABLE exercises;
ALTER TABLE exercises_new RENAME TO exercises;

-- ===== muscle_groups =====
CREATE TABLE muscle_groups_new (
    id INTEGER PRIMARY KEY,
    muscle_group TEXT NOT NULL
);

INSERT INTO muscle_groups_new (id, muscle_group)
SELECT muscle_group_id, muscle_group_name FROM muscle_groups;

DROP TABLE muscle_groups;
ALTER TABLE muscle_groups_new RENAME TO muscle_groups;

-- ===== exercise_muscle_groups =====
CREATE TABLE exercise_muscle_groups_new (
    id INTEGER PRIMARY KEY,
    exercise_id INTEGER NOT NULL,
    muscle_group_id INTEGER NOT NULL,
    UNIQUE (exercise_id, muscle_group_id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    FOREIGN KEY (muscle_group_id) REFERENCES muscle_groups(id)
);

INSERT INTO exercise_muscle_groups_new (id, exercise_id, muscle_group_id)
SELECT id, exercise_id, muscle_group_id FROM exercise_muscle_groups;

DROP TABLE exercise_muscle_groups;
ALTER TABLE exercise_muscle_groups_new RENAME TO exercise_muscle_groups;

-- ===== workout_logs =====
CREATE TABLE workout_logs_new (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    exercise_id INTEGER,
    custom_exercise_id INTEGER,
    exercise_notes TEXT,
    CHECK (
        (exercise_id IS NOT NULL AND custom_exercise_id IS NULL)
        OR
        (exercise_id IS NULL AND custom_exercise_id IS NOT NULL)
    ),
    FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    FOREIGN KEY (custom_exercise_id) REFERENCES custom_exercises(id)
);

INSERT INTO workout_logs_new (id, session_id, exercise_id, custom_exercise_id, exercise_notes)
SELECT id, session_id, exercise_id, custom_exercise_id, exercise_notes FROM workout_logs;

DROP TABLE workout_logs;
ALTER TABLE workout_logs_new RENAME TO workout_logs;

COMMIT;

PRAGMA foreign_keys = ON;

