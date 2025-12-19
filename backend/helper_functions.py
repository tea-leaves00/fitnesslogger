import sqlite3
import os
import sys
import time
from datetime import datetime

#MENU
def menu():
    print("\nSelect an option from below")
    print("-" * 30)
    print("1. Edit overall session notes")
    print("2. Edit individual exercise notes")
    print("3. Edit exercise name")
    print("4. Edit reps")
    print("5. Edit weight")
    print("6. Exit")
    choice = input("Enter your choice: ")
    return choice


#FOR .EXE
def resource_path(relative_path):
    return os.path.join(os.getcwd(), relative_path)


#EDITS
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

def edit_exercise_notes(c,workout_date,workouts,user_id):
    try:
        valid_exercises = [row[2] for row in workouts]
    
        while True:
            exercise_name = input("Enter the exercise name to update notes (exactly as displayed): ").strip()
            if exercise_name in valid_exercises:
                break
            else:
                print("Invalid exercise name. Please enter exactly as displayed.")
        
        new_notes = input("Enter the new notes for this exercise. Press Enter to leave it blank: ").strip()

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    
    try:
        # Update notes for the specific exercise in the workout logs
        c.execute("""
            UPDATE workout_logs
            SET exercise_notes = ?
            WHERE exercise_id = (
                SELECT exercise_id FROM exercises WHERE exercise_name = ?
            )
            AND session_id = (
                SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?
            );
        """, (new_notes if new_notes else None, exercise_name, workout_date,user_id))
        
        print("Exercise notes updated successfully.")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
   
def edit_exercise_name(c,workout_date,workouts,user_id):
    try:
        valid_exercises = [row[2] for row in workouts]
        while True:
            exercise_name = input("Enter the name of the exercise you want to rename: ")
            if exercise_name in valid_exercises:
                break
            else:
                print("Invalid exercise name. Please enter exactly as displayed.")
        
        exercise_list = list_exercises(c)
        print("\n")
        print("-" * 20)
        while True:
            new_exercise_name = input("Enter an exercise from the list to replace the old exercise: ")
            if new_exercise_name in exercise_list:
                break
            else:
                print("Invalid exercise name. Please enter exactly as displayed.")

        # Get the new exercise_id
        c.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (new_exercise_name,))
        result = c.fetchone()
        if not result:
            print("Error: Could not find new exercise ID.")
            return
        
        new_exercise_id = result[0]

        c.execute("""
                UPDATE workout_logs
                SET exercise_id = ?
                WHERE exercise_id = (
                    SELECT exercise_id FROM exercises WHERE exercise_name = ?
                )
                AND session_id = (
                    SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?
                );
            """, (new_exercise_id, exercise_name, workout_date,user_id))
        
        print("Exercise name updated succesfully.\n")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def edit_reps(c,workout_date,workouts,user_id):
    #get valid exercise name
    valid_exercises = [row[2] for row in workouts]
    while True:
        exercise_name = input("Which exercise do you want to edit reps for? ")
        if exercise_name in valid_exercises:
            break
        else:
            print("Invalid exercise name. Please enter exactly as displayed.")


    #get valid set number
    valid_set = [str(row[4]) for row in workouts if row[2] == exercise_name]
    while True:
        set_number = input("Which set do you want to edit? Press Enter to edit all sets: ")
        if not set_number:
            break
        elif set_number in valid_set:
            set_number = int(set_number)
            break
        else:
            print("Invalid set number. Please try again.")
    reps = int(input("Enter the number of reps: "))
    
    #edit reps
    try:
        if not set_number:
            c.execute("""
                UPDATE workout_sets
                SET reps = ?
                WHERE workout_log_id = (
                    SELECT workout_logs.id
                    FROM workout_logs
                    JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id
                    WHERE exercises.exercise_name = ? 
                    AND workout_logs.session_id = (
                        SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?)
                    );
            """, (reps, exercise_name, workout_date, user_id))
        else:
             c.execute("""
                UPDATE workout_sets
                SET reps = ?
                WHERE workout_log_id = (
                    SELECT workout_logs.id
                    FROM workout_logs
                    JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id
                    WHERE exercises.exercise_name = ? AND workout_logs.session_id = (
                        SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?)
                    ) AND set_number = ?;
            """, (reps, exercise_name, workout_date, user_id, set_number))  
        print("Reps updated succesfully.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")         

def edit_weight(c,workout_date,workouts,user_id):
    #get valid exercise name
    valid_exercises = [row[2] for row in workouts]
    while True:
        exercise_name = input("Which exercise do you want to edit weight for? ")
        if exercise_name in valid_exercises:
            break
        else:
            print("Invalid exercise name. Please enter exactly as displayed.")
    
    #get valid set number
    valid_set = [str(row[4]) for row in workouts if row[2] == exercise_name]
    while True:
        set_number = input("Which set do you want to edit? Press Enter to edit all sets: ")
        if not set_number:
            break
        elif set_number in valid_set:
            set_number = int(set_number)
            break
        else:
            print("Invalid set number. Please try again.")
    weight = float(input("Enter the new weight: "))
    
    #edit weight
    try:
        if not set_number:
            c.execute("""
                UPDATE workout_sets
                SET weight = ?
                WHERE workout_log_id = (
                    SELECT workout_logs.id
                    FROM workout_logs
                    JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id
                    WHERE exercises.exercise_name = ? 
                    AND workout_logs.session_id = (
                        SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?)
                    );
            """, (weight, exercise_name, workout_date, user_id))
        else:
            c.execute("""
                UPDATE workout_sets
                SET weight = ?
                WHERE workout_log_id = (
                    SELECT workout_logs.id
                    FROM workout_logs
                    JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id
                    WHERE exercises.exercise_name = ? AND workout_logs.session_id = (
                        SELECT id FROM workout_sessions WHERE session_date = ? AND user_id = ?)
                    ) AND set_number = ?;
            """, (weight, exercise_name, workout_date, user_id, set_number))
        
        print("Weight updated succesfully.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
 

#DISPLAY
def display_exercise_history(c,exercise_name,start_date,end_date,user_id):
    try:
        query = """  
            SELECT workout_sessions.session_date, exercises.exercise_name, 
                   workout_sets.set_number, workout_sets.reps, workout_sets.weight  
            FROM workout_sessions  
            JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
            JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id  
            JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id  
            WHERE exercises.exercise_name = ?
            AND workout_sessions.session_date BETWEEN ? AND ?  
            AND workout_sessions.user_id = ?
            ORDER BY workout_sessions.session_date, workout_sets.set_number;
        """

        c.execute(query, (exercise_name, start_date, end_date,user_id))
        workouts = c.fetchall()

        if not workouts:
            print(f"No history found for '{exercise_name}' between {start_date} and {end_date}.")
            return

        # Print the formatted results
        print(f"\nExercise history for '{exercise_name}' ({start_date} to {end_date}):")
        print("-" * 60)

        current_date = None
        for session_date, exercise_name, set_number, reps, weight in workouts:
            if session_date != current_date:
                print(f"\nDate: {session_date}")
                print("-" * 15)
                current_date = session_date
            print(f"   Set {set_number}: {reps} reps, {weight if weight else 'Bodyweight'} lbs")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

 
    
def display_workout(c,workout_date,user_id):

    try:
        query = """  
            SELECT workout_sessions.session_date, workout_sessions.session_notes, 
                exercises.exercise_name, workout_logs.exercise_notes, workout_sets.set_number, 
                workout_sets.reps, workout_sets.weight  
            FROM workout_sessions  
            JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
            JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id  
            JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id  
            WHERE workout_sessions.session_date = ? AND workout_sessions.user_id = ?
            ORDER BY workout_logs.id, workout_sets.set_number;
        """

        c.execute(query, (workout_date,user_id))
        workouts = c.fetchall()
        
        if not workouts:
            print("No workouts logged for this date yet.")
            return

        current_exercise = None

        for session_date, session_notes, exercise_name, exercise_notes, set_number, reps, weight, in workouts:
            if current_exercise is None:
                print(f"\nDate: {session_date} | Notes: {session_notes if session_notes else 'None'}")
                print("-" * 60)
            
            if exercise_name != current_exercise:
                print(f"\nExercise: {exercise_name} | Exercise Notes: {exercise_notes if exercise_notes else 'None'}") 
                current_exercise = exercise_name
                
            if weight is None:
                print(f"    Set {set_number}: {reps} reps, Bodyweight")
            else:
                print(f"    Set {set_number}: {reps} reps, {weight} lbs")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")

    return workouts


def display_workout_range(c,start_date,end_date,user_id):
    
    try:
        query = """
            SELECT workout_sessions.session_date, workout_sessions.session_notes, exercises.exercise_name, 
                workout_logs.exercise_notes, workout_sets.set_number, workout_sets.reps, workout_sets.weight
            FROM workout_sessions
            JOIN workout_logs ON workout_sessions.id = workout_logs.session_id  
            JOIN exercises ON workout_logs.exercise_id = exercises.exercise_id  
            JOIN workout_sets ON workout_logs.id = workout_sets.workout_log_id
            WHERE workout_sessions.session_date BETWEEN ? AND ?  
            AND workout_sessions.user_id = ?
            ORDER BY workout_sessions.session_date, workout_logs.id, workout_sets.set_number;
        """

        c.execute(query,(start_date,end_date,user_id))
        workouts = c.fetchall()

        if not workouts:
            print(f"No workout history found for {start_date} and {end_date}.")
            return
        
        print(f"\nWorkout history for ({start_date} to {end_date}):")
        print("-" * 50)

        current_date = None
        current_exercise = None

        for session_date, session_notes, exercise_name, exercise_notes, set_number, reps, weight in workouts:
            if session_date != current_date:
                print(f"\nDate: {session_date} | Session Notes: {session_notes if session_notes else 'None'}")
                print("-" * 60)
                current_date = session_date
            
            if exercise_name != current_exercise:
                print(f"\nExercise: {exercise_name} | Exercise Notes: {exercise_notes if exercise_notes else 'None'}") 
                current_exercise = exercise_name
            
            if weight is None:
                print(f"    Set {set_number}: {reps} reps, Bodyweight")
            else:
                print(f"    Set {set_number}: {reps} reps, {weight} lbs")


    
    except sqlite3.Error as e:
        print(f"Database error: {e}")

    

#QUERY
def list_exercises(c):
    c.execute("SELECT exercise_id, exercise_name FROM exercises")
    rows = c.fetchall()

    if not rows:
        print("No exercises found. Add some exercises first.")
        return []

    print("\nAvailable Exercises:")
    print("-" * 30)
    for exercise_id, exercise_name in rows:
        print(f"{exercise_id}: {exercise_name}")
    return [row[1] for row in rows]

def list_exercises_by_muscle_group(c):
    c.execute("SELECT * FROM muscle_groups")
    rows = c.fetchall()
    for row in rows:
      print(f"{row[0]}. {row[1]}")

    while True:
        muscle_choice = int(input("\nEnter the corresponding ID number for the muscle group you'd like to view: "))
        c.execute("SELECT muscle_group_id from muscle_groups")
        muscle_group_ids = c.fetchall()
        valid_muscle_group_ids = [row[0] for row in muscle_group_ids]
        if muscle_choice in valid_muscle_group_ids:
            break
        else:
            print(f"\nNo muscle group associated with ID: {muscle_choice}")
    
    query = """
        SELECT exercises.exercise_name, muscle_groups.muscle_group_name
        FROM exercise_muscle_groups
        JOIN exercises ON exercise_muscle_groups.exercise_id = exercises.exercise_id
        JOIN muscle_groups ON exercise_muscle_groups.muscle_group_id = muscle_groups.muscle_group_id
        WHERE exercise_muscle_groups.muscle_group_id = ?;
    """
    c.execute(query, (muscle_choice,))
    results = c.fetchall()
    exercises = [row[0] for row in results]
    muscle_group_name = results[0][1]

    print(f"\nExercises for muscle group: {muscle_group_name}:")
    print("-" * 40)
    index = 1
    for exercise in exercises:
        print(f"{index}. {exercise}")
        index +=1

    return exercises


#LOG
def log_date():
    while True:
        date = input("\nEnter the date (YYYY-MM-DD) of the workout. Press Enter for today: ").strip()
        if not date:
            return datetime.today().strftime('%Y-%m-%d')  # Default to today's date
        try:
            datetime.strptime(date, '%Y-%m-%d')   
            return date
        except ValueError:
            print("Invalid date format! Please enter the date in YYYY-MM-DD format.")

def log_date_timerange():
    while True:
        start_date = input("\nEnter the start date (YYYY-MM-DD) of the time frame you'd like to view: ").strip()
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            break
        except ValueError:
            print("Invalid date format! Please enter the date in YYYY-MM-DD format.")
    
    while True:
        end_date = input("\nEnter the end date (YYYY-MM-DD) of the time frame: ").strip()
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
            if end_date > start_date:
                break
            else:
                print("End date must be after the start date.")
        except ValueError:
            print("Invalid date format! Please enter the date in YYYY-MM-DD format.")
    return start_date, end_date

def log_cardio_duration():
    while True:
        duration = input("Enter the duration (HH:MM:SS) of the cardio session: ").strip()
        try: 
            time = datetime.strptime(duration, '%H:%M:%S')
            break
        except ValueError:
            print("\nInvalid time format. Please enter the time as HH:MM:SS.\n")
            time.sleep(1)

    db_duration = (time.hour * 3600) + (time.minute * 60) + time.second
    return db_duration, duration
    
def log_cardio_distance():
    while True:
        distance_unit = input("Enter 'mi' for miles, or 'km' for kilometers: ").strip().lower()
        if distance_unit == 'mi':
            try:
                distance = float(input("Enter the number of miles: "))
                return distance, distance_unit
            except ValueError:
                print("\nPlease Enter a valid number\n")
                continue
        elif distance_unit == 'km':
            try:
                distance = float(input("Enter the number of kilometers: "))
                return distance, distance_unit
            except ValueError:
                print("\nPlease Enter a valid number\n")
                continue
        else:
            print("\nInvalid Choice.\n")

def log_cardio_intensity():
    while True:
        intensity = int(input("Rate the intensity on a scale from 1-10. Press 'Enter' to skip: "))
        if 1 <= intensity <= 10 or not intensity:
            return intensity
        else: 
            print("\nInvalid Choice.\n")

def log_workout_session(c, workout_date, notes, user_id):
    c.execute("""
        INSERT INTO workout_sessions (session_date, session_notes, user_id)
        VALUES (?, ?, ?)
    """, (workout_date, notes if notes else None, user_id))
    session_id = c.lastrowid  
    return session_id
    print(f"New session created for {workout_date}")

def log_cardio_session(c, workout_date, notes, cardio_type_id, user_id):
    c.execute("""
        INSERT INTO cardio_sessions (session_date, session_notes, cardio_type_id, user_id)
        VALUES (?, ?, ?, ?)
    """, (workout_date, notes if notes else None, cardio_type_id, user_id))
    session_id = c.lastrowid
    return session_id
    print(f"New session created for {workout_date}")

def log_cardio_type(c):
    c.execute("SELECT cardio_type_name FROM cardio_types;")
    valid_cardio_types = [row[0] for row in c.fetchall()]

    print("Cardio List")
    print("-" * 10)

    cardio_index = 1
    for valid_cardio_type in valid_cardio_types:
        print(f"{cardio_index}. {valid_cardio_type}")
        cardio_index += 1

    while True:
        cardio_type = input("Enter the name of the cardio performed: ")
        if cardio_type in valid_cardio_types:
            break
        else:
            print("Invalid Cardio Type. Enter exactly as displayed.\n")
    
    c.execute("SELECT cardio_type_id FROM cardio_types WHERE cardio_type_name = ?", (cardio_type))
    cardio_type_id = c.fetchone()[0]
    return cardio_type_id

def log_cardio_log(c, cardio_session_id, duration, distance, distance_unit, intensity):
    c.execute("""
        INSERT INTO cardio_logs (cardio_session_id, duration, distance, distance_unit, intensity)
        VALUES (?, ?, ?, ?, ?)
        """, (cardio_session_id, duration, 
        distance if distance else None, distance_unit if distance_unit else None,
        intensity if intensity else None))
    cardio_log_id = c.lastrowid
    return cardio_log_id

def log_sets(session_id, c):
    done = False

    c.execute("SELECT exercise_name FROM exercises;")
    valid_exercise_names = [row[0] for row in c.fetchall()]

    #Exercise Name
    while True:
        exercise_name = input("\nEnter the exercise name you performed (or type 'done' to finish): ").strip()
        if exercise_name.lower() == "done":
            done = True
            break
        if exercise_name not in valid_exercise_names:
            print("Invalid exercise name. Please enter exactly as written.")
            continue
 
        c.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (exercise_name,))
        result = c.fetchone()
        if result:
            exercise_id = result[0]
        else:
            print("Error finding exercise ID")
            continue
        notes = input("Any specific notes for this exercise? Press Enter to skip: \n").strip()
        break

    set_number = 1
    sets_logged = False 

    #Reps and Weight
    while True:
        # First set input - must enter at least one set
        if not done:
            if set_number == 1:  
                while True:
                    try:
                        reps = int(input(f"Enter reps for set {set_number}: "))
                        break
                    except ValueError:
                        print("Error: Please enter a valid number of reps.")
            else:
                reps = input(f"Enter reps for set {set_number} (or type 'done' to finish this exercise): ").strip()
                if reps.lower() == "done":
                    break 
                try:
                    reps = int(reps)
                except ValueError:
                    print("Error: Please enter a valid number of reps.")
                    continue

            while True:   
                weight = input(f"Enter weight for set {set_number} (or type 'bodyweight' if none): ").strip()
                if weight.lower() == "bodyweight":
                    weight = None 
                    break
                try:
                    weight = float(weight)
                    break
                except ValueError:
                    print("Error: Please enter a valid number for weight, or enter 'bodyweight.'")
            
            #Only insert the workout log if at least one set is logged
            if not sets_logged:
                try:
                    c.execute("""
                        INSERT INTO workout_logs (session_id, exercise_id, exercise_notes)
                        VALUES (?, ?, ?)
                    """, (session_id, exercise_id, notes if notes else None))
                    workout_log_id = c.lastrowid 
                    sets_logged = True
                except sqlite3.Error as e:
                    print(f"Database error while logging exercise: {e}")
                    continue
            try:
                c.execute("""
                    INSERT INTO workout_sets (workout_log_id, set_number, reps, weight)
                    VALUES (?, ?, ?, ?)
                """, (workout_log_id, set_number, reps, weight))

            except sqlite3.Error as e:
                    print(f"Database error while logging exercise: {e}")

            set_number += 1
        else: 
            break
    

#USERS
def create_user():
    first_name = input("Enter your First Name: ").strip()
    last_name = input("Enter your Last Name: ").strip()
    username= input("Create a username: ").strip()
    password = input("Create a password: ").strip()
    email = input("Enter your email: ").strip()

def login(c):
    c.execute("SELECT username from users")
    valid_usernames = [row[0] for row in c.fetchall()]

    while True:
        username = input("Enter your username: ")
        if username in valid_usernames:
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_id = c.fetchone()[0]
            return user_id
        else:
            print("Invalid username. Please try again.")



