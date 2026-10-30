-- Block duplicate custom exercise names per user. The exercise dropdowns map name -> id, so a
-- duplicate name hid the earlier exercise. NOCASE treats "Sled Push" and "sled push" as the same.
BEGIN TRANSACTION;

CREATE UNIQUE INDEX idx_custom_exercises_user_exercise
ON custom_exercises(user_id, exercise COLLATE NOCASE);

COMMIT;
