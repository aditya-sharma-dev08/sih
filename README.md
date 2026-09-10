# AyushConnect rebuilt full-stack prototype

## Stack
- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja templates
- Bootstrap 5

## Run on Windows

1. Open this folder in VS Code.
2. Create a virtual environment:
   python -m venv venv
3. Activate it:
   venv\Scripts\activate
4. Install packages:
   pip install -r requirements.txt
5. Start:
   python app.py
6. Open:
   http://127.0.0.1:5000

The SQLite database `ayushconnect.db` is created automatically on first run.

## Demo institutional accounts

Faculty:
Email: faculty@ayushconnect.local
Password: Faculty@123

Admin:
Email: admin@ayushconnect.local
Password: Admin@123

For a real deployment, set `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` as environment variables.

## Main workflow

Student:
Sign up -> profile saved in SQLite -> automatic login -> dashboard -> skill-based job ranking -> apply -> track status.

Company:
Sign up -> account saved -> automatic login -> create jobs/internships -> select standardized required skills -> listings appear in student dashboard -> review applicants -> see match percentage -> accept/reject.

Faculty:
Login -> see students and applications -> record skill endorsements and ratings.

Admin:
Login -> see students, companies, opportunities, applications, status distribution and average skill-match metrics.

## Security note

Passwords are stored as Werkzeug password hashes, not plain-text passwords.
