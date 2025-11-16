"""
Database models for the chore tracking application.

This module defines three SQLAlchemy models:

* ``User`` – represents people who can log in to the system. Each user has a
  unique username and a password hash for authentication.
* ``Chore`` – represents a chore that needs to be performed. A chore has a
  descriptive name and an associated numeric value to reflect its importance
  or reward.
* ``UserChoreStatus`` – tracks the daily status of each chore for each user.
  It records which chores have been prepared, verified or completed on a
  particular date.

The models are linked via foreign keys to ensure referential integrity.
"""

from flask_sqlalchemy import SQLAlchemy

# create a SQLAlchemy object without an app – we'll initialize it in app.py
db = SQLAlchemy()


class User(db.Model):
    """Represents a user of the chore tracking app."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship to statuses; when a user is deleted, cascade delete their statuses
    chores = db.relationship(
        "UserChoreStatus", backref="user", cascade="all, delete-orphan", lazy=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"


class Chore(db.Model):
    """Represents a chore that can be assigned to users."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Float, nullable=False)

    statuses = db.relationship(
        "UserChoreStatus", backref="chore", cascade="all, delete-orphan", lazy=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Chore {self.name} (value={self.value})>"


class UserChoreStatus(db.Model):
    """Tracks the daily progress of a user's chores.

    Each instance of this model reflects the state of a particular chore for a
    specific user on a given date. Flags indicate whether the chore has been
    prepared, verified and/or completed.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey("chore.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    prepared = db.Column(db.Boolean, default=False)
    verified = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UserChoreStatus user={self.user_id} chore={self.chore_id} "
            f"date={self.date} prepared={self.prepared} verified={self.verified} "
            f"completed={self.completed}>"
        )
