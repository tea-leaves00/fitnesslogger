from flask import Flask, render_template, request, redirect, url_for, session, flash
# from flask_login import LoginManager, UserMixin
# from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from sql_functions import *


app = Flask(__name__)
app.secret_key = 'something'
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = 'login' 


# == MAIN PAGE ==
@app.route('/')
def index():
    return render_template('base.html')


# === WEIGHTLIFTING ===
# == HOME ==
@app.route('/weightlifting_home')
def weightlifting_index():
    return render_template('weightlifting_index.html')

# == LOG WORKOUT ==
# ok this is working way better but now need to figure out what happens when someone goes BACK
# little trash can icons next to each set
# form resubmission fucks things up (for example it input a duplicate entry and then upon viewing the workout it say set 1 1 2 2)
# same_sets button resets everything cuz it redirects
# reset should not pop everything...like it shouldnt go all the way back to date selection....idk maybe it should???
# error handling for not entering sets
# if you do finish workout before adding last set, handle that maybe
#do same thing as log cardio where it will input the first set if not added log, OR even better error handling

@app.route('/log_workout', methods=['POST', 'GET'])
def log_workout():
    user_id = "1"
    exercises = display_exercises()
    custom_exercises = display_custom_exercises(user_id)

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False
            print(session_notes)

        elif request.form.get('action') == 'same_sets':
            session['same_sets'] = True
            session.modified = True

        elif request.form.get('action') == 'add_set':
            exercise_name = request.form.get('exercise')
            custom_exercise = request.form.get('custom_exercise')
            exercise_notes = request.form.get('exercise_notes')

            # light error handling
            if exercise_name and custom_exercise:
                flash("Please select either a standard exercise OR a custom exercise, not both")
                return redirect(url_for('log_workout'))
            if not exercise_name and not custom_exercise:
                flash("Please select an exercise")
                return redirect(url_for('log_workout'))
            if not exercise_notes:
                exercise_notes = session.get('exercise_notes', '')
            if not request.form.get('reps'):
                flash('Reps are required')
                return redirect(url_for('log_workout'))

            selected_exercise = exercise_name if exercise_name else custom_exercise
            reps = int(request.form.get('reps'))
            bodyweight = request.form.get('bodyweight')
            weight = (request.form.get('weight'))

            if bodyweight:
                weight = None
            elif weight:
                weight = float(weight)
            else:
                weight = None

            if 'current_sets' not in session:
                session['current_sets'] = []
                
            if session.get('same_sets'):
                if not request.form.get('sets'):
                    flash('Enter Number of Sets')
                    return redirect(url_for('log_workout'))
                sets = int(request.form.get('sets'))
                session['current_sets'].append({
                    'same_sets': True,
                    'exercise': selected_exercise,
                    'exercise_notes': exercise_notes,
                    'sets': sets,
                    'reps': reps, 
                    'weight': weight,
                })
                session['same_sets'] = False
                print(session['current_sets'])

            else: 
                if 'current_set_number' not in session:
                    session['current_set_number'] = 1

                if session.get('current_exercise') != selected_exercise:
                    session['current_exercise'] = selected_exercise
                    session['current_set_number'] = 1
                
                session['current_sets'].append({
                'same_sets': False,
                'exercise': selected_exercise,
                'exercise_notes': exercise_notes,
                'set_number': session['current_set_number'],
                'reps': reps, 
                'weight': weight
                })
                
                session['current_set_number'] += 1

            session.modified = True

        elif request.form.get('action') == 'reset':
            session.clear()
            return redirect(url_for('log_workout'))
        
        elif request.form.get('action') == 'finish_workout':
            if 'current_workout_id' not in session:
                user_id = "1"
                session_id = insert_session(session['session_date'], session['session_notes'], user_id)
                session['current_workout_id'] = session_id
            
            exercises_processed = set()
            conn, c = establish_connection()
            try:
                for set_data in session['current_sets']:
                    # Only create workout_logs entry once per exercise
                    if set_data['exercise'] not in exercises_processed:
                        if set_data['exercise'] in custom_exercises:
                            exercise_id = None
                            custom_exercise_id = get_custom_exercise_id(c, set_data['exercise'], user_id)
                        else:
                            exercise_id = get_exercise_id(c, set_data['exercise'])
                            custom_exercise_id = None
                        
                        workout_log_id = insert_workout_log(c, session_id, exercise_id, custom_exercise_id, set_data['exercise_notes'])
                        exercises_processed.add(set_data['exercise'])

                    if set_data['same_sets'] == True:
                        for set_number in range(1, set_data['sets'] + 1):
                            insert_sets(c, workout_log_id, set_number, set_data['reps'], set_data['weight'])
                    else:
                        insert_sets(c, workout_log_id, set_data['set_number'], set_data['reps'], set_data['weight'])
            finally:
                close_connection(conn)

            session.clear()
            flash("Workout Logged Successfully!")
            return redirect(url_for('log_workout'))

            
    return render_template('log_workout.html', exercises=exercises, 
                        custom_exercises=custom_exercises,
                        current_sets = session.get('current_sets', []), 
                        date_selection=session.setdefault('date_selection', True),
                        same_sets=session.setdefault('same_sets', False))

# == VIEW WORKOUT ==
@app.route('/view_workout', methods= ['GET', 'POST'])
def view_workout():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        session['session_date'] = session_date
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
        if request.form.get('action') == 'save':
            conn, c = establish_connection()

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


# == CUSTOM EXERCISES ==
@app.route('/custom_exercises', methods=['GET', 'POST'])
def custom_exercises():
    custom_exercises = []
    editing_exercise = False
    user_id = "1"

    if request.method == 'POST':
        if request.form.get('action') == 'add_exercise':
            custom_exercise = request.form.get('create_custom_exercise')
            create_custom_exercise(user_id, custom_exercise)
            flash('Custom exercise added successfully!')
            return redirect(url_for('custom_exercises'))
        elif request.form.get('action') == 'view_exercises':
            custom_exercises = view_custom_exercises(user_id)
        elif request.form.get('action') == 'edit_exercises':
            editing_exercise = True
            custom_exercises = view_custom_exercises(user_id)
        elif request.form.get('action') == 'save_changes':
            old_exercises = request.form.getlist('old_exercise')
            new_exercises = request.form.getlist('new_exercise')

            conn, c = establish_connection()
            for old_exercise, new_exercise in zip(old_exercises, new_exercises):
                if old_exercise != new_exercise:
                    edit_custom_exercises(c, user_id, new_exercise, old_exercise)
            close_connection(conn)

    return render_template('custom_exercises.html', custom_exercises=custom_exercises, editing_exercise=editing_exercise)




# === CARDIO ===
# == HOME ==
@app.route('/cardio_home', methods=['GET', 'POST'])
def cardio_index():
    return render_template('cardio_index.html')


# == LOG CARDIO ==
@app.route('/log_cardio', methods=['GET', 'POST'])
def log_cardio():
    cardio_types = display_cardio_types()
    user_id = "1"

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

        elif request.form.get('action') == 'add_log':
            cardio_type = request.form.get('cardio_type')
            if request.form.get('hours'): hours = int(request.form.get('hours'))
            else: hours = 0
            if request.form.get('minutes'): minutes = int(request.form.get('minutes'))
            else: minutes = 0
            if request.form.get('seconds'): seconds = int(request.form.get('seconds'))
            else: seconds = 0
            db_duration = get_db_duration(hours, minutes, seconds)
            distance = request.form.get('distance')
            distance_unit = request.form.get('distance_unit')
            intensity = request.form.get('intensity')
            
            if distance and not distance_unit:
                flash("Please select either miles or kilometers")
                return redirect(url_for('log_cardio'))
            elif distance_unit and not distance:
                flash("Please enter distance")
                return redirect(url_for('log_cardio'))

            if 'current_logs' not in session:
                session['current_logs'] = []

            session['current_logs'].append({
                'cardio_type': cardio_type,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'db_duration': db_duration,
                'distance': distance,
                'distance_unit': distance_unit,
                'intensity': intensity
            })
            session.modified = True
        
        elif request.form.get('action') == 'finish_session':
            if 'current_logs' not in session:
                flash("Please add at least one cardio log before finishing up the session")
                return redirect(url_for('log_cardio'))
            else: 
                conn, c = establish_connection()
                session_id = log_cardio_session(c, session['session_date'], session['session_notes'], user_id)
                current_logs = session['current_logs']
                for log in current_logs:
                    print(log)
                    log_cardio_log(c, session_id, log['cardio_type'], log['db_duration'], log['distance'], log['distance_unit'], log['intensity'])
                close_connection(conn)
                session.clear()
                flash("Cardio Session Logged Successfully!")
                return redirect(url_for('log_cardio'))

        elif request.form.get('action') == 'reset':
            session.clear()
            return redirect(url_for('log_cardio'))

    return render_template('log_cardio.html', cardio_types=cardio_types, 
                           current_logs = session.get('current_logs', []),
                           date_selection=session.setdefault('date_selection', True))

# == VIEW CARDIO SESSION == 
@app.route('/view_cardio_session', methods= ['GET', 'POST'])
def view_cardio_session():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        user_id = "1"

        cardio_session = display_cardio_session(session_date, user_id)
        
        session['current_session'] = cardio_session
        session['session_searched'] = True
        session.modified = True
    else:
        session['session_searched'] = False

      
    return render_template('view_cardio_session.html', cardio_session=session.get('current_session', []), 
                           session_searched=session.get('session_searched', False))


# == EDIT CARDIO SESSION == 
@app.route('/edit_cardio_session/<session_date>', methods=['GET', 'POST'])
def edit_cardio_session(session_date):
    user_id = "1"
    cardio_session = session.get('current_session', [])

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            conn, c = establish_connection()

            session_id = request.form.get('session_id')
            new_session_date = request.form.get('session_date')
            
            # Update session date if changed
            if new_session_date and new_session_date != session_date:
                c.execute("""
                    UPDATE cardio_sessions
                    SET session_date = ?
                    WHERE id = ?
                    """, (new_session_date, session_id))
                
                return redirect(url_for('edit_cardio_session', session_date=new_session_date))
            
            # Update session notes
            session_notes = request.form.get('session_notes')
            if session_notes:
                c.execute("""
                    UPDATE cardio_sessions 
                    SET session_notes = ? 
                    WHERE id = ?
                """, (session_notes, session_id))

            # Update each cardio log
            for input in request.form:
                if input.startswith('log_id_'):
                    index = input.split('_')[-1]
                    log_id = request.form.get(f'log_id_{index}')
                    cardio_type = request.form.get(f'cardio_type_{index}')
                    duration = request.form.get(f'duration_{index}')
                    distance = request.form.get(f'distance_{index}')
                    distance_unit = request.form.get(f'distance_unit_{index}')
                    intensity = request.form.get(f'intensity_{index}')
                    
                    # Get cardio_type_id
                    result = c.execute("SELECT cardio_type_id FROM cardio_types WHERE cardio_type_name = ?", (cardio_type,)).fetchone()
                    if result:
                        cardio_type_id = result[0]
                        c.execute("""
                            UPDATE cardio_logs
                            SET cardio_type_id = ?, duration = ?, distance = ?, distance_unit = ?, intensity = ?
                            WHERE id = ?
                        """, (cardio_type_id, duration, 
                              distance if distance else None, 
                              distance_unit if distance_unit else None,
                              intensity if intensity else None,
                              log_id))
            
            conn.commit()
            conn.close()
            
            flash("Cardio session updated successfully!")
            return redirect(url_for('view_cardio_session'))

    return render_template('edit_cardio_session.html', cardio_session=cardio_session, session_date=session_date)


# == CUSTOM CARDIO ==
@app.route('/custom_cardio', methods=['GET', 'POST'])
def custom_cardio():
    custom_cardio = []
    editing_cardio = False
    user_id = "1"

    if request.method == 'POST':
        if request.form.get('action') == 'add_cardio':
            custom_cardio = request.form.get('create_custom_cardio')
            create_custom_cardio(user_id, custom_cardio)
            flash('Custom cardio added successfully!')
            return redirect(url_for('custom_cardio'))
        elif request.form.get('action') == 'view_custom_cardio':
            custom_cardio = view_custom_cardio(user_id)
        elif request.form.get('action') == 'edit_cardio':
            editing_cardio = True
            custom_cardio = view_custom_cardio(user_id)
        elif request.form.get('action') == 'save_changes':
            old_cardio = request.form.getlist('old_cardio')
            new_cardio = request.form.getlist('new_cardio')

            conn, c = establish_connection()
            for old_card, new_card in zip(old_cardio, new_cardio):
                if old_card != new_card:
                    edit_custom_cardio(c, user_id, new_card, old_card)
            close_connection(conn)

    return render_template('custom_cardio.html', custom_cardio=custom_cardio, editing_cardio=editing_cardio)

if __name__ == '__main__':
    app.run(debug=True)