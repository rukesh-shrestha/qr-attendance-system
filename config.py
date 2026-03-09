"""
Configuration settings for the QR Attendance System.
"""

import os

class Config:
    # Flask secret key (MUST be changed in production via the SECRET_KEY environment variable)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'qr-attendance-secret-key-change-in-production')

    # Database URI: defaults to SQLite for easy setup; set DATABASE_URL env var for MySQL
    # MySQL example: "mysql+pymysql://user:password@localhost/qr_attendance"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///qr_attendance.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # QR token generation
    QR_TOKEN_BYTES = 32  # bytes of randomness for secrets.token_urlsafe()

    # QR code session configuration
    QR_TOKEN_EXPIRY_SECONDS = 120       # QR session expires after 2 minutes
    QR_REFRESH_INTERVAL_SECONDS = 20    # QR code refreshes every 20 seconds

    # Allowed IP ranges for attendance (college WiFi)
    # Students must be on the college network to mark attendance
    ALLOWED_IP_RANGES = [
        '192.168.',   # 192.168.x.x
        '10.',        # 10.x.x.x
        '172.16.',    # 172.16.x.x (RFC1918)
        '172.17.',
        '172.18.',
        '172.19.',
        '172.20.',
        '172.21.',
        '172.22.',
        '172.23.',
        '172.24.',
        '172.25.',
        '172.26.',
        '172.27.',
        '172.28.',
        '172.29.',
        '172.30.',
        '172.31.',
        '127.0.0.1', # Allow localhost for development/testing
        '::1',       # IPv6 localhost
    ]

    # Server base URL (update for production deployment)
    SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', 'http://127.0.0.1:5000')
