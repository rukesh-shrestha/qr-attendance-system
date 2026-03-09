"""
Database connection and initialization for the QR Attendance System.
"""

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy database instance (imported in app.py and models.py)
db = SQLAlchemy()


def init_db(app):
    """
    Initialise the database with the Flask app.
    Creates all tables if they do not already exist.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()
