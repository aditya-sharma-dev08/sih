"""Repair a student account password without deleting any AyushConnect data.

Run:
    python reset_student_password.py
"""

from getpass import getpass

from app import app, db, Student, normalize_email, generate_password_hash


def main():
    with app.app_context():
        email = normalize_email(input("Student email: "))
        student = Student.query.filter_by(email=email).first()

        if not student:
            print("No student account was found for that email.")
            return

        password = getpass("New password (minimum 6 characters): ")
        confirm = getpass("Confirm new password: ")

        if len(password) < 6:
            print("Password must contain at least 6 characters.")
            return
        if password != confirm:
            print("Passwords do not match.")
            return

        student.password_hash = generate_password_hash(password)
        db.session.commit()
        print(f"Password reset successfully for {student.email}.")
        print("Return to Student Login and use the new password.")


if __name__ == "__main__":
    main()
