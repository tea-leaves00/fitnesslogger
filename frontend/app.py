from flask import Flask, render_template, request,redirect, url_for, session, flash
import sqlite3
from sql_functions import *

app = Flask(__name__)
app.secret_key = 'something'

# == HOME ==
@app.route('/')
def weightlifting_index():
    return render_template('weightlifting_index.html')


# == LOG WORKOUT ==
@app.route('/log_workout', methods = ['POST', 'GET'])
def log_workout():
    exercises = display_exercises()

    if request.method == 'POST':
        if request.form.get('action') == 'add_set':
            # == FORM DATA ==
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            exercise_name = request.form.get('exercise')
            exercise_notes = request.form.get('exercise_notes')
            if not exercise_notes:
                exercise_notes = session.get('exercise_notes', '')

            reps = request.form.get('reps')
            bodyweight = request.form.get('bodyweight')
            weight = request.form.get('weight')

            if bodyweight:
                weight = None
            elif not weight:
                weight = None

            # == SESSION ==
            if 'session_date' not in session:
                session['session_date'] = session_date
                session['session_notes'] = session_notes

            if 'current_sets' not in session:
                session['current_sets'] = []
                session['current_set_number'] = 1

            if session.get('current_exercise') != exercise_name:
                session['current_exercise'] = exercise_name
                session['current_set_number'] = 1
                

            session['current_sets'].append({
                'exercise': exercise_name,
                'exercise_notes': exercise_notes,
                'reps': reps, 
                'weight': weight,
                'set_number': session['current_set_number']
            })


            session.modified = True
            session['current_set_number'] += 1

            if 'current_workout_id' not in session:
                user_id = "1"

                session_id = insert_session(session_date, session_notes, user_id)
                session['current_workout_id'] = session_id
                
                
    return render_template('log_workout.html', exercises=exercises, 
                           current_sets = session.get('current_sets', []))

# == VIEW AND EDIT WORKOUT ==
@app.route('/view_workout', methods= ['GET', 'POST'])
def view_workout():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        user_id = "1"

        workouts = display_workout(session_date, user_id)
        
        session['current_workout'] = workouts
        session['workout_searched'] = True
        session.modified = True
    else:
        session['workout_searched'] = False

      
    return render_template('view_workout.html', 
                           workouts=session.get('current_workout', []), 
                           workout_searched=session.get('workout_searched', False))


# == EDIT WORKOUT == 
@app.route('/edit_workout/<session_date>', methods=['GET', 'POST'])
def edit_workout(session_date):
    user_id = "1"
    workouts = session.get('current_workout', [])
    

    if request.method == 'POST':
        print("Request method:", request.method)
        print("Form data:", request.form)
        print("Form keys:", list(request.form.keys()))
        action = request.form.get('action')
        if action == 'save':
            conn = sqlite3.connect('C:/Users/12146/Documents/VS Code Files/Workout_App/backend/exercises.db')
            c = conn.cursor()

            session_id = request.form.get('session_id')
            new_session_date = request.form.get('session_date')
            if new_session_date and new_session_date != session_date:
                c.execute("""
                    UPDATE workout_sessions
                    SET session_date = ?
                    WHERE id = ?
                    """, (new_session_date, session_id))
                
                return redirect(url_for('edit_workout', session_date=new_session_date))
                
            session_notes = request.form.get('session_notes')
            if session_notes:
                c.execute("""
                    UPDATE workout_sessions 
                    SET session_notes = ? 
                    WHERE session_id = ?
                """, (session_notes, session_id))

            for input in request.form:
                if input.startswith('exercise_name_'):
                    index = input.split('_')[-1]
                    workout_log_id = request.form.get(f'workout_log_id_{index}')
                    exercise_name = request.form.get(f'exercise_name_{index}')
                    
                    result = c.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (exercise_name,)).fetchone()
                    if result:
                        exercise_id = result[0]
                        c.execute("""
                            UPDATE workout_logs
                            SET exercise_id = ?
                            WHERE id = ?
                        """, (exercise_id, workout_log_id))

            for input in request.form:
                if input.startswith('exercise_notes_'):
                    index = input.split('_')[-1]
                    workout_log_id = request.form.get(f'workout_log_id_{index}')
                    exercise_notes = request.form.get(f'exercise_notes_{index}')
                    
                    c.execute("""
                        UPDATE workout_logs
                        SET exercise_notes = ?
                        WHERE id = ?
                    """, (exercise_notes, workout_log_id))
            

            for input in request.form:
                if input.startswith('set_id_'):
                    index = input.split('_')[-1] 
                    set_id = request.form.get(f'set_id_{index}')
                    reps = request.form.get(f'reps_{index}')
                    weight = request.form.get(f'weight_{index}')
                    
                    c.execute("""
                        UPDATE workout_sets 
                        SET reps = ?, weight = ? 
                        WHERE id = ?
                    """, (reps, weight, set_id))
            
            conn.commit()
            conn.close()
            
            flash("Workout updated successfully!")
            return redirect(url_for('view_workout'))


        
    return render_template('edit_workout.html', workouts=workouts, session_date=session_date)


# == CLEAR ==
@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('log_workout'))


# == POST WORKOUT ==
@app.route('/finish_workout')
def finish_workout():
    conn = sqlite3.connect('../backend/exercises.db')
    c = conn.cursor()

    print(f"Session current_sets: {session.get('current_sets', 'NOT FOUND')}")

    if 'current_sets' not in session or not session['current_sets']:
        flash("No sets to save!")
        return redirect(url_for('log_workout'))
    
    if 'current_workout_id' not in session:  # TEST THIS OUT FURTHER
        flash("No workout session found!")
        return redirect(url_for('log_workout'))

    session_id = session['current_workout_id']
    exercises_processed = set()
    for set_data in session['current_sets']:
        exercise_name = set_data['exercise']
        
        # Only create workout_logs entry once per exercise
        if exercise_name not in exercises_processed:
            c.execute("SELECT exercise_id FROM exercises WHERE exercise_name = ?", (exercise_name,))
            exercise_id = c.fetchone()[0]

            if exercise_id is None:
                print(f"Exercise '{exercise_name}' not found in database!")
                continue
            
            c.execute("""
                INSERT INTO workout_logs (session_id, exercise_id, exercise_notes)
                VALUES (?, ?, ?)
            """, (session_id, exercise_id, set_data['exercise_notes']))
            workout_log_id = c.lastrowid
            
            exercises_processed.add(exercise_name)

        c.execute("""
            INSERT INTO workout_sets (workout_log_id, set_number, reps, weight)
            VALUES (?, ?, ?, ?)
        """, (workout_log_id, set_data['set_number'], set_data['reps'], set_data['weight']))

    conn.commit()
    conn.close()

    session.clear()
    flash("Workout logged successfully!")
    return redirect(url_for('log_workout'))


# == CREATE CUSTOM EXERCISE ==
@app.route('/custom_exercises', methods=['GET', 'POST'])
def custom_exercises():
    custom_exercises = []
    editing_exercise = False

    if request.method == 'POST':
        if request.form.get('action') == 'add_exercise':
            user_id = "1"
            custom_exercise = request.form.get('create_custom_exercise')

            create_custom_exercise(user_id, custom_exercise)
            flash('Custom exercise added successfully!')
            return redirect(url_for('custom_exercises'))
        elif request.form.get('action') == 'view_exercises':
            user_id = "1"
            custom_exercises = view_custom_exercises(user_id)
        elif request.form.get('action') == 'edit_exercises':
            editing_exercise = True
            


    return render_template('custom_exercises.html', custom_exercises=custom_exercises, editing_exercise=editing_exercise)


if __name__ == '__main__':
    app.run(debug=True)