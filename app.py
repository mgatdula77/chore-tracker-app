"""
Main Flask application for the chore tracking app.

This module creates a Flask application, configures the database, and defines
routes for user authentication, chore management and daily status tracking. The
application uses session-based authentication with a secret key. It stores
data in a SQLite database located in the project directory.

Key routes:

* ``/register`` – create a new user account.
* ``/login`` – authenticate an existing user.
* ``/logout`` – clear the user's session.
* ``/`` or ``/dashboard`` – show today's chores for the current user and allow
  updating their status.
* ``/add_chore`` – add new chores or list existing ones with delete links.
* ``/delete_chore/<int:chore_id>`` – remove a chore from the system.

To run the app locally, install the requirements (see requirements.txt) and
execute ``python app.py``. When deploying to Render, use a production WSGI
server such as Gunicorn (the provided render.yaml sets this up).
"""

from __future__ import annotations

import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Chore, UserChoreStatus


def create_app() -> Flask:
    """Factory function for creating the Flask application.

    Returns
    -------
    Flask
        A configured Flask application.
    """
    app = Flask(__name__)
    # Use SQLite for ease of deployment; Render persistent disk can be attached
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # IMPORTANT: change this secret in a real deployment
    app.config["SECRET_KEY"] = "change-me-secret-key"

    db.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    def login_required(view_func):  # type: ignore[misc]
        """Decorator to require an authenticated user for a route."""
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """Display the registration form and handle account creation."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Both username and password are required.")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("Username is already taken.")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)
            new_user = User(username=username, password_hash=password_hash)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Show the login form and authenticate the user."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                session["user_id"] = user.id
                flash("Logged in successfully.")
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.")
            return redirect(url_for("login"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        """Log out the current user by clearing the session."""
        session.clear()
        flash("You have been logged out.")
        return redirect(url_for("login"))

    @app.route("/", methods=["GET", "POST"])
    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        """Display and update the current user's chores for today."""
        user = User.query.get(session["user_id"])
        today = datetime.date.today()

        # On POST, update statuses based on submitted form
        if request.method == "POST":
            # For each chore, update or create the status entry
            for chore in Chore.query.all():
                # Determine which checkboxes were ticked
                prepared = bool(request.form.get(f"prepared_{chore.id}"))
                verified = bool(request.form.get(f"verified_{chore.id}"))
                completed = bool(request.form.get(f"completed_{chore.id}"))

                status = (
                    UserChoreStatus.query.filter_by(
                        user_id=user.id, chore_id=chore.id, date=today
                    ).first()
                )
                if status is None:
                    status = UserChoreStatus(
                        user_id=user.id,
                        chore_id=chore.id,
                        date=today,
                    )
                    db.session.add(status)
                status.prepared = prepared
                status.verified = verified
                status.completed = completed
            db.session.commit()
            flash("Chore statuses updated.")
            return redirect(url_for("dashboard"))

        # On GET, build status dict for template
        chores = Chore.query.all()
        statuses = {}
        for chore in chores:
            status = (
                UserChoreStatus.query.filter_by(
                    user_id=user.id, chore_id=chore.id, date=today
                ).first()
            )
            statuses[chore.id] = status or UserChoreStatus(
                user_id=user.id, chore_id=chore.id, date=today
            )
        return render_template(
            "dashboard.html",
            user=user,
            chores=chores,
            statuses=statuses,
            today=today,
        )

    @app.route("/add_chore", methods=["GET", "POST"])
    @login_required
    def add_chore():
        """Allow the user to add new chores and view/delete existing ones."""
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            value = request.form.get("value", "").strip()
            try:
                value_num = float(value)
            except ValueError:
                flash("Please enter a valid value for the chore.")
                return redirect(url_for("add_chore"))
            if not name:
                flash("Chore name is required.")
                return redirect(url_for("add_chore"))
            new_chore = Chore(name=name, value=value_num)
            db.session.add(new_chore)
            db.session.commit()
            flash("Chore added successfully.")
            return redirect(url_for("add_chore"))
        chores = Chore.query.all()
        return render_template("add_chore.html", chores=chores)

    @app.route("/delete_chore/<int:chore_id>")
    @login_required
    def delete_chore(chore_id: int):
        """Delete a chore and all associated status records."""
        chore = Chore.query.get_or_404(chore_id)
        db.session.delete(chore)
        db.session.commit()
        flash(f"Deleted chore '{chore.name}'.")
        return redirect(url_for("add_chore"))

    return app


# 👇 NEW: create the app at module import time so gunicorn can find `app`
app = create_app()


if __name__ == "__main__":  # pragma: no cover
    # When running locally with `python app.py`, use Flask's dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
