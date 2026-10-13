import resend
from flask import current_app


def send_verification_email(email, token):
    verification_link = f"{current_app.config['BASE_URL']}/verify/{token}"
    
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Verify your account",
        "html": f"""
            <h2>Welcome to My Workout App!</h2>
            <p>Click the link below to verify your account:</p>
            <p><a href="{verification_link}">{verification_link}</a></p>
            <p>This link expires in 24 hours.</p>
        """,
    }
    
    resend.Emails.send(params)

def send_password_reset_email(email, token):
    reset_link = f"{current_app.config['BASE_URL']}/reset_password/{token}"
    
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Reset your password",
        "html": f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't request this, you can ignore this email.</p>
        """,
    }
    
    resend.Emails.send(params)

def send_username_email(email, username):
    params = {
        "from": "Fitness Logger <noreply@fitnesslogger.app>",
        "to": [email],
        "subject": "Forgot Username",
        "html": f"""
            <h2>Forgot Username Request</h2>
            <p>Hello, your username is <strong>{username}</strong>. 
            Click <a href="https://www.fitnesslogger.app/login">this link</a> to be redirected back to the login page.</p>
        """,
    }
    resend.Emails.send(params)
