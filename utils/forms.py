from flask_wtf import FlaskForm              
from flask_wtf.csrf import CSRFProtect
from wtforms import (StringField, PasswordField, EmailField, IntegerField,
                     DecimalField, DateField, TextAreaField, SelectField,
                     BooleanField, HiddenField, SubmitField)
from wtforms.validators import (DataRequired, InputRequired, Optional, Length,
                                Email, EqualTo, NumberRange, ValidationError)

MIN_PASSWORD_LENGTH = 8

def strip(value):
    return value.strip() if value else value

def lower(value):
    return value.lower() if value else value

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', filters=[strip], validators=[DataRequired()])
    last_name  = StringField('Last Name',  filters=[strip], validators=[DataRequired()])
    username   = StringField('Username',   filters=[strip], 
                            validators=[DataRequired(), Length(min=3, max=30, message='Must be between 3-30 characters')])
    email      = EmailField('Email', filters=[strip, lower], validators=[DataRequired(), Email()])
    password   = PasswordField('Password', 
                            validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH, message=f'Must be at least {MIN_PASSWORD_LENGTH} characters')])
    confirm    = PasswordField('Confirm Password',
                            validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit     = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', filters=[strip], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')


class ForgotLoginForm(FlaskForm):
    email  = EmailField('Email', filters=[strip, lower], validators=[DataRequired(), Email()])
    submit = SubmitField('Send Email')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', 
                                validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH, message=f'Must be at least {MIN_PASSWORD_LENGTH} characters')])
    confirm  = PasswordField('Confirm Password',
                                validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit   = SubmitField('Reset Password')
