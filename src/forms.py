from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from .models import User


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired("Enter your username.")])
    password = PasswordField("Password", validators=[DataRequired("Enter your password.")])
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired("Choose a username."), Length(min=4, max=25, message="Username must be 4 to 25 characters.")])
    password = PasswordField("Password", validators=[DataRequired("Choose a password."), Length(min=8, message="Password must be at least 8 characters.")])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired("Type the password again."), EqualTo("password", message="Passwords do not match.")])
    submit = SubmitField("Create account")

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError("That username is taken. Try another one.")

class LogbookEntryForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired("Pick the date this entry is for.")])
    title = StringField("Title", validators=[DataRequired("Give the entry a short title."), Length(max=150)])
    description = HiddenField("Description")
    submit = SubmitField("Save entry")
