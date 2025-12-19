import sqlite3
import os
import sys
import time
from datetime import datetime

# == CONNECT AND CLOSE ==
def establish_connection():
    conn = sqlite3.connect('../backend/exercises.db')
    conn.execute("PRAGMA foreign_keys = ON")
    # conn.row_factory = sqlite3.Row
    c = conn.cursor()
    return conn, c

def close_connection(conn):
    conn.commit()
    conn.close()




# == EDITS ==
def edit_session_notes(c,workout_date,user_id):
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

def edit_custom_exercises(user_id, exercise):
    conn, c = establish_connection()
    try:
        c.execute("UPDATE custom_exercises SET exercise_name = ? WHERE user_id = ?", (exercise, user_id))
    except sqlite3.Error as e:
        print(f"database error: {e}")
        conn.rollback()
    close_connection(conn)
    return

# == DISPLAY ==
def display_exercises():
    conn, c = establish_connection()
    c.execute("SELECT exercise_id, exercise_name FROM exercises")
    valid_exercises = sorted([row[1] for row in c.fetchall()])
    close_connection(conn)

    return valid_exercises

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
    query = """
        SELECT workout_sessions.id, workout_sessions.session_date, workout_sessions.session_notes,
        workout_logs.id, exercises.exercise_name, workout_logs.exercise_notes, 
        workout_sets.id, workout_sets.set_number, workout_sets.reps, workout_sets.weight 
        FROM workout_sessions  
        JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
        JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id  
        JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id  
        WHERE workout_sessions.session_date = ? AND workout_sessions.user_id = ?
        ORDER BY workout_logs.id, workout_sets.set_number;
        """
    
    c.execute(query,(session_date, user_id))
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



# == INSERT ==
def create_custom_exercise(user_id, exercise):
    conn, c = establish_connection()
    c.execute("INSERT INTO custom_exercises (user_id, exercise_name) VALUES (?, ?)", (user_id, exercise))
    close_connection(conn)

def insert_session(session_date, session_notes, user_id):
    conn, c = establish_connection()
    c.execute("""
            INSERT INTO workout_sessions (session_date, session_notes, user_id)
            VALUES (?, ?, ?)
            """, (session_date, session_notes if session_notes else None, user_id))
    session_id = c.lastrowid
    close_connection(conn)
    return session_id




    




    
    

