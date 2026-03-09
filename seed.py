"""
Seed script to populate the database with sample teachers, students, and courses.
Run once after the database tables have been created:

    python seed.py
"""

from werkzeug.security import generate_password_hash
from app import app
from database import db
from models import Student, Teacher, Course


def seed():
    with app.app_context():
        db.create_all()

        # ----------------------------------------------------------------
        # Teachers
        # ----------------------------------------------------------------
        teachers_data = [
            {'name': 'Dr. Alice Johnson',   'email': 'alice@college.edu',   'password': 'teacher123'},
            {'name': 'Prof. Bob Williams',  'email': 'bob@college.edu',     'password': 'teacher456'},
        ]
        teachers = {}
        for td in teachers_data:
            existing = Teacher.query.filter_by(email=td['email']).first()
            if not existing:
                t = Teacher(
                    name     = td['name'],
                    email    = td['email'],
                    password = generate_password_hash(td['password']),
                )
                db.session.add(t)
                db.session.flush()      # assign teacher_id before using it
                teachers[td['email']] = t
                print(f'  Created teacher: {td["email"]} / {td["password"]}')
            else:
                teachers[td['email']] = existing
                print(f'  Teacher already exists: {td["email"]}')

        db.session.commit()

        # ----------------------------------------------------------------
        # Courses
        # ----------------------------------------------------------------
        courses_data = [
            {'name': 'Introduction to Computer Science', 'teacher_email': 'alice@college.edu'},
            {'name': 'Data Structures and Algorithms',   'teacher_email': 'alice@college.edu'},
            {'name': 'Database Management Systems',      'teacher_email': 'bob@college.edu'},
            {'name': 'Operating Systems',                'teacher_email': 'bob@college.edu'},
        ]
        for cd in courses_data:
            teacher = Teacher.query.filter_by(email=cd['teacher_email']).first()
            if teacher:
                existing_course = Course.query.filter_by(
                    course_name=cd['name'], teacher_id=teacher.teacher_id
                ).first()
                if not existing_course:
                    c = Course(course_name=cd['name'], teacher_id=teacher.teacher_id)
                    db.session.add(c)
                    print(f'  Created course: {cd["name"]}')
                else:
                    print(f'  Course already exists: {cd["name"]}')

        db.session.commit()

        # ----------------------------------------------------------------
        # Students (100 sample students)
        # ----------------------------------------------------------------
        for i in range(1, 101):
            email = f'student{i:03d}@college.edu'
            existing = Student.query.filter_by(email=email).first()
            if not existing:
                s = Student(
                    name     = f'Student {i:03d}',
                    email    = email,
                    password = generate_password_hash('student123'),
                )
                db.session.add(s)

        db.session.commit()
        print('  Created 100 sample students (student001@college.edu – student100@college.edu)')

        # ----------------------------------------------------------------
        print('\nSeeding complete!')
        print('\nDefault credentials:')
        print('  Teachers:')
        for td in teachers_data:
            print(f'    Email: {td["email"]}  Password: {td["password"]}')
        print('  Students:')
        print('    Email: student001@college.edu  Password: student123')
        print('    (student001 through student100 all use password: student123)')


if __name__ == '__main__':
    seed()
