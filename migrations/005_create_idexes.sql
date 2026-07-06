BEGIN TRANSACTION;

CREATE INDEX idx_workout_logs_session ON workout_logs(session_id);
CREATE INDEX idx_workout_sets_log ON workout_sets(workout_log_id);
CREATE INDEX idx_cardio_logs_session ON cardio_logs(cardio_session_id);
CREATE INDEX idx_workout_sessions_user ON workout_sessions(user_id);
CREATE INDEX idx_cardio_sessions_user ON cardio_sessions(user_id);

COMMIT;