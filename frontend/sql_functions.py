import sqlite3
import os
import sys
import time
from datetime import datetime

# == CONNECT AND CLOSE ==
def establish_connection():
    conn = sqlite3.connect('../backend/exercises.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    return conn, c

def close_connection(conn):
    conn.commit()
    conn.close()


# == SELECT ==
def get_exercise_id(c, exercise_name):
    c.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (exercise_name,))
    exercise_id = c.fetchone()[0]
    return exercise_id

def get_custom_exercise_id(c, custom_exercise, user_id):
    c.execute("SELECT id FROM custom_exercises WHERE exercise_name = ? AND user_id = ?", (custom_exercise, user_id))
    exercise_id = c.fetchone()[0]
    return exercise_id

def get_session_ids(c, session_date, user_id):
    c.execute("SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?", (session_date, user_id))
    session_ids = [id[0] for id in c.fetchall()]
    return session_ids


# == EDITS ==
def edit_session_notes(c, workout_date,user_id):
    try: 
        new_notes = input("Enter your new notes. Press Enter if you'd like to enter nothing: ").strip()

        c.execute("""
                UPDATE workout_sessions
                SET session_notes = ?
                WHERE session_date = ?
                AND user_id = ?;
                """, (new_notes if new_notes else None, workout_date, user_id))
        
        print("Notes updated succesfully.")
        return
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def edit_custom_exercises(c, user_id, new_exercise, old_exercise):
    c.execute("UPDATE custom_exercises SET exercise_name = ? WHERE user_id = ? AND exercise_name = ?", (new_exercise, user_id, old_exercise))

def edit_custom_cardio(c, user_id, new_cardio, old_cardio):
    c.execute("UPDATE custom_cardio SET cardio_type = ? WHERE user_id = ? AND cardio_type = ?", (new_cardio, user_id, old_cardio))

# == DISPLAY ==
def display_exercises():
    conn, c = establish_connection()
    c.execute("SELECT exercise_id, exercise_name FROM exercises")
    exercises = sorted([row[1] for row in c.fetchall()])
    close_connection(conn)
    return exercises

def display_custom_exercises(user_id):
    conn, c = establish_connection()
    c.execute("SELECT id, exercise_name FROM custom_exercises WHERE user_id = ?", (user_id,))
    exercises = sorted([row[1] for row in c.fetchall()])
    close_connection(conn)
    return exercises

def display_exercises_by_muscle_group():
    conn, c = establish_connection()
    c.execute("""
            SELECT exercises.exercise_name, muscle_groups.muscle_group_name
            FROM exercise_muscle_groups
            JOIN exercises ON exercise_muscle_groups.exercise_id = exercises.exercise_id
            JOIN muscle_groups ON exercise_muscle_groups.muscle_group_id = muscle_groups.muscle_group_id
            ORDER by muscle_group_name, exercise_name
            """)
    
    exercises_and_muscles = c.fetchall()
    close_connection(conn)
    return exercises_and_muscles 

def display_workout(session_date, user_id):
    conn, c = establish_connection()
    session_ids = get_session_ids(c, session_date, user_id)

    placeholders = ','.join('?' * len(session_ids))

    query = f"""
        SELECT workout_sessions.id, workout_sessions.session_date, workout_sessions.session_notes,
        workout_logs.id, COALESCE(exercises.exercise_name, custom_exercises.exercise_name) AS exercise_name, workout_logs.exercise_notes, 
        workout_sets.id, workout_sets.set_number, workout_sets.reps, workout_sets.weight 
        FROM workout_sessions  
        JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
        LEFT JOIN exercises
        ON workout_logs.exercise_id = exercises.exercise_id
        LEFT JOIN custom_exercises
        ON workout_logs.custom_exercise_id = custom_exercises.id
        JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id  
        WHERE workout_sessions.id IN ({placeholders})
        ORDER BY workout_sessions.id, workout_logs.id, workout_sets.set_number;
        """
    
    c.execute(query, session_ids)
    workouts = c.fetchall()
    close_connection(conn)
    return workouts


def view_custom_exercises(user_id):
    conn, c = establish_connection()
    c.execute("SELECT exercise_name FROM custom_exercises WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    custom_exercises = [row[0] for row in data]
    close_connection(conn)
    return custom_exercises

def view_custom_cardio(user_id):
    conn, c = establish_connection()
    c.execute("SELECT cardio_type FROM custom_cardio WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    custom_cardio = [row[0] for row in data]
    close_connection(conn)
    return custom_cardio

def display_cardio_session(session_date, user_id):
    conn, c = establish_connection()
    query = """
        SELECT cardio_sessions.id, cardio_sessions.session_date, cardio_sessions.session_notes,
        cardio_logs.id, cardio_logs.duration, cardio_logs.distance, cardio_logs.distance_unit, cardio_logs.intensity,
        cardio_types.cardio_type_name
        FROM cardio_sessions
        JOIN cardio_logs ON cardio_sessions.id = cardio_logs.cardio_session_id
        JOIN cardio_types ON cardio_logs.cardio_type_id = cardio_types.cardio_type_id
        WHERE cardio_sessions.session_date = ? AND user_id = ?
        ORDER by cardio_logs.id
        """
    
    c.execute(query, (session_date,user_id))
    session = c.fetchall()
    close_connection(conn)
    return session

# == INSERT ==
def create_custom_exercise(user_id, exercise):
    conn, c = establish_connection()
    c.execute("INSERT INTO custom_exercises (user_id, exercise_name) VALUES (?, ?)", (user_id, exercise))
    close_connection(conn)

def create_custom_cardio(user_id, cardio_type):
    conn, c = establish_connection()
    c.execute("INSERT INTO custom_cardio (user_id, cardio_type) VALUES (?, ?)", (user_id, cardio_type))
    close_connection(conn)

# test this out with try except blocks, in case session row cant be inserted
def insert_session(session_date, session_notes, user_id):
    conn, c = establish_connection()
    c.execute("""
            INSERT INTO workout_sessions (session_date, session_notes, user_id)
            VALUES (?, ?, ?)
            """, (session_date, session_notes if session_notes else None, user_id))
    session_id = c.lastrowid
    close_connection(conn)
    return session_id

def insert_workout_log(c, session_id, exercise_id, custom_exercise_id, exercise_notes):
    c.execute("""
                INSERT INTO workout_logs (session_id, exercise_id, custom_exercise_id, exercise_notes)
                VALUES (?, ?, ?, ?)
            """, (session_id, exercise_id, custom_exercise_id, exercise_notes if exercise_notes else None))
    workout_log_id = c.lastrowid
    return workout_log_id

def insert_sets(c, workout_log_id, set_number, reps, weight):
    c.execute("""
            INSERT INTO workout_sets (workout_log_id, set_number, reps, weight)
            VALUES (?, ?, ?, ?)
        """, (workout_log_id, set_number, reps, weight))


# == CARDIO ==
def get_db_duration(hours, minutes, seconds):
    duration = (hours * 3600) + (minutes * 60) + seconds
    return duration

def log_cardio_session(c, session_date, notes, user_id):
    c.execute("""
        INSERT INTO cardio_sessions (session_date, session_notes, user_id)
        VALUES (?, ?, ?)
    """, (session_date, notes if notes else None, user_id))
    session_id = c.lastrowid
    return session_id

def log_cardio_log(c, cardio_session_id, cardio_type, duration, distance, distance_unit, intensity):
    c.execute("SELECT cardio_type_id FROM cardio_types WHERE cardio_type_name = ?", (cardio_type,))
    cardio_type_id = c.fetchone()[0]
    c.execute("""
        INSERT INTO cardio_logs (cardio_session_id, cardio_type_id, duration, distance, distance_unit, intensity)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (cardio_session_id, cardio_type_id, duration, 
        distance if distance else None, distance_unit if distance_unit else None,
        intensity if intensity else None))

def display_cardio_types():
    conn, c = establish_connection()
    c.execute("SELECT cardio_type_name FROM cardio_types")
    cardio_types = sorted([row[0] for row in c.fetchall()])
    close_connection(conn)
    return cardio_types


    




    
    

