from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from user_class import User
from sql_functions import *
from flask_wtf.csrf import CSRFProtect
import os

# == APP CONFIG ==
app = Flask(__name__)
env = os.environ.get('FLASK_ENV', 'development')
if env == 'production': app.config.from_object('config.ProdConfig')
else: app.config.from_object('config.DevConfig')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
csrf = CSRFProtect(app)

# == LIMITER ==
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour"]
)

# == HTTP ==
@app.after_request
def add_cache_headers(response):
    if response.content_type and response.content_type.startswith('text/html'):
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# == LOGIN & WHATNOT ==
@login_manager.user_loader
def load_user(user_id):
    data = get_user_by_id(int(user_id))

    if not data:
        return None
    
    user = User(id=data[0], first_name=data[1], last_name=data[2], username=data[3], email=data[4])
    return user

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_hash = generate_password_hash(password)

        if create_user(first_name, last_name, username, password_hash, email):
            token = generate_verification_token()
            save_verification_token(email, token)
            send_verification_email(email, token)

            flash("Registration successful! Check your email to verify your account.")
            return redirect(url_for('register'))
        else:
            flash("Username or email already exists.")
            return redirect(url_for('register'))
    
    return render_template('register.html')
    
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        data = get_user_by_username(username)
        
        if not data:
            flash("Incorrect username or password")
            return redirect(url_for('login'))
        
        password_hash = data[5]
        if check_password_hash(password_hash, password):
            if data[6] == 0:
                flash("Please verify your email before logging in.")
                return redirect(url_for('login'))
            
            user = User(id=data[0], first_name=data[1], last_name=data[2], 
            username=data[3], email=data[4])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Incorrect username or password. Please try again")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/verify/<token>')
def verify_email(token):
    success, message = verify_user_token(token)
    flash(message)

    if success:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('register'))

@app.route('/forgot_username', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def forgot_username():
    if request.method == 'POST':
        email = request.form.get('email')
        username = get_username_by_email(email)

        if username:
            send_username_email(email, username)
        
        flash("If an account with that email exists, you'll receive an email shortly.")
        return redirect(url_for('forgot_username'))

    return render_template('forgot_username.html')
 
@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user_by_email(email)
        
        if user:
            token = generate_verification_token()
            save_reset_token(email, token)
            send_password_reset_email(email, token)
        
        flash("If an account with that email exists, you'll receive a reset link.")
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id, message = verify_reset_token(token)
    
    if not user_id:
        flash(message)
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        
        if password != confirmation:
            flash("Passwords don't match")
            return redirect(url_for('reset_password', token=token))
        
        password_hash = generate_password_hash(password)
        update_password(user_id, password_hash)
        clear_reset_token(user_id)
        
        flash("Password updated! You can now log in.")
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("See ya next time!")
    return redirect(url_for('login'))

# == MAIN PAGE ==
@app.route('/')
@login_required
def index():
    return render_template('landing.html')

# =============
# WEIGHTLIFTING 
# =============

# == HOME ==
@app.route('/weightlifting_home')
@login_required
def weightlifting_index():
    return render_template('weightlifting_index.html')

# == EXERCISE LIST ==
@app.route('/exercises', methods=['GET'])
@login_required
def exercises():
    conn, c = establish_connection()
    exercises = display_exercises(c)
    close_connection(conn)
    return render_template('exercises.html', exercises=exercises)

# == LOG WORKOUT ==
@app.route('/log_workout', methods=['POST', 'GET'])
@login_required
def log_workout():
    user_id = current_user.id
    
    keys = ['exercises', 'custom_exercises', 'time_based_exercises', 'time_based_custom_exercises']
    if any(key not in session for key in keys):
        conn, c = establish_connection()
        data = {
            'exercises': display_exercises(c),
            'custom_exercises': display_custom_exercises(c, user_id),
            'time_based_exercises': get_time_based_exercises(c),
            'time_based_custom_exercises': get_time_based_custom_exercises(c, user_id)
            }
        close_connection(conn)
        session.update(data)

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

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

            sets_input = request.form.get('sets')
                
            if sets_input:
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

        elif request.form.get('action').startswith('delete_'):
            action = request.form.get('action')
            index = int(action.split('_')[1])
            current_sets = session.get('current_sets', [])
            if 0 <= index < len(current_sets):
                current_sets.pop(index)
                session['current_sets'] = current_sets
                session.modified = True
            return redirect(url_for('log_workout'))

        elif request.form.get('action') == 'reset':
            clear_sets()
            return redirect(url_for('log_workout'))
        elif request.form.get('action') == 'back':
            clear_workout_session()
            return redirect(url_for('log_workout'))
        
        elif request.form.get('action') == 'finish_workout':
            if 'current_sets' not in session:
                flash("Please enter at least one set")
                return redirect(url_for('log_workout'))
            if 'current_workout_id' not in session:
                user_id = current_user.id
                session_id = insert_workout_session(session['session_date'], session['session_notes'], user_id)
                session['current_workout_id'] = session_id
                print(session_id)
            
            exercises_processed = set()
            conn, c = establish_connection()
            try:
                for set_data in session['current_sets']:
                    if set_data['exercise'] not in exercises_processed:
                        if set_data['exercise'] in [exercise['name'] for exercise in session['custom_exercises']]:
                            exercise_id = None
                            custom_exercise_id = get_custom_exercise_id(c, set_data['exercise'], user_id)
                        else:
                            exercise_id = get_exercise_id(c, set_data['exercise'])
                            custom_exercise_id = None
                        
                        workout_log_id = insert_workout_log(c, conn, session['current_workout_id'], exercise_id, custom_exercise_id, set_data['exercise_notes'])
                        if workout_log_id:
                            print(workout_log_id)
                        exercises_processed.add(set_data['exercise'])
                    #consider using ".executemany()"
                    if set_data['same_sets'] == True:
                        for set_number in range(1, set_data['sets'] + 1):
                            insert_workout_sets(c, conn, workout_log_id, set_number, set_data['reps'], set_data['weight'])
                    else:
                        insert_workout_sets(c, conn, workout_log_id, set_data['set_number'], set_data['reps'], set_data['weight'])
            finally:
                conn.commit()
                close_connection(conn)

            clear_workout_session()
            flash("Workout Logged Successfully!")
            return redirect(url_for('log_workout'))

            
    return render_template('log_workout.html', exercises=session.get('exercises', []), 
                        custom_exercises=session.get('custom_exercises', []),
                        current_sets = session.get('current_sets', []), 
                        date_selection=session.setdefault('date_selection', True),
                        time_based_exercises=session.get('time_based_exercises', []),
                        time_based_custom_exercises=session.get('time_based_custom_exercises', []))

# == VIEW WORKOUT ==
@app.route('/view_workout', methods= ['GET', 'POST'])
@login_required
def view_workout():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        # should the session date be stored in session?
        session['session_date'] = session_date
        user_id = current_user.id

        workouts = display_workout(session_date, user_id)
        print(workouts)
        
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
@login_required
def edit_workout(session_date):
    user_id = current_user.id
    
    if request.method == 'POST':
        if request.form.get('action') == 'save':
            conn, c = establish_connection()
            try:
                session_id = request.form.get('session_id')
                new_session_date = request.form.get('session_date')
                if new_session_date and new_session_date != session_date:
                    c.execute("UPDATE workout_sessions SET session_date = ? WHERE id = ?",
                            (new_session_date, session_id))
                    conn.commit()
                    return redirect(url_for('edit_workout', session_date=new_session_date))

                session_notes = request.form.get('session_notes')
                if session_notes:
                    c.execute("UPDATE workout_sessions SET session_notes = ? WHERE id = ?",
                            (session_notes, session_id))

                for input in request.form:
                    # ====================================
                    # RETURN TO THIS LATER TO FIX THIS
                    # ====================================

                    # if input.startswith('exercise_name_'):
                    #             index = input.split('_')[-1]
                    #             workout_log_id = request.form.get(f'workout_log_id_{index}')
                    #             exercise_name = request.form.get(f'exercise_name_{index}')
                                
                    #             result = c.execute("SELECT id FROM exercises WHERE exercise = ?", (exercise_name,)).fetchone()
                    #             if result:
                    #                 exercise_id = result[0]
                    #                 c.execute("""
                    #                     UPDATE workout_logs
                    #                     SET exercise_id = ?
                    #                     WHERE id = ?
                    #                 """, (exercise_id, workout_log_id))
                    #                 conn.commit()

                    # ====================================
                    # RETURN TO THIS LATER TO FIX THIS
                    # ====================================
                    
                    if input.startswith('exercise_notes_'):
                        index = input.split('_')[-1]
                        workout_log_id = request.form.get(f'workout_log_id_{index}')
                        exercise_notes = request.form.get(f'exercise_notes_{index}')
                        c.execute("UPDATE workout_logs SET exercise_notes = ? WHERE id = ?",
                                (exercise_notes, workout_log_id))
                    elif input.startswith('set_id_'):
                        index = input.split('_')[-1]
                        set_id = request.form.get(f'set_id_{index}')
                        reps = request.form.get(f'reps_{index}')
                        weight = request.form.get(f'weight_{index}')
                        c.execute("UPDATE workout_sets SET reps = ?, weight = ? WHERE id = ?",
                                (reps, weight, set_id))

                conn.commit()
                flash("Workout updated successfully!")
                return redirect(url_for('view_workout'))

            except sqlite3.Error:
                conn.rollback()
                flash("Could not edit workout. Try again.")
                return redirect(url_for('view_workout'))
            finally:
                conn.close()

    # after pressing save changes, this should immediately render with the new changes
    return render_template('edit_workout.html', 
                            workouts=session.get('current_workout', []), 
                            session_date=session_date)

# == CUSTOM EXERCISES ==
@app.route('/custom_exercises', methods=['GET', 'POST'])
@login_required
def custom_exercises():
    custom_exercises = []
    editing_exercise = False
    user_id = current_user.id

    if request.method == 'POST':
        if request.form.get('action') == 'add_exercise':
            custom_exercise = request.form.get('create_custom_exercise')
            if not custom_exercise:
                flash("Please enter name of exercise")
                return redirect(url_for('custom_exercises'))
            create_custom_exercise(user_id, custom_exercise)
            flash('Custom exercise added successfully!')
            return redirect(url_for('custom_exercises'))
        elif request.form.get('action') == 'view_exercises':
            conn, c = establish_connection()
            custom_exercises = display_custom_exercises(c, user_id)
            close_connection(conn)
            if not custom_exercises:
                flash("No custom exercises have been created")
        elif request.form.get('action') == 'edit_exercises':
            editing_exercise = True
            conn, c = establish_connection()
            custom_exercises = display_custom_exercises(c, user_id)
            close_connection(conn)
        elif request.form.get('action').startswith('delete_'):
            action = request.form.get('action')
            exercise_id = action.split('_')[1]
            success = delete_custom_exercise(user_id, exercise_id)
            if not success:
                flash("Can't delete this exercise — it's been used in a workout.")
            editing_exercise = True
            conn, c = establish_connection()
            custom_exercises = display_custom_exercises(c, user_id)
            conn.commit()
            close_connection(conn)
        elif request.form.get('action') == 'save_changes':
            old_exercises = request.form.getlist('old_exercise')
            exercise_ids = request.form.getlist('exercise_id')
            new_exercises = request.form.getlist('new_exercise')
            conn, c = establish_connection()
            for exercise_id, old_exercise, new_exercise in zip(exercise_ids, old_exercises, new_exercises):
                if old_exercise != new_exercise:
                    edit_custom_exercises(c, user_id, new_exercise, exercise_id)
            conn.commit()
            close_connection(conn)
            flash("Exercises succesfully edited")
            return redirect(url_for('custom_exercises'))

    return render_template('custom_exercises.html', custom_exercises=custom_exercises, editing_exercise=editing_exercise)


# =============
# CARDIO 
# =============

# == HOME ==
@app.route('/cardio_home', methods=['GET', 'POST'])
@login_required
def cardio_index():
    return render_template('cardio_index.html')

# == LOG CARDIO ==
@app.route('/log_cardio', methods=['GET', 'POST'])
@login_required
def log_cardio():
    conn, c = establish_connection()
    cardio_types = display_cardio_types(c)
    close_connection(conn)
    user_id = current_user.id

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
            
            if not distance and not db_duration:
                flash("Please enter either distance or duration")
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
                session_id = log_cardio_session(c, conn, session['session_date'], session['session_notes'], user_id)
                current_logs = session['current_logs']
                for log in current_logs:
                    log_cardio_log(c, conn, session_id, log['cardio_type'], log['db_duration'], log['distance'], log['distance_unit'], log['intensity'])
                conn.commit()
                close_connection(conn)
                clear_cardio_session()
                flash("Cardio Session Logged Successfully!")
                return redirect(url_for('log_cardio'))

        elif request.form.get('action') == 'reset':
            clear_logs()
            return redirect(url_for('log_cardio'))
        elif request.form.get('action') == 'back':
            clear_cardio_session()
            return redirect(url_for('log_cardio'))

    return render_template('log_cardio.html', cardio_types=cardio_types, 
                           current_logs = session.get('current_logs', []),
                           date_selection=session.setdefault('date_selection', True))

# == VIEW CARDIO SESSION == 
@app.route('/view_cardio_session', methods= ['GET', 'POST'])
@login_required
def view_cardio_session():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        user_id = current_user.id

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
@login_required
def edit_cardio_session(session_date):
    user_id = current_user.id
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
                    result = c.execute("SELECT id FROM cardio_types WHERE cardio_type = ?", (cardio_type,)).fetchone()
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
@login_required
def custom_cardio():
    custom_cardio = []
    editing_cardio = False
    user_id = current_user.id

    if request.method == 'POST':
        if request.form.get('action') == 'add_cardio':
            custom_cardio = request.form.get('create_custom_cardio')
            if not custom_cardio:
                flash("Please enter a name for the cardio type")
                return redirect(url_for('custom_cardio'))
            create_custom_cardio(user_id, custom_cardio)
            flash('Custom cardio added successfully!')
            return redirect(url_for('custom_cardio'))
        elif request.form.get('action') == 'view_custom_cardio':
            conn, c = establish_connection()
            custom_cardio = display_custom_cardio(c, user_id)
            close_connection(conn)
            if not custom_cardio:
                flash("No custom cardio types have been created")
        elif request.form.get('action') == 'edit_cardio':
            editing_cardio = True
            conn, c = establish_connection()
            custom_cardio = display_custom_cardio(c, user_id)
            conn.commit()
            close_connection(conn)
        elif request.form.get('action').startswith('delete_'):
            action = request.form.get('action')
            cardio_id = action.split('_')[1]
            print(user_id)
            success = delete_custom_cardio(user_id, cardio_id)
            if not success:
                flash("Can't delete this cardio type — it's been used in a session.")
            editing_cardio = True
            conn, c = establish_connection()
            custom_cardio = display_custom_cardio(c, user_id)
            conn.commit()
            close_connection(conn)
        elif request.form.get('action') == 'save_changes':
            old_cardio = request.form.getlist('old_cardio')
            cardio_id = request.form.getlist('cardio_id')
            new_cardio = request.form.getlist('new_cardio')

            conn, c = establish_connection()
            for cardio_id, old_card, new_card in zip(cardio_id, old_cardio, new_cardio):
                if old_card != new_card:
                    edit_custom_cardio(c, user_id, new_card, cardio_id)
            conn.commit()
            close_connection(conn)

    return render_template('custom_cardio.html', custom_cardio=custom_cardio, editing_cardio=editing_cardio)


if __name__ == '__main__':
    app.run(debug=True)