#NOTE eventually implement logging module
#NOTE eventually implement contextlib module
#NOTE do integrity check everynight? before copying maybe?

import sqlite3
from flask import session, current_app
from config import Config
import secrets
import resend
import os

resend.api_key = Config.RESEND_API_KEY


# == CONNECT  ==
def establish_connection():
    db_path = current_app.config['DB_PATH']
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    return conn, c


# == EMAIL VERIFICATION == 
def generate_verification_token():
    return secrets.token_urlsafe(32)

def save_verification_token(email, token):
    conn, c = establish_connection()
    try:
        c.execute("""
            UPDATE users
            SET verification_token = ?, verification_token_created_at = CURRENT_TIMESTAMP
            WHERE email = ?
        """, (token, email))
        conn.commit()
    finally:
        conn.close()

def send_verification_email(email, token):
    verification_link = f"{current_app.config['BASE_URL']}/verify/{token}"
    
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Verify your account",
        "html": f"""
            <h2>Welcome to My Workout App!</h2>
            <p>Click the link below to verify your account:</p>
            <p><a href="{verification_link}">{verification_link}</a></p>
            <p>This link expires in 24 hours.</p>
        """,
    }
    
    resend.Emails.send(params)

def verify_user_token(token):
    conn, c = establish_connection()
    try:
        c.execute("SELECT id, verification_token_created_at FROM users WHERE verification_token = ?", (token,))
        result = c.fetchone()
        if not result:
            return False, "Invalid token"
        
        user_id, token_created_at = result
        c.execute("SELECT (julianday('now') - julianday(?)) * 24 < 24", (token_created_at,))
        if not c.fetchone()[0]:
            return False, "Token expired"
        
        c.execute("""UPDATE users SET verified = 1, verification_token = NULL,
                     verification_token_created_at = NULL WHERE id = ?""", (user_id,))
        conn.commit()
        return True, "Account verified"
    finally:
        conn.close()


# == RESET PASSWORD ==
def save_reset_token(email, token):
    conn, c = establish_connection()
    try:
        c.execute("""
            UPDATE users
            SET reset_token = ?, reset_token_created_at = CURRENT_TIMESTAMP
            WHERE email = ?
        """, (token, email))
        conn.commit()
    finally:
        conn.close()

def send_password_reset_email(email, token):
    reset_link = f"{current_app.config['BASE_URL']}/reset_password/{token}"
    
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Reset your password",
        "html": f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't request this, you can ignore this email.</p>
        """,
    }
    
    resend.Emails.send(params)

def verify_reset_token(token):
    conn, c = establish_connection()
    try:
        c.execute("""
            SELECT id, reset_token_created_at FROM users 
            WHERE reset_token = ?
        """, (token,))
        result = c.fetchone()
        if not result:
            return None, "Invalid token"
        
        user_id, token_created_at = result
        c.execute("""
            SELECT (julianday('now') - julianday(?)) * 24 < 24
        """, (token_created_at,))
        is_valid = c.fetchone()[0]
        if not is_valid:
            return None, "Token expired"
        
        return user_id, "Valid"
    finally:
        conn.close()

def update_password(user_id, password_hash):
    conn, c = establish_connection()
    try:
        c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()

def clear_reset_token(user_id):
    conn, c = establish_connection()
    try:
        c.execute("UPDATE users SET reset_token = NULL, reset_token_created_at = NULL WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# == SEND USERNAME ==
def send_username_email(email, username):
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Forgot Username",
        "html": f"""
            <h2>Forgot Username Request</h2>
            <p>Hello, your username is <strong>{username}</strong>. 
            Click <a href="https://www.fitnesslogger.app/login">this link</a> to be redirected back to the login page.</p>
        """,
    }
    resend.Emails.send(params)


# == USERS == 
def create_user(first_name, last_name, username, password_hash, email):
    conn, c = establish_connection()
    try:
        c.execute("INSERT INTO users (first_name, last_name, username, password_hash, email) VALUES (?, ?, ?, ?, ?)"
                    ,(first_name, last_name, username, password_hash, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
    
def get_user_by_id(user_id):
    conn, c = establish_connection()
    try:
        c.execute("SELECT id, first_name, last_name, username, email FROM users WHERE id = ?", (user_id,))
        data = c.fetchone()
        return data
    finally:
        conn.close()

def get_user_by_username(username):
    conn, c = establish_connection()
    try:
        c.execute("SELECT id, first_name, last_name, username, email, password_hash, verified FROM users WHERE username = ?", (username,))
        data = c.fetchone()
        return data
    finally:
        conn.close()

def get_user_by_email(email):
    conn, c = establish_connection()
    try:
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        data = c.fetchone()
        if data:
            return True
        else:
            return False
    finally:
        conn.close()

def get_username_by_email(email):
    conn, c = establish_connection()
    try:
        c.execute("SELECT username FROM users WHERE email = ?", (email,))
        data = c.fetchone()
        if data:
            return data[0]
        else:
            return None
    finally:
        conn.close()
    
    
# == SELECT ==
def get_exercise_id(c, exercise):
    c.execute("SELECT id FROM exercises WHERE exercise = ?", (exercise,))
    exercise_id = c.fetchone()[0]
    return exercise_id

def get_custom_exercise_id(c, exercise, user_id):
    c.execute("SELECT id FROM custom_exercises WHERE exercise = ? AND user_id = ?", (exercise, user_id))
    exercise_id = c.fetchone()[0]
    return exercise_id

def get_workout_session_ids(c, session_date, user_id):
    c.execute("SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?", (session_date, user_id))
    session_ids = [id[0] for id in c.fetchall()]
    return session_ids

def get_cardio_session_ids(c, session_date, user_id):
    c.execute("SELECT id FROM cardio_sessions WHERE session_date = ? AND user_id = ?", (session_date, user_id))
    session_ids = [id[0] for id in c.fetchall()]
    return session_ids

def get_time_based_exercises(c):
    result = c.execute("SELECT exercise FROM exercises WHERE is_time_based = 1").fetchall()
    return [row[0] for row in result]

def get_time_based_custom_exercises(c, user_id):
    result = c.execute("SELECT exercise FROM custom_exercises WHERE user_id = ? AND is_time_based = 1", (user_id,)).fetchall()
    return [row[0] for row in result]

def get_db_duration(hours, minutes, seconds):
    duration = (hours * 3600) + (minutes * 60) + seconds
    return duration

# == EDITS ==
def edit_custom_exercises(c, user_id, new_exercise, exercise_id):
    c.execute("UPDATE custom_exercises SET exercise = ? WHERE user_id = ? AND id = ?", (new_exercise, user_id, exercise_id))

def edit_custom_cardio(c, user_id, new_cardio, cardio_id):
    c.execute("UPDATE custom_cardio SET cardio_type = ? WHERE user_id = ? AND id = ?", (new_cardio, user_id, cardio_id))

# == DISPLAY ==
def display_exercises(c):
    c.execute("SELECT id, exercise FROM exercises")
    exercises = sorted([row[1] for row in c.fetchall()])
    return exercises

def display_workout(session_date, user_id):
    conn, c = establish_connection()
    session_ids = get_workout_session_ids(c, session_date, user_id)
    placeholders = ','.join('?' * len(session_ids))

    query = f"""
        SELECT workout_sessions.id, workout_sessions.session_date, workout_sessions.session_notes,
        workout_logs.id, COALESCE(exercises.exercise, custom_exercises.exercise) AS exercise, 
        workout_logs.exercise_notes, 
        workout_sets.id, workout_sets.set_number, workout_sets.reps, workout_sets.weight,
        COALESCE(exercises.is_time_based, custom_exercises.is_time_based, 0) AS is_time_based
        FROM workout_sessions  
        JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
        LEFT JOIN exercises ON workout_logs.exercise_id = exercises.id
        LEFT JOIN custom_exercises ON workout_logs.custom_exercise_id = custom_exercises.id
        JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id  
        WHERE workout_sessions.id IN ({placeholders})
        ORDER BY workout_sessions.id, workout_logs.id, workout_sets.set_number;
        """
    
    try:
        c.execute(query, session_ids)
        workouts = c.fetchall()
        return workouts
    finally:
        conn.close()
    
def display_custom_exercises(c, user_id):
    data = c.execute("SELECT id, exercise FROM custom_exercises WHERE user_id = ?", (user_id,)).fetchall()
    custom_exercises = [{"id": row[0], "name": row[1]} for row in data]
    return custom_exercises

def display_custom_cardio(c, user_id):
    data = c.execute("SELECT id, cardio_type FROM custom_cardio WHERE user_id = ?", (user_id,)).fetchall()
    custom_cardio = [{"id": row[0], "name": row[1]} for row in data]
    return custom_cardio

def display_cardio_session(session_date, user_id):
    conn, c = establish_connection()
    session_ids = get_cardio_session_ids(c, session_date, user_id)
    placeholders = ','.join('?' * len(session_ids))

    query = f"""
        SELECT cardio_sessions.id, cardio_sessions.session_date, cardio_sessions.session_notes,
        cardio_logs.id, cardio_logs.duration, cardio_logs.distance, cardio_logs.distance_unit, cardio_logs.intensity,
        COALESCE(cardio_types.cardio_type, custom_cardio.cardio_type) AS cardio_type
        FROM cardio_sessions
        JOIN cardio_logs ON cardio_sessions.id = cardio_logs.cardio_session_id
        LEFT JOIN cardio_types ON cardio_logs.cardio_type_id = cardio_types.id
        LEFT JOIN custom_cardio ON cardio_logs.custom_cardio_id = custom_cardio.id
        WHERE cardio_sessions.id IN ({placeholders})
        ORDER by cardio_logs.id
        """
    
    try:
        c.execute(query, session_ids)
        session = c.fetchall()
        return session
    finally:
        conn.close()
    
def display_cardio_types(c):
    c.execute("SELECT cardio_type FROM cardio_types")
    cardio_types = sorted([row[0] for row in c.fetchall()])
    return cardio_types

# == INSERT ==
def create_custom_exercise(user_id, exercise):
    conn, c = establish_connection()
    try:
        c.execute("INSERT INTO custom_exercises (user_id, exercise) VALUES (?, ?)", (user_id, exercise))
        conn.commit()
    finally:
        conn.close()

def create_custom_cardio(user_id, cardio_type):
    conn, c = establish_connection()
    try:
        c.execute("INSERT INTO custom_cardio (user_id, cardio_type) VALUES (?, ?)", (user_id, cardio_type))
        conn.commit()
    finally:
        conn.close()

def insert_workout_session(session_date, session_notes, user_id):
    conn, c = establish_connection()
    try:
        c.execute("""
                INSERT INTO workout_sessions (session_date, session_notes, user_id)
                VALUES (?, ?, ?)
                """, (session_date, session_notes if session_notes else None, user_id))
        session_id = c.lastrowid
        conn.commit()
        return session_id
    finally:
        conn.close()
    
def insert_workout_log(c, conn, session_id, exercise_id, custom_exercise_id, exercise_notes):
    c.execute("""
                INSERT INTO workout_logs (session_id, exercise_id, custom_exercise_id, exercise_notes)
                VALUES (?, ?, ?, ?)
            """, (session_id, exercise_id, custom_exercise_id, exercise_notes if exercise_notes else None))
    conn.commit()
    workout_log_id = c.lastrowid
    return workout_log_id

def insert_workout_sets(c, conn, workout_log_id, set_number, reps, weight):
    #consider using ".executemany()"
    c.execute("""
            INSERT INTO workout_sets (workout_log_id, set_number, reps, weight)
            VALUES (?, ?, ?, ?)
        """, (workout_log_id, set_number, reps, weight))
    conn.commit()

def log_cardio_session(c, conn, session_date, notes, user_id):
    c.execute("""
        INSERT INTO cardio_sessions (session_date, session_notes, user_id)
        VALUES (?, ?, ?)
    """, (session_date, notes if notes else None, user_id))
    conn.commit()
    session_id = c.lastrowid
    return session_id

def log_cardio_log(c, conn, cardio_session_id, cardio_type, duration, distance, distance_unit, intensity):
    c.execute("SELECT id FROM cardio_types WHERE cardio_type = ?", (cardio_type,))
    cardio_type_id = c.fetchone()[0]
    c.execute("""
        INSERT INTO cardio_logs (cardio_session_id, cardio_type_id, duration, distance, distance_unit, intensity)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (cardio_session_id, cardio_type_id, duration, 
        distance if distance else None, distance_unit if distance_unit else None,
        intensity if intensity else None))
    conn.commit()

# == DELETE ==
def delete_custom_exercise(user_id, exercise_id):
    conn, c = establish_connection()
    try:
        c.execute("DELETE FROM custom_exercises WHERE user_id = ? AND id = ?",(user_id, exercise_id))
        conn.commit()
        return True
    except sqlite3.IntergrityError:
        return False
    finally:
        conn.close()
    
def delete_custom_cardio(user_id, cardio_id):
    conn, c = establish_connection()
    try:
        c.execute("DELETE FROM custom_cardio WHERE user_id = ? AND id = ?",(user_id, cardio_id))
        conn.commit()
        return True
    except sqlite3.IntergrityError:
        return False  
    finally:
        conn.close()

# == CLEAR FLASK SESSION ==
def clear_workout_session():
    keys = [
        'current_sets', 'session_date', 'session_notes', 
        'date_selection', 'same_sets', 'current_set_number',
        'current_exercise', 'current_workout_id'
    ]
    for key in keys:
        session.pop(key, None)

def clear_sets():
    keys = [
        'current_sets', 'same_sets', 'current_set_number',
        'current_exercise', 'current_workout_id'
    ]
    for key in keys:
        session.pop(key, None)

def clear_cardio_session():
    keys = [
        'current_logs', 'session_date', 
        'session_notes', 'date_selection',
    ]
    for key in keys:
        session.pop(key, None)

def clear_logs():
    keys = [
        'current_logs'
    ]
    for key in keys:
        session.pop(key, None)
