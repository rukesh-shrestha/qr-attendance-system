-- =============================================================
-- schema.sql – QR Attendance System
-- MySQL-compatible DDL.
-- For SQLite (default dev setup) the tables are created
-- automatically by SQLAlchemy on first run.
-- =============================================================

CREATE DATABASE IF NOT EXISTS qr_attendance
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE qr_attendance;

-- -------------------------------------------------------------
-- Students
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_id  INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    password    VARCHAR(255) NOT NULL,
    PRIMARY KEY (student_id),
    UNIQUE KEY uq_students_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------------
-- Teachers
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id  INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    password    VARCHAR(255) NOT NULL,
    PRIMARY KEY (teacher_id),
    UNIQUE KEY uq_teachers_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------------
-- Courses
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    course_id   INT          NOT NULL AUTO_INCREMENT,
    course_name VARCHAR(200) NOT NULL,
    teacher_id  INT          NOT NULL,
    PRIMARY KEY (course_id),
    CONSTRAINT fk_courses_teacher
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------------
-- Attendance Sessions
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance_sessions (
    session_id  INT          NOT NULL AUTO_INCREMENT,
    course_id   INT          NOT NULL,
    qr_token    VARCHAR(64)  NOT NULL,
    start_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expire_time DATETIME     NOT NULL,
    PRIMARY KEY (session_id),
    UNIQUE KEY uq_qr_token (qr_token),
    CONSTRAINT fk_sessions_course
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------------
-- Attendance Records
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT         NOT NULL AUTO_INCREMENT,
    student_id    INT         NOT NULL,
    course_id     INT         NOT NULL,
    session_id    INT         NOT NULL,
    timestamp     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address    VARCHAR(45),
    PRIMARY KEY (attendance_id),
    UNIQUE KEY uq_student_session (student_id, session_id),
    CONSTRAINT fk_attendance_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attendance_course
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attendance_session
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(session_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
