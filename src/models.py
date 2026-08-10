from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Load a user stored in the active session."""
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    logbook_entries = db.relationship(
        "LogbookEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LogbookEntry(db.Model):
    __tablename__ = "logbook_entries"
    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_user_log_date"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False
    )
    user = db.relationship("User", back_populates="logbook_entries")
    activities = db.relationship(
        "Activity",
        back_populates="logbook_entry",
        cascade="all, delete-orphan",
        order_by="Activity.display_order",
    )


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    logbook_entry_id = db.Column(
        db.Integer, db.ForeignKey("logbook_entries.id"), nullable=False
    )
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    activity = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    logbook_entry = db.relationship("LogbookEntry", back_populates="activities")
