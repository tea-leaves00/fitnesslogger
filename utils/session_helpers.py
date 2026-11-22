import secrets
import hashlib
from urllib.parse import urlsplit

def generate_token():
    return secrets.token_urlsafe(32)

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def get_db_duration(hours, minutes, seconds):
    return (hours * 3600) + (minutes * 60) + seconds    

def get_set_number(current_sets, exercise_id, is_custom):
    if current_sets:
        last_set = current_sets[-1]
        if (last_set['exercise_id'], last_set['is_custom']) == (exercise_id, is_custom):
            return last_set['set_number'] + (last_set['sets'] if last_set['same_sets'] else 1)
    return 1

def group_sets(sets):
    grouped_sets = []
    for set_data in sets:
        if set_data['is_custom']: exercise_id, custom_exercise_id = None, set_data['exercise_id']
        else: exercise_id, custom_exercise_id = set_data['exercise_id'], None

        if not grouped_sets or (grouped_sets[-1]['exercise_id'], grouped_sets[-1]['custom_exercise_id']) != (exercise_id, custom_exercise_id):
            grouped_sets.append({
                'exercise_id': exercise_id,
                'custom_exercise_id': custom_exercise_id,
                'exercise_notes': set_data['exercise_notes'],
                'sets': []
            })

        set_count = set_data['sets'] if set_data['same_sets'] else 1
        for _ in range(set_count):
            set_number = len(grouped_sets[-1]['sets']) + 1
            grouped_sets[-1]['sets'].append((set_number, set_data['reps'], set_data['weight']))

    return grouped_sets

def group_logs(logs):
    grouped_logs = []
    for log in logs:
        if log['is_custom']: cardio_type_id, custom_cardio_id = None, log['cardio_type_id']
        else: cardio_type_id, custom_cardio_id = log['cardio_type_id'], None

        grouped_logs.append((cardio_type_id, custom_cardio_id, log['db_duration'],
                             log['distance'], log['distance_unit'], log['intensity']))
    return grouped_logs

def clear_workout_session(session):
    keys = [
        'current_sets', 'session_date', 'session_notes',
        'date_selection'
    ]
    for key in keys:
        session.pop(key, None)

def clear_sets(session):
    keys = [
        'current_sets'
    ]
    for key in keys:
        session.pop(key, None)

def clear_cardio_session(session):
    keys = [
        'current_logs', 'session_date', 
        'session_notes', 'date_selection',
    ]
    for key in keys:
        session.pop(key, None)

def clear_logs(session):
    keys = [
        'current_logs'
    ]
    for key in keys:
        session.pop(key, None)

def is_safe_next(next_url):
    parts = urlsplit(next_url)
    return (not parts.scheme and not parts.netloc and next_url.startswith('/')
            and not next_url.startswith('//') and '\\' not in next_url)
