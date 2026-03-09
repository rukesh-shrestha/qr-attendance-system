"""
Main Flask application for the QR Code Based Attendance System.

Routes:
  /                     - Home (redirects based on login state)
  /login                - Login for teachers and students
  /logout               - Logout

Teacher routes:
  /teacher/dashboard    - Teacher dashboard
  /teacher/generate_qr  - Generate attendance QR for a course
  /teacher/qr_display/<session_id> - Display QR code (auto-refreshes)
  /teacher/refresh_qr/<session_id> - API: rotate QR token, return new QR image
  /teacher/attendance/<session_id> - View attendance list for a session
  /teacher/export/<session_id>     - Export attendance to Excel

Student routes:
  /student/dashboard    - Student dashboard
  /attend/<token>       - Mark attendance via scanned QR token
"""

import io
import base64
import secrets
from datetime import datetime, timedelta, timezone

import qrcode
import openpyxl
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file, abort)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import db, init_db
from models import Student, Teacher, Course, AttendanceSession, Attendance


def _utcnow():
    """Return the current UTC time as a naive datetime (UTC, no tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


app = Flask(__name__)
app.config.from_object(Config)

# Initialise DB
init_db(app)


# ---------------------------------------------------------------------------
# Template context processor
# ---------------------------------------------------------------------------

@app.context_processor
def inject_now():
    """Make 'now' available in all templates (used in footer year)."""
    return {'now': _utcnow()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client_ip():
    """Return the real client IP, honouring X-Forwarded-For if present."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr


def is_allowed_ip(ip):
    """
    Check whether *ip* belongs to an allowed range (college WiFi).
    Compares against the prefix list in Config.ALLOWED_IP_RANGES.
    """
    if ip is None:
        return False
    for prefix in app.config['ALLOWED_IP_RANGES']:
        if ip.startswith(prefix):
            return True
    return False


def generate_qr_image(data: str) -> str:
    """
    Generate a QR code for *data* and return it as a base64-encoded PNG string
    suitable for embedding in an <img src="data:image/png;base64,..."> tag.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def login_required_teacher(func):
    """Decorator: redirect to login if the teacher is not authenticated."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'teacher':
            flash('Please log in as a teacher to access this page.', 'warning')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


def login_required_student(func):
    """Decorator: redirect to login if the student is not authenticated."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'student':
            flash('Please log in as a student to access this page.', 'warning')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Redirect to the appropriate dashboard based on the logged-in role."""
    role = session.get('role')
    if role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for both teachers and students."""
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'student')

        # Preserve next_url before clearing the session
        next_url = session.get('next_url')

        if role == 'teacher':
            user = Teacher.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session.clear()
                session['role']       = 'teacher'
                session['user_id']    = user.teacher_id
                session['user_name']  = user.name
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect(url_for('teacher_dashboard'))
        else:
            user = Student.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session.clear()
                session['role']      = 'student'
                session['user_id']   = user.student_id
                session['user_name'] = user.name
                flash(f'Welcome back, {user.name}!', 'success')
                # Redirect back to QR attendance page if student came from one
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('student_dashboard'))

        flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Teacher routes
# ---------------------------------------------------------------------------

@app.route('/teacher/dashboard')
@login_required_teacher
def teacher_dashboard():
    """Show the teacher's courses and active sessions."""
    teacher_id = session['user_id']
    courses = Course.query.filter_by(teacher_id=teacher_id).all()

    # Gather summary stats per course
    course_stats = []
    for course in courses:
        total_students = Student.query.count()
        # Count distinct students who attended any session of this course
        attended = (
            db.session.query(Attendance.student_id)
            .filter_by(course_id=course.course_id)
            .distinct()
            .count()
        )
        # Latest active session for this course
        active_session = (
            AttendanceSession.query
            .filter_by(course_id=course.course_id)
            .filter(AttendanceSession.expire_time > _utcnow())
            .order_by(AttendanceSession.start_time.desc())
            .first()
        )
        course_stats.append({
            'course': course,
            'total_students': total_students,
            'attended': attended,
            'absent': max(0, total_students - attended),
            'percentage': round(attended / total_students * 100, 1) if total_students else 0,
            'active_session': active_session,
        })

    return render_template('teacher_dashboard.html',
                           course_stats=course_stats,
                           teacher_name=session['user_name'])


@app.route('/teacher/generate_qr', methods=['POST'])
@login_required_teacher
def generate_qr():
    """
    Create a new AttendanceSession for the selected course and redirect to the
    QR display page.
    """
    course_id = request.form.get('course_id', type=int)
    if not course_id:
        flash('Please select a course.', 'warning')
        return redirect(url_for('teacher_dashboard'))

    course = Course.query.get(course_id)
    if not course or course.teacher_id != session['user_id']:
        flash('Course not found or access denied.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    # Create the session
    token       = secrets.token_urlsafe(app.config['QR_TOKEN_BYTES'])
    start_time  = _utcnow()
    expire_time = start_time + timedelta(seconds=app.config['QR_TOKEN_EXPIRY_SECONDS'])

    att_session = AttendanceSession(
        course_id   = course_id,
        qr_token    = token,
        start_time  = start_time,
        expire_time = expire_time,
    )
    db.session.add(att_session)
    db.session.commit()

    flash(f'Attendance session created for {course.course_name}.', 'success')
    return redirect(url_for('qr_display', session_id=att_session.session_id))


@app.route('/teacher/qr_display/<int:session_id>')
@login_required_teacher
def qr_display(session_id):
    """Display the QR code for an attendance session with auto-refresh."""
    att_session = AttendanceSession.query.get_or_404(session_id)

    # Only the owning teacher can view this page
    if att_session.course.teacher_id != session['user_id']:
        abort(403)

    attend_url = f"{app.config['SERVER_BASE_URL']}/attend/{att_session.qr_token}"
    qr_b64     = generate_qr_image(attend_url)

    return render_template(
        'qr_display.html',
        att_session    = att_session,
        qr_b64         = qr_b64,
        attend_url     = attend_url,
        refresh_interval = app.config['QR_REFRESH_INTERVAL_SECONDS'],
    )


@app.route('/teacher/refresh_qr/<int:session_id>', methods=['POST'])
@login_required_teacher
def refresh_qr(session_id):
    """
    API endpoint called by the auto-refresh JavaScript.
    Rotates the QR token (keeping the same session) and returns the new QR
    image as base64 JSON.  If the session has expired the response signals
    expiry so the UI can inform the teacher.
    """
    att_session = AttendanceSession.query.get_or_404(session_id)

    if att_session.course.teacher_id != session['user_id']:
        return jsonify({'error': 'forbidden'}), 403

    if att_session.is_expired:
        return jsonify({'expired': True})

    # Rotate token
    att_session.qr_token = secrets.token_urlsafe(app.config['QR_TOKEN_BYTES'])
    db.session.commit()

    attend_url = f"{app.config['SERVER_BASE_URL']}/attend/{att_session.qr_token}"
    qr_b64     = generate_qr_image(attend_url)

    return jsonify({
        'expired': False,
        'qr_b64' : qr_b64,
        'token'  : att_session.qr_token,
    })


@app.route('/teacher/attendance/<int:session_id>')
@login_required_teacher
def view_attendance(session_id):
    """Show the attendance list for a specific session."""
    att_session = AttendanceSession.query.get_or_404(session_id)

    if att_session.course.teacher_id != session['user_id']:
        abort(403)

    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.student_id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.timestamp)
        .all()
    )

    total_students  = Student.query.count()
    present_count   = len(records)
    absent_count    = max(0, total_students - present_count)
    percentage      = round(present_count / total_students * 100, 1) if total_students else 0

    return render_template(
        'attendance_list.html',
        att_session    = att_session,
        records        = records,
        total_students = total_students,
        present_count  = present_count,
        absent_count   = absent_count,
        percentage     = percentage,
    )


@app.route('/teacher/export/<int:session_id>')
@login_required_teacher
def export_attendance(session_id):
    """Export the attendance list for a session as an Excel (.xlsx) file."""
    att_session = AttendanceSession.query.get_or_404(session_id)

    if att_session.course.teacher_id != session['user_id']:
        abort(403)

    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.student_id)
        .filter(Attendance.session_id == session_id)
        .order_by(Attendance.timestamp)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Attendance'

    # Header row
    ws.append([
        'No.', 'Student ID', 'Name', 'Email',
        'Timestamp', 'IP Address',
    ])

    for idx, (att, student) in enumerate(records, start=1):
        ws.append([
            idx,
            student.student_id,
            student.name,
            student.email,
            att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            att.ip_address or '',
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = (
        f"attendance_{att_session.course.course_name.replace(' ', '_')}"
        f"_session_{session_id}.xlsx"
    )
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------

@app.route('/student/dashboard')
@login_required_student
def student_dashboard():
    """Show the student's attendance history."""
    student_id = session['user_id']
    student    = Student.query.get_or_404(student_id)

    # Attendance records with course and session info
    records = (
        db.session.query(Attendance, Course, AttendanceSession)
        .join(Course, Attendance.course_id == Course.course_id)
        .join(AttendanceSession, Attendance.session_id == AttendanceSession.session_id)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.timestamp.desc())
        .all()
    )

    return render_template('student_dashboard.html',
                           student=student,
                           records=records)


@app.route('/attend/<token>')
def attend(token):
    """
    Entry point when a student scans a QR code.
    Validates the token, the session, the network, and marks attendance.
    """
    # Look up the session by the current active token
    att_session = AttendanceSession.query.filter_by(qr_token=token).first()

    # --- Validation: session exists and is not expired ---
    if att_session is None or att_session.is_expired:
        return render_template('attendance_error.html',
                               reason='expired',
                               message='This QR code has expired or is invalid. '
                                       'Please ask your teacher for a new QR code.')

    # --- Validation: student must be logged in ---
    if session.get('role') != 'student':
        # Remember where to return after login
        session['next_url'] = url_for('attend', token=token)
        flash('Please log in to mark your attendance.', 'warning')
        return redirect(url_for('login'))

    student_id = session['user_id']
    client_ip  = get_client_ip()

    # --- Validation: must be on college WiFi ---
    if not is_allowed_ip(client_ip):
        return render_template('attendance_error.html',
                               reason='network',
                               message=f'Attendance can only be marked from the college WiFi network. '
                                       f'Your IP address ({client_ip}) is not on the allowed network.')

    # --- Validation: no duplicate attendance ---
    existing = Attendance.query.filter_by(
        student_id = student_id,
        session_id = att_session.session_id,
    ).first()
    if existing:
        return render_template('attendance_error.html',
                               reason='duplicate',
                               message='You have already marked your attendance for this session.')

    # --- Record attendance ---
    record = Attendance(
        student_id = student_id,
        course_id  = att_session.course_id,
        session_id = att_session.session_id,
        timestamp  = _utcnow(),
        ip_address = client_ip,
    )
    db.session.add(record)
    db.session.commit()

    student = Student.query.get(student_id)
    return render_template('attendance_success.html',
                           student   = student,
                           course    = att_session.course,
                           timestamp = record.timestamp)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('attendance_error.html',
                           reason='forbidden',
                           message='You do not have permission to access this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('attendance_error.html',
                           reason='not_found',
                           message='The page you requested could not be found.'), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
