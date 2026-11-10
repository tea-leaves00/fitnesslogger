from urllib.parse import urlsplit
from werkzeug.security import check_password_hash

MIN_PASSWORD_LENGTH = 8

def validate_password(password):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None

def validate_password_reset(password, confirmation):
    if password != confirmation:
        return "Passwords don't match"
    return validate_password(password)

def validate_registration(first_name, last_name, username, email, password):
    required_fields = {'First name': first_name, 'Last name': last_name,
                       'Username': username, 'Email': email}
    
    for label, value in required_fields.items():
        if not value:
            return f"{label} is required"
    if '@' not in email:
        return "Please enter a valid email address"
    
    return validate_password(password)

def validate_login(user, password):
    if not user or not password or not check_password_hash(user['password_hash'], password):
        return "Incorrect username or password"
    return None

def is_safe_next(next_url):
    parts = urlsplit(next_url)
    return (not parts.scheme and not parts.netloc and next_url.startswith('/')
            and not next_url.startswith('//') and '\\' not in next_url)
