-- Test cardio logs saved with duration 0 before blank durations were stored as NULL.
-- 1, 3, and 4 have no duration or distance; 7 is a test log.
-- Test cardio sessions with no logs: 1-6 never had any, 8 only held logs 3 and 4.
BEGIN TRANSACTION;

DELETE FROM cardio_logs WHERE id IN (1, 3, 4, 7) AND duration = 0;
DELETE FROM cardio_sessions
WHERE id IN (1, 2, 3, 4, 5, 6, 8) AND id NOT IN (SELECT cardio_session_id FROM cardio_logs);

COMMIT;
