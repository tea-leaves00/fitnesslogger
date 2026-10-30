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

# ====
# AUTH
# ====

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
            #NOTE any point of these local variables?
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

        elif request.form.get('action') == 'add_set':
            exercise = request.form.get('exercise')
            custom_exercise = request.form.get('custom_exercise')
            exercise_notes = request.form.get('exercise_notes') or None
            sets = request.form.get('sets', type=int)
            reps = request.form.get('reps', type=int)
            bodyweight = request.form.get('bodyweight')
            weight = request.form.get('weight', type=float)

            #TODO move this validation to a function/separate module
            if exercise and custom_exercise:
                flash("Please select either a standard exercise OR a custom exercise, not both")
                return redirect(url_for('log_workout'))
            if not exercise and not custom_exercise:
                flash("Please select an exercise")
                return redirect(url_for('log_workout'))
            if not reps:
                flash('Reps are required')
                return redirect(url_for('log_workout'))

            if exercise:
                selected_exercise = exercise
                exercise_id = exercise_ids.get(selected_exercise)
                is_custom = False
            else:
                selected_exercise = custom_exercise
                exercise_id = custom_exercise_ids.get(selected_exercise)
                is_custom = True
        
            if bodyweight: weight = None


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
                        current_sets=session.get('current_sets', []), 
                        date_selection=session.setdefault('date_selection', True)
                        )
                        
# == VIEW WORKOUT ==
@app.route('/view_workout', methods= ['GET', 'POST'])
@login_required
def view_workout():
    if request.method == 'POST':
        session['view_workout_date'] = request.form.get('session_date')
        workout_searched = True
    else:
        workout_searched = False

    session_date = session.get('view_workout_date')
    workouts = get_workout(session_date, current_user.id) if session_date else []

    return render_template('view_workout.html',
                           workouts=workouts,
                           workout_searched=workout_searched)

# == EDIT WORKOUT == 
@app.route('/edit_workout/<session_date>', methods=['GET', 'POST'])
@login_required
def edit_workout(session_date):
    exercises = get_exercises()
    custom_exercises = get_custom_exercises(current_user.id)
    exercise_ids = {row['exercise']: row['id'] for row in exercises}
    custom_exercise_ids = {row['exercise']: row['id'] for row in custom_exercises}

    if request.method == 'POST':
        session_updates = []
        for session_id in request.form.getlist('session_id'):
            new_session_date = request.form.get(f'session_date_{session_id}')
            session_notes = request.form.get(f'session_notes_{session_id}') or None
            session_updates.append((new_session_date, session_notes, session_id))

        log_updates = []
        for workout_log_id in request.form.getlist('workout_log_id'):
            exercise = request.form.get(f'exercise_{workout_log_id}')
            custom_exercise = request.form.get(f'custom_exercise_{workout_log_id}')
            exercise_notes = request.form.get(f'exercise_notes_{workout_log_id}') or None

            if exercise and custom_exercise:
                flash("Please select either a standard exercise OR a custom exercise, not both")
                return redirect(url_for('edit_workout', session_date=session_date))
            if not exercise and not custom_exercise:
                flash("Please select an exercise")
                return redirect(url_for('edit_workout', session_date=session_date))

            exercise_id = exercise_ids.get(exercise)
            custom_exercise_id = custom_exercise_ids.get(custom_exercise)
            if not exercise_id and not custom_exercise_id:
                flash(f"'{exercise or custom_exercise}' isn't in your exercise list")
                return redirect(url_for('edit_workout', session_date=session_date))

            log_updates.append((exercise_id, custom_exercise_id, exercise_notes, workout_log_id))

        set_updates = []
        for set_id in request.form.getlist('set_id'):
            reps = request.form.get(f'reps_{set_id}', type=int)
            weight = request.form.get(f'weight_{set_id}', type=float)
            if not reps:
                flash("Reps are required")
                return redirect(url_for('edit_workout', session_date=session_date))
            set_updates.append((reps, weight, set_id))

        try:
            update_workout(current_user.id, session_updates, log_updates, set_updates)
        except sqlite3.IntegrityError:
            flash("Could not edit workout. Please try again.")
            return redirect(url_for('edit_workout', session_date=session_date))

        session.pop('view_workout_date', None)
        flash("Workout updated successfully! View another workout?")
        return redirect(url_for('view_workout'))

    workouts = get_workout(session_date, current_user.id)
    return render_template('edit_workout.html',
                            workouts=workouts,
                            exercises=exercises,
                            custom_exercises=custom_exercises,
                            session_date=session_date)

# == CUSTOM EXERCISES ==
@app.route('/custom_exercises', methods=['GET', 'POST'])
@login_required
def custom_exercises():
    user_id = current_user.id

    if request.method == 'POST':
        if request.form.get('action') == 'add_exercise':
            custom_exercise = request.form.get('create_custom_exercise').strip()
            if not custom_exercise:
                flash("Please enter name of exercise")
                return redirect(url_for('custom_exercises'))
            if not create_custom_exercise(user_id, custom_exercise):
                flash(f"You already have an exercise named '{custom_exercise}'")
                return redirect(url_for('custom_exercises'))
            flash('Custom exercise added successfully!')
            return redirect(url_for('custom_exercises'))
        elif request.form.get('action').startswith('delete_'):
            exercise_id = request.form.get('action').split('_')[1]
            if not delete_custom_exercise(user_id, exercise_id):
                flash("Can't delete this exercise — it's been used in a workout.")
            return redirect(url_for('custom_exercises', edit=1))
        elif request.form.get('action') == 'save_changes':
            old_exercises = request.form.getlist('old_exercise')
            exercise_ids = request.form.getlist('exercise_id')
            new_exercises = [name.strip() for name in request.form.getlist('new_exercise')]
            for exercise_id, old_exercise, new_exercise in zip(exercise_ids, old_exercises, new_exercises):
                if old_exercise != new_exercise:
                    if not new_exercise or not update_custom_exercise(user_id, new_exercise, exercise_id):
                        flash(f"Couldn't rename '{old_exercise}' (blank or duplicate name). Any edits below it weren't saved.")
                        return redirect(url_for('custom_exercises', edit=1))
            flash("Exercises successfully edited")
            return redirect(url_for('custom_exercises'))

    custom_exercises = get_custom_exercises(user_id)
    editing_exercise = request.args.get('edit')
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
    user_id = current_user.id

    cardio_types = get_cardio_types()
    custom_cardio = get_custom_cardio(user_id)
    cardio_type_ids = {row['cardio_type']: row['id'] for row in cardio_types}
    custom_cardio_ids = {row['cardio_type']: row['id'] for row in custom_cardio}

    if request.method == 'POST':
        if request.form.get('action') == 'select_date':
            session_date = request.form.get('session_date')
            session_notes = request.form.get('session_notes')
            session['session_date'] = session_date
            session['session_notes'] = session_notes
            session['date_selection'] = False

        elif request.form.get('action') == 'add_log':
            cardio_type = request.form.get('cardio_type')
            custom_cardio_type = request.form.get('custom_cardio')
            hours = request.form.get('hours', 0, type=int)
            minutes = request.form.get('minutes', 0, type=int)
            seconds = request.form.get('seconds', 0, type=int)
            db_duration = get_db_duration(hours, minutes, seconds) or None
            distance = request.form.get('distance', type=float) or None
            distance_unit = request.form.get('distance_unit') or None
            intensity = request.form.get('intensity', type=int) or None

            if cardio_type and custom_cardio_type:
                flash("Please select either a standard cardio type OR a custom cardio type, not both")
                return redirect(url_for('log_cardio'))
            if not cardio_type and not custom_cardio_type:
                flash("Please select a cardio type")
                return redirect(url_for('log_cardio'))

            cardio_type_id = cardio_type_ids.get(cardio_type)
            custom_cardio_id = custom_cardio_ids.get(custom_cardio_type)
            if not cardio_type_id and not custom_cardio_id:
                flash(f"'{cardio_type or custom_cardio_type}' isn't in your cardio list")
                return redirect(url_for('log_cardio'))

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
                'cardio_type': cardio_type or custom_cardio_type,
                'cardio_type_id': cardio_type_id,
                'custom_cardio_id': custom_cardio_id,
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
            if not session.get('current_logs'):
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
                           custom_cardio=custom_cardio,
                           current_logs = session.get('current_logs', []),
                           date_selection=session.setdefault('date_selection', True))

# == VIEW CARDIO SESSION == 
@app.route('/view_cardio_session', methods= ['GET', 'POST'])
@login_required
def view_cardio_session():
    if request.method == 'POST':
        session['view_cardio_date'] = request.form.get('session_date')
        session_searched = True
    else:
        session_searched = False

    session_date = session.get('view_cardio_date')
    cardio_session = get_cardio_session(session_date, current_user.id) if session_date else []

    return render_template('view_cardio_session.html',
                           cardio_session=cardio_session,
                           session_searched=session_searched)

# == EDIT CARDIO SESSION == 
@app.route('/edit_cardio_session/<session_date>', methods=['GET', 'POST'])
@login_required
def edit_cardio_session(session_date):
    cardio_types = get_cardio_types()
    custom_cardio = get_custom_cardio(current_user.id)
    cardio_type_ids = {row['cardio_type']: row['id'] for row in cardio_types}
    custom_cardio_ids = {row['cardio_type']: row['id'] for row in custom_cardio}

    if request.method == 'POST':
        session_updates = []
        for session_id in request.form.getlist('session_id'):
            new_session_date = request.form.get(f'session_date_{session_id}')
            session_notes = request.form.get(f'session_notes_{session_id}') or None
            session_updates.append((new_session_date, session_notes, session_id))

        log_updates = []
        for log_id in request.form.getlist('log_id'):
            cardio_type = request.form.get(f'cardio_type_{log_id}')
            custom_cardio_type = request.form.get(f'custom_cardio_{log_id}')
            hours = request.form.get(f'hours_{log_id}', 0, type=int)
            minutes = request.form.get(f'minutes_{log_id}', 0, type=int)
            seconds = request.form.get(f'seconds_{log_id}', 0, type=int)
            distance = request.form.get(f'distance_{log_id}', type=float) or None
            distance_unit = request.form.get(f'distance_unit_{log_id}') or None
            intensity = request.form.get(f'intensity_{log_id}', type=int) or None

            if cardio_type and custom_cardio_type:
                flash("Please select either a standard cardio type OR a custom cardio type, not both")
                return redirect(url_for('edit_cardio_session', session_date=session_date))
            if not cardio_type and not custom_cardio_type:
                flash("Please select a cardio type")
                return redirect(url_for('edit_cardio_session', session_date=session_date))

            cardio_type_id = cardio_type_ids.get(cardio_type)
            custom_cardio_id = custom_cardio_ids.get(custom_cardio_type)
            if not cardio_type_id and not custom_cardio_id:
                flash(f"'{cardio_type or custom_cardio_type}' isn't in your cardio list")
                return redirect(url_for('edit_cardio_session', session_date=session_date))

            duration = get_db_duration(hours, minutes, seconds) or None

            if distance and not distance_unit:
                flash("Please select either miles or kilometers")
                return redirect(url_for('edit_cardio_session', session_date=session_date))
            if distance_unit and not distance:
                flash("Please enter distance")
                return redirect(url_for('edit_cardio_session', session_date=session_date))
            if not distance and not duration:
                flash("Please enter either distance or duration")
                return redirect(url_for('edit_cardio_session', session_date=session_date))

            log_updates.append((cardio_type_id, custom_cardio_id, duration,
                                distance, distance_unit, intensity, log_id))

        try:
            update_cardio_session(current_user.id, session_updates, log_updates)
        except sqlite3.IntegrityError:
            flash("Could not edit cardio session. Please try again.")
            return redirect(url_for('edit_cardio_session', session_date=session_date))

        session.pop('view_cardio_date', None)
        flash("Cardio session updated successfully! View another session?")
        return redirect(url_for('view_cardio_session'))

    cardio_session = get_cardio_session(session_date, current_user.id)
    return render_template('edit_cardio_session.html',
                           cardio_session=cardio_session,
                           cardio_types=cardio_types,
                           custom_cardio=custom_cardio,
                           session_date=session_date)

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