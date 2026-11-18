-- Block duplicate custom cardio names per user. The cardio type dropdowns map name -> id, so a
-- duplicate name hid the earlier cardio type. NOCASE treats "Stair Sprints" and "stair sprints" as the same.
BEGIN TRANSACTION;

CREATE UNIQUE INDEX idx_custom_cardio_user_cardio_type
ON custom_cardio(user_id, cardio_type COLLATE NOCASE);

COMMIT;
