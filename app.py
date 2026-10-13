from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from utils.user_class import User
from utils.db import *
from utils.session_helpers import *
from utils.email_service import *
import os

# == APP CONFIG ==
app = Flask(__name__)
env = os.environ.get('FLASK_ENV', 'dev')
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

# == AUTH ==
@login_manager.user_loader
def load_user(user_id):
    user = get_user(id=int(user_id))

    if not user: return None
    
    return User(
        id=user['id'], 
        first_name=user['first_name'], last_name=user['last_name'], 
        username=user['username'], email=user['email'])

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
        
        user = get_user(username=username)
        
        if not user:
            flash("Incorrect username or password")
            return redirect(url_for('login'))
        
        password_hash = user['password_hash']
        if check_password_hash(password_hash, password):
            if not user['verified']:
                flash("Please verify your email before logging in.")
                return redirect(url_for('login'))
            
            user = User(
                id=user['id'], 
                first_name=user['first_name'], last_name=user['last_name'], 
                username=user['username'], email=user['email'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Incorrect username or password. Please try again")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/verify/<token>')
def verify_email(token):
    user_id, message = verify_user_token(token)
    flash(message)

    if user_id:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('register'))

@app.route('/forgot_username', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def forgot_username():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user(email=email)

        if user:
            send_username_email(email, user['username'])
        
        flash("If an account with that email exists, you'll receive an email shortly.")
        return redirect(url_for('forgot_username'))

    return render_template('forgot_username.html')
 
@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user(email=email)
        
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
    exercises = get_exercises()
    return render_template('exercises.html', exercises=exercises)

# == LOG WORKOUT ==
@app.route('/log_workout', methods=['POST', 'GET'])
@login_required
def log_workout():
    user_id = current_user.id

    exercises = get_exercises()
    custom_exercises = get_custom_exercises(user_id)
    exercise_ids = {row['exercise']: row['id'] for row in exercises}
    custom_exercise_ids = {row['exercise']: row['id'] for row in custom_exercises}

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

        elif request.form.get('action') == 'add_set':
            exercise = request.form.get('exercise')
            custom_exercise = request.form.get('custom_exercise')
            exercise_notes = request.form.get('exercise_notes')
            sets = (request.form.get('sets'))
            reps = (request.form.get('reps'))
            bodyweight = request.form.get('bodyweight')
            weight = (request.form.get('weight'))

            if exercise and custom_exercise:
                flash("Please select either a standard exercise OR a custom exercise, not both")
                return redirect(url_for('log_workout'))
            if not exercise and not custom_exercise:
                flash("Please select an exercise")
                return redirect(url_for('log_workout'))
            if not exercise_notes: exercise_notes = None
            if not reps:
                flash('Reps are required')
                return redirect(url_for('log_workout'))
            reps = int(reps)

            sets = int(sets) if sets else None

            if exercise:
                selected_exercise = exercise
                exercise_id = exercise_ids.get(selected_exercise)
                is_custom = False
            else:
                selected_exercise = custom_exercise
                exercise_id = custom_exercise_ids.get(selected_exercise)
                is_custom = True
        
            if bodyweight: weight = None
            elif weight: weight = float(weight)
            else: weight = None


            if not session.get('current_sets'): session['current_sets'] = []

            if sets:
                session['current_sets'].append({
                    'exercise': selected_exercise,
                    'exercise_id': exercise_id,
                    'is_custom': is_custom,
                    'exercise_notes': exercise_notes,
                    'same_sets': True,
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
                    'exercise': selected_exercise,
                    'exercise_id': exercise_id,
                    'is_custom': is_custom,
                    'exercise_notes': exercise_notes,
                    'same_sets': False,
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
            clear_sets(session)
            return redirect(url_for('log_workout'))
        elif request.form.get('action') == 'back':
            clear_workout_session(session)
            return redirect(url_for('log_workout'))
        
        elif request.form.get('action') == 'finish_workout':
            if 'current_sets' not in session:
                flash("Please enter at least one set")
                return redirect(url_for('log_workout'))


            grouped_sets = group_sets(session['current_sets'])
            create_workout(session['session_date'], session['session_notes'], user_id, grouped_sets)

            clear_workout_session(session)
            flash("Workout Logged Successfully!")
            return redirect(url_for('log_workout'))

            
    return render_template('log_workout.html', exercises=exercises, 
                        custom_exercises=custom_exercises,
                        time_based_exercises=[row['exercise'] for row in exercises if row['is_time_based']],
                        time_based_custom_exercises=[row['exercise'] for row in custom_exercises if row['is_time_based']],
                        current_set=session.get('current_sets', []), 
                        date_selection=session.setdefault('date_selection', True)
                        )
                        

# == VIEW WORKOUT ==
@app.route('/view_workout', methods= ['GET', 'POST'])
@login_required
def view_workout():
    if request.method == 'POST':
        session_date = request.form.get('session_date')
        #NOTE should the session date be stored in session?
        session['session_date'] = session_date
        user_id = current_user.id

        workouts = get_workout(session_date, user_id)
        
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
            with db_connection() as (conn, c):
                try:
                    session_id = request.form.get('session_id')
                    new_session_date = request.form.get('session_date')
                    if new_session_date and new_session_date != session_date:
                        c.execute("UPDATE workout_sessions SET session_date = ? WHERE id = ?",
                                (new_session_date, session_id))
                        return redirect(url_for('edit_workout', session_date=new_session_date))

                    session_notes = request.form.get('session_notes')
                    if session_notes:
                        c.execute("UPDATE workout_sessions SET session_notes = ? WHERE id = ?",
                                (session_notes, session_id))

                    for input in request.form:
                        # ====================================
                        #FIXME RETURN TO THIS LATER TO FIX THIS
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

                    flash("Workout updated successfully!")
                    return redirect(url_for('view_workout'))

                except sqlite3.Error:
                    conn.rollback()
                    flash("Could not edit workout. Try again.")
                    return redirect(url_for('view_workout'))

    #TODO after pressing save changes, this should immediately render with the new changes
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
            custom_exercises = get_custom_exercises(user_id)
            if not custom_exercises:
                flash("No custom exercises have been created")
        elif request.form.get('action') == 'edit_exercises':
            editing_exercise = True
            custom_exercises = get_custom_exercises(user_id)
        elif request.form.get('action').startswith('delete_'):
            action = request.form.get('action')
            exercise_id = action.split('_')[1]
            success = delete_custom_exercise(user_id, exercise_id)
            if not success:
                flash("Can't delete this exercise — it's been used in a workout.")
            editing_exercise = True
            custom_exercises = get_custom_exercises(user_id)
        elif request.form.get('action') == 'save_changes':
            old_exercises = request.form.getlist('old_exercise')
            exercise_ids = request.form.getlist('exercise_id')
            new_exercises = request.form.getlist('new_exercise')
            for exercise_id, old_exercise, new_exercise in zip(exercise_ids, old_exercises, new_exercises):
                if old_exercise != new_exercise:
                    if not update_custom_exercise(user_id, new_exercise, exercise_id):
                        flash(f"Couldn't update {old_exercise}.")
            flash("Exercises succesfully edited")
            return redirect(url_for('custom_exercises'))

    return render_template('custom_exercises.html', 
                           custom_exercises=custom_exercises, 
                           editing_exercise=editing_exercise)


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
    cardio_types = get_cardio_types()
    cardio_type_ids = {row['cardio_type']: row['id'] for row in cardio_types}
    user_id = current_user.id

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

        #TODO consider which of these should be stored as NULL vs 0
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

            if not distance: distance = None
            if not distance_unit: distance_unit = None
            if not intensity: intensity = None

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
                'cardio_type_id': cardio_type_ids.get(cardio_type),
                'custom_cardio_id': None,
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
                grouped_logs = group_logs(session['current_logs'])
                create_cardio_session(session['session_date'], session['session_notes'], user_id, grouped_logs)
                clear_cardio_session(session)
                flash("Cardio Session Logged Successfully!")
                return redirect(url_for('log_cardio'))

        elif request.form.get('action') == 'reset':
            clear_logs(session)
            return redirect(url_for('log_cardio'))
        elif request.form.get('action') == 'back':
            clear_cardio_session(session)
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

        cardio_session = get_cardio_session(session_date, user_id)
        
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
            with db_connection() as (conn, c):
                session_id = request.form.get('session_id')
                new_session_date = request.form.get('session_date')

                if new_session_date and new_session_date != session_date:
                    c.execute("""
                        UPDATE cardio_sessions
                        SET session_date = ?
                        WHERE id = ?
                        """, (new_session_date, session_id))

                    return redirect(url_for('edit_cardio_session', session_date=new_session_date))

                session_notes = request.form.get('session_notes')
                if session_notes:
                    c.execute("""
                        UPDATE cardio_sessions
                        SET session_notes = ?
                        WHERE id = ?
                    """, (session_notes, session_id))

                for input in request.form:
                    if input.startswith('log_id_'):
                        index = input.split('_')[-1]
                        log_id = request.form.get(f'log_id_{index}')
                        cardio_type = request.form.get(f'cardio_type_{index}')
                        duration = request.form.get(f'duration_{index}')
                        distance = request.form.get(f'distance_{index}')
                        distance_unit = request.form.get(f'distance_unit_{index}')
                        intensity = request.form.get(f'intensity_{index}')

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
            custom_cardio = get_custom_cardio(user_id)
            if not custom_cardio:
                flash("No custom cardio types have been created")
        elif request.form.get('action') == 'edit_cardio':
            editing_cardio = True
            custom_cardio = get_custom_cardio(user_id)
        elif request.form.get('action').startswith('delete_'):
            action = request.form.get('action')
            cardio_id = action.split('_')[1]
            success = delete_custom_cardio(user_id, cardio_id)
            if not success:
                flash("Can't delete this cardio type — it's been used in a session.")
            editing_cardio = True
            custom_cardio = get_custom_cardio(user_id)
        elif request.form.get('action') == 'save_changes':
            old_cardio = request.form.getlist('old_cardio')
            cardio_id = request.form.getlist('cardio_id')
            new_cardio = request.form.getlist('new_cardio')

            for cardio_id, old_card, new_card in zip(cardio_id, old_cardio, new_cardio):
                if old_card != new_card:
                    if not update_custom_cardio(user_id, new_card, cardio_id):
                        flash(f"Couldn't update {old_card}.")

    return render_template('custom_cardio.html', custom_cardio=custom_cardio, editing_cardio=editing_cardio)


if __name__ == '__main__':
    app.run(debug=True)