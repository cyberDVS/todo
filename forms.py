from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, HiddenField, PasswordField
from wtforms.validators import DataRequired, Email, Length


class Task(FlaskForm):
    id = HiddenField('id')
    text = TextAreaField(validators=[DataRequired()], render_kw={'rows': 5, 'placeholder': 'Text'})
    end_date = StringField(validators=[DataRequired()], render_kw={'placeholder': 'End Date'})
    submit = SubmitField(render_kw={'class': 'form-button'})


class Register(FlaskForm):
    name = StringField(validators=[DataRequired()], render_kw={'placeholder': 'Name'})
    email = StringField(validators=[DataRequired(), Email(message='Incorrect email')], render_kw={'placeholder': 'Email'})
    password = PasswordField(validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    submit = SubmitField('Register', render_kw={'class': 'form-button'})


class Login(FlaskForm):
    email = StringField(validators=[DataRequired(), Email(message='Incorrect email')], render_kw={'placeholder': 'Email'})
    password = PasswordField(validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login', render_kw={'class': 'form-button'})


class Forgot(FlaskForm):
    password = PasswordField(validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    confirm_password = PasswordField(validators=[DataRequired()], render_kw={'placeholder': 'Confirm Password'})
    submit = SubmitField('Restore', render_kw={'class': 'form-button'})

