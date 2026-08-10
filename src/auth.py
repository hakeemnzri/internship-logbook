from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from . import db
from .forms import LoginForm, RegistrationForm
from .models import User

# Authentication Blueprint
auth_bp = Blueprint("auth", __name__)


def is_safe_redirect_url(target):
    """Allow login redirects only to local application pages."""
    reference = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    return candidate.scheme in {"http", "https"} and candidate.netloc == reference.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""

    # Prevent logged-in users from accessing the register page
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():
        # Create a new user
        user = User(
            username=form.username.data,
        )

        # Hash the password before saving
        user.set_password(form.password.data)

        # Save user to the database
        db.session.add(user)
        db.session.commit()

        flash(
            "Your account has been created successfully! Please log in.",
            "success",
        )

        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user."""

    # Prevent logged-in users from accessing the login page
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user)

            flash(
                f"Welcome back, {user.username}!",
                "success",
            )

            # Redirect to the page the user originally wanted
            next_page = request.args.get("next")

            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)

            return redirect(url_for("main.dashboard"))

        flash(
            "Invalid username or password.",
            "danger",
        )

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Log the current user out."""

    logout_user()

    flash(
        "You have been logged out successfully.",
        "info",
    )

    return redirect(url_for("auth.login"))
