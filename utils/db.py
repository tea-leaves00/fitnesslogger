#TODO eventually implement logging module
#TODO do integrity check everynight? before copying maybe?

import sqlite3
from flask import current_app
from contextlib import contextmanager
import os


# == CONNECT  ==
@contextmanager
def db_connection():
    db_path = current_app.config['DB_PATH']
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    
    try:
        yield conn, c
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# == AUTH ==
def save_verification_token(email, token):
    with db_connection() as (conn, c):
        c.execute("""
            UPDATE users
            SET verification_token = ?, verification_token_created_at = CURRENT_TIMESTAMP
            WHERE email = ?
        """, (token, email))

def verify_user_token(token):
    with db_connection() as (conn, c):
        result = c.execute("""
            SELECT id, julianday('now') - julianday(verification_token_created_at) < 1 AS is_valid
            FROM users WHERE verification_token = ?
        """, (token,)).fetchone()
        if not result:
            return None, "Invalid token"
        if not result['is_valid']:
            return None, "Token expired"

        c.execute("""UPDATE users SET verified = 1, verification_token = NULL,
                     verification_token_created_at = NULL WHERE id = ?""", (result['id'],))
        return result['id'], "Account verified"
    
def save_reset_token(email, token):
    with db_connection() as (conn, c):
        c.execute("""
            UPDATE users
            SET reset_token = ?, reset_token_created_at = CURRENT_TIMESTAMP
            WHERE email = ?
        """, (token, email))

def verify_reset_token(token):
    with db_connection() as (conn, c):
        result = c.execute("""
            SELECT id, julianday('now') - julianday(reset_token_created_at) < 1 AS is_valid
            FROM users WHERE reset_token = ?
        """, (token,)).fetchone()
        if not result:
            return None, "Invalid token"
        if not result['is_valid']:
            return None, "Token expired"

        return result['id'], "Valid"


# == CREATE ==
def create_user(first_name, last_name, username, password_hash, email):
    with db_connection() as (conn, c):
        try:
            c.execute("INSERT INTO users (first_name, last_name, username, password_hash, email) VALUES (?, ?, ?, ?, ?)"
                        ,(first_name, last_name, username, password_hash, email))
            return True
        except sqlite3.IntegrityError:
            return False

def create_custom_exercise(user_id, exercise):
    with db_connection() as (conn, c):
        c.execute("INSERT INTO custom_exercises (user_id, exercise) VALUES (?, ?)", (user_id, exercise))

def create_custom_cardio(user_id, cardio_type):
    with db_connection() as (conn, c):
        c.execute("INSERT INTO custom_cardio (user_id, cardio_type) VALUES (?, ?)", (user_id, cardio_type))

def create_workout(session_date, session_notes, user_id, grouped_sets):
    with db_connection() as (conn, c):
        c.execute("""
                INSERT INTO workout_sessions (session_date, session_notes, user_id)
                VALUES (?, ?, ?)
                """, (session_date, session_notes if session_notes else None, user_id))
        session_id = c.lastrowid

        for exercise in grouped_sets:
            c.execute("""
                        INSERT INTO workout_logs (session_id, exercise_id, custom_exercise_id, exercise_notes)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, exercise['exercise_id'], exercise['custom_exercise_id'], exercise['exercise_notes']))
            workout_log_id = c.lastrowid

            c.executemany("""
                    INSERT INTO workout_sets (workout_log_id, set_number, reps, weight)
                    VALUES (?, ?, ?, ?)
                """, [(workout_log_id, set_number, reps, weight)
                      for set_number, reps, weight in exercise['sets']])

        return session_id

def create_cardio_session(session_date, session_notes, user_id, grouped_logs):
    with db_connection() as (conn, c):
        c.execute("""
            INSERT INTO cardio_sessions (session_date, session_notes, user_id)
            VALUES (?, ?, ?)
        """, (session_date, session_notes if session_notes else None, user_id))
        session_id = c.lastrowid

        c.executemany("""
            INSERT INTO cardio_logs (cardio_session_id, cardio_type_id, custom_cardio_id, duration, distance, distance_unit, intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(session_id, *log) for log in grouped_logs])

        return session_id


# == READ ==
def get_user(*, id=None, username=None, email=None):
    with db_connection() as (conn, c):
        user = c.execute("""SELECT id, first_name, last_name, username, email, password_hash, verified
                            FROM users
                            WHERE id = :id OR username = :username OR email = :email""",
                         {'id': id, 'username': username, 'email': email}).fetchone()
        return user

def get_exercises():
    with db_connection() as (conn, c):
        exercises = c.execute("SELECT id, exercise, is_time_based FROM exercises ORDER BY exercise").fetchall()
        return exercises

def get_custom_exercises(user_id):
    with db_connection() as (conn, c):
        custom_exercises = c.execute("SELECT id, exercise, is_time_based FROM custom_exercises WHERE user_id = ? ORDER BY exercise", (user_id,)).fetchall()
        return custom_exercises

def get_cardio_types():
    with db_connection() as (conn, c):
        cardio_types = c.execute("SELECT id, cardio_type FROM cardio_types ORDER BY cardio_type").fetchall()
        return cardio_types

def get_custom_cardio(user_id):
    with db_connection() as (conn, c):
        custom_cardio = c.execute("SELECT id, cardio_type FROM custom_cardio WHERE user_id = ? ORDER BY cardio_type", (user_id,)).fetchall()
        return custom_cardio

def get_workout(session_date, user_id):
    with db_connection() as (conn, c):
        workouts = c.execute("""
            SELECT workout_sessions.id AS session_id, workout_sessions.session_date, workout_sessions.session_notes,
            workout_logs.id AS workout_log_id, COALESCE(exercises.exercise, custom_exercises.exercise) AS exercise,
            workout_logs.exercise_notes,
            workout_sets.id AS set_id, workout_sets.set_number, workout_sets.reps, workout_sets.weight,
            COALESCE(exercises.is_time_based, custom_exercises.is_time_based, 0) AS is_time_based
            FROM workout_sessions
            JOIN workout_logs ON workout_sessions.id = workout_logs.session_id
            LEFT JOIN exercises ON workout_logs.exercise_id = exercises.id
            LEFT JOIN custom_exercises ON workout_logs.custom_exercise_id = custom_exercises.id
            JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id
            WHERE workout_sessions.session_date = ? AND workout_sessions.user_id = ?
            ORDER BY workout_sessions.id, workout_logs.id, workout_sets.set_number
            """, (session_date, user_id)).fetchall()
        return workouts

def get_cardio_session(session_date, user_id):
    with db_connection() as (conn, c):
        session = c.execute("""
            SELECT cardio_sessions.id AS session_id, cardio_sessions.session_date, cardio_sessions.session_notes,
            cardio_logs.id AS log_id, cardio_logs.duration, cardio_logs.distance, cardio_logs.distance_unit, cardio_logs.intensity,
            COALESCE(cardio_types.cardio_type, custom_cardio.cardio_type) AS cardio_type
            FROM cardio_sessions
            JOIN cardio_logs ON cardio_sessions.id = cardio_logs.cardio_session_id
            LEFT JOIN cardio_types ON cardio_logs.cardio_type_id = cardio_types.id
            LEFT JOIN custom_cardio ON cardio_logs.custom_cardio_id = custom_cardio.id
            WHERE cardio_sessions.session_date = ? AND cardio_sessions.user_id = ?
            ORDER by cardio_logs.id
            """, (session_date, user_id)).fetchall()
        return session
    

# == UPDATE ==
def update_custom_exercise(user_id, new_exercise, exercise_id):
    with db_connection() as (conn, c):
        c.execute("UPDATE custom_exercises SET exercise = ? WHERE user_id = ? AND id = ?", (new_exercise, user_id, exercise_id))
        return c.rowcount == 1

def update_custom_cardio(user_id, new_cardio, cardio_id):
    with db_connection() as (conn, c):
        c.execute("UPDATE custom_cardio SET cardio_type = ? WHERE user_id = ? AND id = ?", (new_cardio, user_id, cardio_id))
        return c.rowcount == 1

def update_password(user_id, password_hash):
    with db_connection() as (conn, c):
        c.execute("""
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_token_created_at = NULL
            WHERE id = ?
        """, (password_hash, user_id))
        return c.rowcount == 1


# == DELETE ==
def delete_custom_exercise(user_id, exercise_id):
    with db_connection() as (conn, c):
        try:
            c.execute("DELETE FROM custom_exercises WHERE user_id = ? AND id = ?",(user_id, exercise_id))
            return c.rowcount == 1
        except sqlite3.IntegrityError:
            return False

def delete_custom_cardio(user_id, cardio_id):
    with db_connection() as (conn, c):
        try:
            c.execute("DELETE FROM custom_cardio WHERE user_id = ? AND id = ?",(user_id, cardio_id))
            return c.rowcount == 1
        except sqlite3.IntegrityError:
            return False

