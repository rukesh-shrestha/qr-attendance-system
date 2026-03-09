"""
SQLAlchemy database models for the QR Attendance System.
"""

from datetime import datetime, timezone
from database import db


def _utcnow():
    """Return the current UTC time as a naive datetime (stored without timezone info)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Student(db.Model):
    """Represents a student who can mark attendance."""
    __tablename__ = 'students'

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)  # bcrypt/werkzeug hash

    # Relationships
    attendances = db.relationship('Attendance', backref='student', lazy=True)

    def __repr__(self):
        return f'<Student {self.student_id}: {self.name}>'


class Teacher(db.Model):
    """Represents a teacher who manages courses and generates QR codes."""
    __tablename__ = 'teachers'

    teacher_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)

    # Relationships
    courses = db.relationship('Course', backref='teacher', lazy=True)

    def __repr__(self):
        return f'<Teacher {self.teacher_id}: {self.name}>'


class Course(db.Model):
    """Represents a course taught by a teacher."""
    __tablename__ = 'courses'

    course_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_name = db.Column(db.String(200), nullable=False)
    teacher_id  = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'), nullable=False)

    # Relationships
    sessions    = db.relationship('AttendanceSession', backref='course', lazy=True)
    attendances = db.relationship('Attendance', backref='course', lazy=True)

    def __repr__(self):
        return f'<Course {self.course_id}: {self.course_name}>'


class AttendanceSession(db.Model):
    """
    Represents one attendance-taking session for a course.
    A session contains one or more rotating QR tokens; only the active token
    (within expiry) is accepted but all tokens generated during the session
    window remain valid until session expiry.
    """
    __tablename__ = 'attendance_sessions'

    session_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id   = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    qr_token    = db.Column(db.String(64), unique=True, nullable=False)  # current active token
    start_time  = db.Column(db.DateTime, default=_utcnow, nullable=False)
    expire_time = db.Column(db.DateTime, nullable=False)

    # Relationships
    attendances = db.relationship('Attendance', backref='session', lazy=True)

    @property
    def is_expired(self):
        """Return True if the session has passed its expiry time."""
        return _utcnow() > self.expire_time

    def __repr__(self):
        return f'<AttendanceSession {self.session_id} course={self.course_id}>'


class Attendance(db.Model):
    """Records that a student attended a particular session of a course."""
    __tablename__ = 'attendance'

    attendance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    course_id     = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    session_id    = db.Column(db.Integer, db.ForeignKey('attendance_sessions.session_id'), nullable=False)
    timestamp     = db.Column(db.DateTime, default=_utcnow, nullable=False)
    ip_address    = db.Column(db.String(45), nullable=True)  # supports IPv6

    # Prevent duplicate attendance for the same student in the same session
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', name='uq_student_session'),
    )

    def __repr__(self):
        return f'<Attendance student={self.student_id} session={self.session_id}>'
