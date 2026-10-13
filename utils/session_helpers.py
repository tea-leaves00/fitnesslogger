import secrets

def generate_verification_token():
    return secrets.token_urlsafe(32)

def get_db_duration(hours, minutes, seconds):
    return (hours * 3600) + (minutes * 60) + seconds    

def group_sets(current_sets):
    grouped_sets = {}
    for set_data in current_sets:
        if set_data['is_custom']: exercise_id, custom_exercise_id = None, set_data['exercise_id']
        else: exercise_id, custom_exercise_id = set_data['exercise_id'], None

        key = (exercise_id, custom_exercise_id)
        if key not in grouped_sets:
            grouped_sets[key] = {
                'exercise_id': exercise_id,
                'custom_exercise_id': custom_exercise_id,
                'exercise_notes': set_data['exercise_notes'],
                'sets': []
            }

        if set_data['same_sets']:
            for set_number in range(1, set_data['sets'] + 1):
                grouped_sets[key]['sets'].append((set_number, set_data['reps'], set_data['weight']))
        else:
            grouped_sets[key]['sets'].append((set_data['set_number'], set_data['reps'], set_data['weight']))

    return list(grouped_sets.values())

def group_logs(current_logs):
    return [(log['cardio_type_id'], log['custom_cardio_id'], log['db_duration'],
              log['distance'], log['distance_unit'], log['intensity'])
            for log in current_logs]

def clear_workout_session(session):
    keys = [
        'current_sets', 'session_date', 'session_notes',
        'date_selection', 'same_sets', 'current_set_number',
        'current_exercise'
    ]
    for key in keys:
        session.pop(key, None)

def clear_sets(session):
    keys = [
        'current_sets', 'same_sets', 'current_set_number',
        'current_exercise'
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
