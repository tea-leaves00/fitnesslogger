-- Rebuilding cardio_types, custom_cardio, cardio_sessions, cardio_logs
-- removing auto-increments from PKs for performance
-- column name changes for clarity
-- adding date CHECK

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ===== cardio types =====
CREATE TABLE cardio_types_new (
    id INTEGER PRIMARY KEY,
    cardio_type TEXT NOT NULL
);

INSERT INTO cardio_types_new (id, cardio_type)
SELECT cardio_type_id, cardio_type_name FROM cardio_types;

DROP TABLE cardio_types;
ALTER TABLE cardio_types_new RENAME TO cardio_types;

-- ===== custom cardio =====
CREATE TABLE custom_cardio_new (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    cardio_type TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO custom_cardio_new (id, user_id, cardio_type)
SELECT id, user_id, cardio_type FROM custom_cardio;

DROP TABLE custom_cardio;
ALTER TABLE custom_cardio_new RENAME TO custom_cardio;

-- ===== cardio sessions =====
CREATE TABLE cardio_sessions_new (
    id INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,
    session_notes TEXT,
    user_id INTEGER NOT NULL,
    CHECK (date(session_date) IS NOT NULL),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO cardio_sessions_new (id, session_date, session_notes, user_id)
SELECT id, session_date, session_notes, user_id FROM cardio_sessions;

DROP TABLE cardio_sessions;
ALTER TABLE cardio_sessions_new RENAME TO cardio_sessions;

-- ===== cardio logs =====
CREATE TABLE cardio_logs_new (
    id INTEGER PRIMARY KEY,
    cardio_session_id INTEGER NOT NULL,
    cardio_type_id INTEGER,
    custom_cardio_id INTEGER,
    duration INTEGER,
    distance REAL,
    distance_unit TEXT,
    intensity INTEGER,
    CHECK (intensity BETWEEN 1 AND 10),
    CHECK (
        (distance IS NULL AND distance_unit IS NULL)
        OR
        (distance IS NOT NULL AND distance_unit IS NOT NULL)
    ),
    CHECK (
        (cardio_type_id IS NOT NULL AND custom_cardio_id IS NULL)
        OR
        (cardio_type_id IS NULL AND custom_cardio_id IS NOT NULL)
    ),
    FOREIGN KEY (cardio_session_id) REFERENCES cardio_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (cardio_type_id) REFERENCES cardio_types(id),
    FOREIGN KEY (custom_cardio_id) REFERENCES custom_cardio(id)
);

INSERT INTO cardio_logs_new (id, cardio_session_id, cardio_type_id, custom_cardio_id, 
                             duration, distance, distance_unit, intensity)
SELECT id, cardio_session_id, cardio_type_id, custom_cardio_id, 
       duration, distance, distance_unit, intensity FROM cardio_logs;

DROP TABLE cardio_logs;
ALTER TABLE cardio_logs_new RENAME TO cardio_logs;

COMMIT;

PRAGMA foreign_keys = ON;