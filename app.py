import os
from datetime import datetime, date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ayushconnect-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "ayushconnect.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Shared software/technology skill taxonomy.
SKILLS = [
    "Python", "Java", "C++", "JavaScript", "TypeScript",
    "HTML/CSS", "React", "Node.js", "Flask", "Django", "REST APIs",
    "SQL", "PostgreSQL", "MongoDB", "Machine Learning", "Data Analysis",
    "Cloud / AWS", "Docker", "Git/GitHub", "Figma", "UI / UX", "Cybersecurity"
]

student_skills = db.Table(
    "student_skills",
    db.Column("student_id", db.Integer, db.ForeignKey("student.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)

job_skills = db.Table(
    "job_skills",
    db.Column("job_id", db.Integer, db.ForeignKey("job.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    college = db.Column(db.String(180), nullable=False)
    course = db.Column(db.String(120), nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False)
    preferred_role = db.Column(db.String(160), nullable=False)
    github = db.Column(db.String(300))
    portfolio = db.Column(db.String(300))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    skills = db.relationship("Skill", secondary=student_skills, lazy="subquery")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(180), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    industry = db.Column(db.String(120), nullable=False)
    contact_person = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    jobs = db.relationship("Job", back_populates="company", cascade="all, delete-orphan")

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    opportunity_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    location = db.Column(db.String(180), nullable=False)
    work_mode = db.Column(db.String(40), nullable=False)
    pay = db.Column(db.String(120), nullable=False)
    duration = db.Column(db.String(120), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    openings = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    eligibility = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company = db.relationship("Company", back_populates="jobs")
    skills = db.relationship("Skill", secondary=job_skills, lazy="subquery")
    applications = db.relationship("Application", back_populates="job", cascade="all, delete-orphan")

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    status = db.Column(db.String(30), default="Pending")
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = db.relationship("Student", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")
    __table_args__ = (db.UniqueConstraint("student_id", "job_id", name="uq_student_job"),)

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    institution = db.Column(db.String(180), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Endorsement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    faculty = db.relationship("Faculty")
    student = db.relationship("Student")
    skill = db.relationship("Skill")

def normalize_email(value):
    """Normalize login/registration emails consistently."""
    return "".join((value or "").strip().casefold().split())

def verify_password(password_hash, password):
    """Safely verify a stored Werkzeug password hash."""
    if not password_hash or password is None:
        return False
    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False

def skill_match(student, job):
    required = {s.name.strip().lower() for s in job.skills}
    owned = {s.name.strip().lower() for s in student.skills}
    if not required:
        return 0, []
    matched = sorted(required & owned)
    return round(len(matched) / len(required) * 100), matched

def login_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != role or not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for(f"{role}_login"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

def init_db():
    db.create_all()
    for name in SKILLS:
        if not Skill.query.filter_by(name=name).first():
            db.session.add(Skill(name=name))
    # Demo-only institutional accounts. Students and companies register themselves.
    if not Faculty.query.filter_by(email="faculty@ayushconnect.local").first():
        db.session.add(Faculty(
            name="Academic Coordinator",
            email="faculty@ayushconnect.local",
            institution="AyushConnect Demo Institution",
            password_hash=generate_password_hash("Faculty@123")
        ))
    db.session.commit()

@app.context_processor
def globals_for_templates():
    return {"today": date.today(), "skills_catalog": SKILLS}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/student-signup", methods=["GET", "POST"])
def student_signup():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        if Student.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("student-signup.html")
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        selected = request.form.getlist("skills")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("student-signup.html")
        if len(selected) < 2:
            flash("Select at least two technical skills.", "warning")
            return render_template("student-signup.html")
        skill_rows = Skill.query.filter(Skill.name.in_(selected)).all()
        student = Student(
            name=request.form["name"].strip(),
            email=email,
            college=request.form["college"].strip(),
            course=request.form["course"].strip(),
            graduation_year=int(request.form["graduation_year"]),
            preferred_role=request.form["preferred_role"].strip(),
            github=request.form.get("github", "").strip(),
            portfolio=request.form.get("portfolio", "").strip(),
            password_hash=generate_password_hash(password),
            skills=skill_rows,
        )
        db.session.add(student)
        db.session.commit()
        session.clear()
        session["role"] = "student"
        session["user_id"] = student.id
        return redirect(url_for("student_dashboard"))
    return render_template("student-signup.html")

@app.route("/student-login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        student = Student.query.filter_by(email=email).first()
        if not student or not verify_password(student.password_hash, password):
            flash("Incorrect email or password.", "danger")
            return render_template("student-login.html")
        session.clear()
        session["role"], session["user_id"] = "student", student.id
        return redirect(url_for("student_dashboard"))
    return render_template("student-login.html")

@app.route("/student-portal")
@login_required("student")
def student_dashboard():
    student = db.session.get(Student, session["user_id"])
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    ranked = []
    for job in jobs:
        score, matched = skill_match(student, job)
        ranked.append({"job": job, "score": score, "matched": matched})
    ranked.sort(key=lambda x: (x["score"], x["job"].created_at), reverse=True)
    applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return render_template("student-portal.html", student=student, ranked_jobs=ranked, applications=applications)

@app.post("/student/apply/<int:job_id>")
@login_required("student")
def apply_job(job_id):
    job = db.session.get(Job, job_id)
    student = db.session.get(Student, session["user_id"])
    if not job:
        flash("Opportunity not found.", "danger")
    elif Application.query.filter_by(student_id=student.id, job_id=job.id).first():
        flash("You have already applied for this opportunity.", "warning")
    elif job.deadline and job.deadline < date.today():
        flash("This application deadline has passed.", "warning")
    else:
        db.session.add(Application(student_id=student.id, job_id=job.id))
        db.session.commit()
        flash("Application submitted successfully.", "success")
    return redirect(url_for("student_dashboard"))

@app.route("/student/profile", methods=["POST"])
@login_required("student")
def update_student_profile():
    student = db.session.get(Student, session["user_id"])
    student.name = request.form["name"].strip()
    student.college = request.form["college"].strip()
    student.course = request.form["course"].strip()
    student.graduation_year = int(request.form["graduation_year"])
    student.preferred_role = request.form["preferred_role"].strip()
    student.github = request.form.get("github", "").strip()
    student.portfolio = request.form.get("portfolio", "").strip()
    student.skills = Skill.query.filter(Skill.name.in_(request.form.getlist("skills"))).all()
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("student_dashboard"))

@app.route("/company-signup", methods=["GET", "POST"])
def company_signup():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        if Company.query.filter_by(email=email).first():
            flash("A company account with this email already exists.", "danger")
            return render_template("company-signup.html")
        if request.form["password"] != request.form["confirm_password"]:
            flash("Passwords do not match.", "danger")
            return render_template("company-signup.html")
        company = Company(
            company_name=request.form["company_name"].strip(),
            email=email,
            industry=request.form["industry"].strip(),
            contact_person=request.form["contact_person"].strip(),
            description=request.form.get("description", "").strip(),
            password_hash=generate_password_hash(request.form["password"]),
        )
        db.session.add(company)
        db.session.commit()
        session.clear()
        session["role"], session["user_id"] = "company", company.id
        return redirect(url_for("industry_portal"))
    return render_template("company-signup.html")

@app.route("/industry-login", methods=["GET", "POST"])
def company_login():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        company = Company.query.filter_by(email=email).first()
        if not company or not verify_password(company.password_hash, password):
            flash("Incorrect corporate email or password.", "danger")
            return render_template("industry-login.html")
        session.clear()
        session["role"], session["user_id"] = "company", company.id
        return redirect(url_for("industry_portal"))
    return render_template("industry-login.html")

@app.route("/industry-portal", methods=["GET", "POST"])
@login_required("company")
def industry_portal():
    company = db.session.get(Company, session["user_id"])
    if request.method == "POST":
        try:
            deadline_raw = request.form.get("deadline", "")
            deadline = datetime.strptime(deadline_raw, "%Y-%m-%d").date() if deadline_raw else None
            openings = max(1, int(request.form.get("openings", "1")))
        except ValueError:
            flash("Please check the deadline and openings.", "danger")
            return redirect(url_for("industry_portal"))
        selected = request.form.getlist("skills")
        job = Job(
            company_id=company.id,
            opportunity_type=request.form["opportunity_type"],
            title=request.form["title"].strip(),
            location=request.form["location"].strip(),
            work_mode=request.form["work_mode"],
            pay=request.form["pay"].strip(),
            duration=request.form["duration"].strip(),
            deadline=deadline,
            openings=openings,
            description=request.form.get("description", "").strip(),
            eligibility=request.form.get("eligibility", "").strip(),
            skills=Skill.query.filter(Skill.name.in_(selected)).all(),
        )
        db.session.add(job)
        db.session.commit()
        flash("Opportunity published successfully.", "success")
        return redirect(url_for("industry_portal"))
    jobs = Job.query.filter_by(company_id=company.id).order_by(Job.created_at.desc()).all()
    applications = (Application.query.join(Job).filter(Job.company_id == company.id)
                    .order_by(Application.applied_at.desc()).all())
    app_rows = []
    for application in applications:
        score, matched = skill_match(application.student, application.job)
        app_rows.append({"application": application, "score": score, "matched": matched})
    return render_template("industry-portal.html", company=company, jobs=jobs, app_rows=app_rows, show_login=False)

@app.post("/industry/application/<int:application_id>/<status>")
@login_required("company")
def update_application(application_id, status):
    application = db.session.get(Application, application_id)
    if not application or application.job.company_id != session["user_id"]:
        flash("Application not found.", "danger")
        return redirect(url_for("industry_portal"))
    if status not in {"Accepted", "Rejected", "Pending"}:
        flash("Invalid application status.", "danger")
        return redirect(url_for("industry_portal"))
    application.status = status
    application.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f"Application marked {status.lower()}.", "success")
    return redirect(url_for("industry_portal"))

@app.route("/college-login", methods=["GET", "POST"])
def faculty_login():
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        faculty = Faculty.query.filter_by(email=email).first()
        if not faculty or not verify_password(faculty.password_hash, password):
            flash("Incorrect faculty email or password.", "danger")
            return render_template("faculty-login.html")
        session.clear()
        session["role"], session["user_id"] = "faculty", faculty.id
        return redirect(url_for("college_portal"))
    return render_template("faculty-login.html")

@app.route("/college-portal", methods=["GET", "POST"])
@login_required("faculty")
def college_portal():
    faculty = db.session.get(Faculty, session["user_id"])
    if request.method == "POST":
        student_id = int(request.form["student_id"])
        skill_id = int(request.form["skill_id"])
        rating = min(5, max(1, int(request.form["rating"])))
        student = db.session.get(Student, student_id)
        skill = db.session.get(Skill, skill_id)
        if student and skill:
            endorsement = Endorsement.query.filter_by(faculty_id=faculty.id, student_id=student_id, skill_id=skill_id).first()
            if endorsement:
                endorsement.rating = rating
                endorsement.note = request.form.get("note", "").strip()
            else:
                db.session.add(Endorsement(faculty_id=faculty.id, student_id=student_id, skill_id=skill_id,
                                           rating=rating, note=request.form.get("note", "").strip()))
            db.session.commit()
            flash("Skill endorsement saved.", "success")
        return redirect(url_for("college_portal"))
    students = Student.query.order_by(Student.created_at.desc()).all()
    applications = Application.query.order_by(Application.applied_at.desc()).all()
    endorsements = Endorsement.query.filter_by(faculty_id=faculty.id).all()
    skills = Skill.query.order_by(Skill.name.asc()).all()
    return render_template("college-portal.html", faculty=faculty, students=students,
                           applications=applications, endorsements=endorsements,
                           skills=skills, show_login=False)

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        expected_email = os.environ.get("ADMIN_EMAIL", "admin@ayushconnect.local")
        expected_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
        if email != expected_email or password != expected_password:
            flash("Incorrect administrator email or password.", "danger")
            return render_template("admin-login.html")
        session.clear()
        session["role"], session["user_id"] = "admin", email
        return redirect(url_for("admin_portal"))
    return render_template("admin-login.html")

@app.route("/admin-portal")
@login_required("admin")
def admin_portal():
    students = Student.query.count()
    companies = Company.query.count()
    jobs = Job.query.count()
    applications = Application.query.count()
    accepted = Application.query.filter_by(status="Accepted").count()
    rejected = Application.query.filter_by(status="Rejected").count()
    pending = Application.query.filter_by(status="Pending").count()
    all_apps = Application.query.order_by(Application.applied_at.desc()).limit(20).all()
    students_rows = Student.query.order_by(Student.created_at.desc()).all()
    companies_rows = Company.query.order_by(Company.created_at.desc()).all()
    jobs_rows = Job.query.order_by(Job.created_at.desc()).all()
    scores = [skill_match(a.student, a.job)[0] for a in all_apps]
    avg_match = round(sum(scores) / len(scores), 1) if scores else 0
    match_scores = {a.id: skill_match(a.student, a.job)[0] for a in all_apps}
    return render_template("admin-portal.html", stats={
        "students": students, "companies": companies, "jobs": jobs, "applications": applications,
        "accepted": accepted, "rejected": rejected, "pending": pending, "avg_match": avg_match
    }, all_apps=all_apps, match_scores=match_scores,
       students_rows=students_rows, companies_rows=companies_rows, jobs_rows=jobs_rows,
       show_login=False)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
