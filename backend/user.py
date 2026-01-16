import sqlite3
from datetime import datetime
from helper_functions import *
import time

def weightlifting_main_menu():
    print("\n1. Log a Workout")
    print("2. View a Workout")
    print("3. View Workout History")
    print("4. View the History of a Specific Exercise")
    print("5. Edit a Workout")
    print("6. Delete a Workout")
    print("7. Create Custom Exercises")
    print("8. Return to Main Menu\n")
    choice = input("Enter Your Choice: ")
    return choice

def cardio_main_menu():
    print("\n1. Log a Cardio Session")
    print("2. View a Cardio Session")
    print("3. Edit a Cardio Session")
    print("4. Delete a Cardio Session")
    print("5. Create Custom Cardio Types")
    print("6. Return to Main Menu\n")
    choice = input("Enter Your Choice: ")
    return choice

#WEIGHTLIFTING
def log_workout(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    workout_date = log_date()
    notes = input("Any overall notes for the session? Press Enter to skip: ").strip()
    session_id = log_workout_session(c, workout_date, notes, user_id)
    
    try:
        while True:
            choice = input("\nEnter '1' to log sets or '2' to filter exercises by muscle group. Enter 'done' to finish the workout: ")
            if choice == '1':
                log_sets(session_id, c)
            elif choice == '2':
                list_exercises_by_muscle_group(c)
            elif choice == 'done':
                break
            else:
                print("Invalid choice.")
                time.sleep(1)
            

    except sqlite3.Error as e:
        print(f"Database error while logging sets: {e}")

    finally:
        print("\nWorkout logged succesfully.")
        conn.commit()
        conn.close()

def view_workout(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    workout_date = log_date()
    display_workout(c, workout_date, user_id)

    conn.close()

def view_workouts_timerange(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    start_date, end_date = log_date_timerange()
    display_workout_range(c,start_date,end_date,user_id)

    conn.close()

def view_exercise_history(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    
    rows = list_exercises(c)

    while True:
        exercise_name = input("\nEnter the exercise name to view history: ").strip()
        if exercise_name in rows:
            break
        else:
            print("Error: Exercise not found. Please enter a valid exercise name.")

    start_date, end_date = log_date_timerange()
            
    display_exercise_history(c,exercise_name,start_date,end_date,user_id)

    conn.close()

def edit_session(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    workout_date = log_date()
    workouts = display_workout(c, workout_date,user_id)
    if workouts:
        while True:
            choice = menu()
            if choice == "1":
                edit_session_notes(c,workout_date,user_id)
                conn.commit()
                workouts = display_workout(c, workout_date,user_id)
            elif choice == "2":
                edit_exercise_notes(c,workout_date,workouts,user_id)
                conn.commit()
                workouts = display_workout(c, workout_date,user_id)
            elif choice == "3":
                edit_exercise_name(c,workout_date,workouts,user_id)
                conn.commit()
                workouts = display_workout(c, workout_date,user_id)
            elif choice == "4": 
                edit_reps(c,workout_date,workouts,user_id)
                conn.commit()
                workouts = display_workout(c, workout_date,user_id)
            elif choice == "5":
                edit_weight(c,workout_date,workouts,user_id)
                conn.commit()
                workouts = display_workout(c, workout_date,user_id)
            elif choice == "6":
                print("\n")
                break
            else:
                print("Invalid choice. Please try again.")
    else: 
        print("No session found for this date")
        return

    conn.commit()
    conn.close()
   
def delete_session(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    workout_date = log_date()

    c.execute("SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?", (workout_date, user_id))
    session = c.fetchone()
    
    if session:
        c.execute("DELETE FROM workout_sessions WHERE session_date = ? AND user_id = ?", (workout_date, user_id))
        print(f"All data associated with the session on {workout_date} has been deleted successfully.")
    else:
        print(f"No workout session found for the date: {workout_date}. Nothing to delete.")

    conn.commit()
    conn.close()

def create_custom_exercise(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    while True:
        exercise_name = input("Enter the name of the exercise you want to add: ")
        if not exercise_name:
            print("Exercise name cannot be empty")
            continue
        try:
            c.execute("INSERT INTO custom_exercises (user_id, exercise_name) VALUES (?, ?)", (user_id, exercise_name))
            print(f"{exercise_name} has been added to your list of custom exercises.\n")
        except sqlite3.Error as e:
            print(f"Database error: {e}")

        choice = input("Enter '1' to create another exercise. Press any other key to exit: ")
        if choice != '1':
            break

    conn.commit()
    conn.close()


# == CARDIO ==
def log_cardio_session(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    workout_date = log_date()
    cardio_type_id = log_cardio_type(c)

    notes = input("Any overall notes for the session? Press Enter to skip: ").strip()
    session_id = log_cardio_session(c, workout_date, notes, cardio_type_id, user_id)

    
    db_duration, _ = log_cardio_duration()
    distance, distance_unit = log_cardio_distance()
    intensity = log_cardio_intensity()

    cardio_log_id = log_cardio_log(c, session_id, db_duration, distance, intensity, distance_unit)

def create_custom_cardio(user_id):
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    while True:
        cardio_type = input("Enter the type of cardio you want to add: ")
        if not cardio_type:
            print("Cardio type cannot be empty")
            continue
        try:
            c.execute("INSERT INTO custom_cardio (user_id, cardio_type) VALUES (?, ?)", (user_id, cardio_type))
            print(f"{cardio_type} has been added to your list of custom cardio.\n")
        except sqlite3.Error as e:
            print(f"Database error: {e}")

        choice = input("Enter '1' to create another cardio type. Press any other key to exit: ")
        if choice != '1':
            break

    conn.commit()
    conn.close()



def run_cli():
    db_path = resource_path("exercises.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    user_id = login(c) 
    conn.close()

    menu = True
    
    while True: 
        if menu:
            mode = input("\nEnter '1' for Weightlifting Mode or '2' for Cardio Mode. Enter 'quit' to exit the program: ")
            menu = False

        if mode == '1':
            choice = weightlifting_main_menu() 
            if choice == "1":
                log_workout(user_id)
            elif choice == "2":
                view_workout(user_id)
            elif choice == "3":
                view_workouts_timerange(user_id)
            elif choice == "4": 
                view_exercise_history(user_id)
            elif choice == "5":
                edit_session(user_id)
            elif choice == "6":
                delete_session(user_id)
            elif choice == '7':
                create_custom_exercise(user_id)
            elif choice == '8':
                menu = True
                continue
            else:
                print("\nInvalid choice. Please try again.")
        elif mode == '2':
            pass
        elif mode == 'quit':
            break
        else:
            print("Invalid Choice. Try Again.\n")

run_cli()















