import os
import re
import sqlite3
from functools import wraps

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader
from docx import Document


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "talentiq-development-secret-change-this",
)

DATABASE = "talentiq.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            phone TEXT,
            education TEXT,
            skills TEXT,
            experience TEXT,
            projects TEXT,
            resume_filename TEXT,
            resume_text TEXT,
            score INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            description TEXT,
            skills TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Applied',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, job_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM jobs"
    ).fetchone()[0]

    if count == 0:
        jobs = [
            (
                "Java Full Stack Developer",
                "TalentIQ Partner",
                "India",
                "Build scalable Java full stack applications.",
                "Java,Spring Boot,SQL,HTML,CSS,JavaScript,React",
            ),
            (
                "Python Developer",
                "TalentIQ Partner",
                "Remote",
                "Develop Python and Flask based applications.",
                "Python,Flask,Django,SQL,Git,REST API",
            ),
            (
                "Data Analyst",
                "TalentIQ Analytics",
                "India",
                "Analyze business data and create useful insights.",
                "Python,SQL,Excel,Power BI,Data Analysis",
            ),
            (
                "Software Engineer",
                "TalentIQ Technologies",
                "India",
                "Develop and maintain production software.",
                "Java,Python,DSA,Git,SQL,APIs",
            ),
        ]

        conn.executemany("""
            INSERT INTO jobs
            (title, company, location, description, skills)
            VALUES (?, ?, ?, ?, ?)
        """, jobs)

    conn.commit()
    conn.close()


# ---------------- HELPERS ----------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_resume_text(filepath):
    extension = filepath.rsplit(".", 1)[1].lower()

    if extension == "pdf":
        reader = PdfReader(filepath)
        text = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            text.append(page_text)

        return "\n".join(text)

    if extension == "docx":
        document = Document(filepath)
        return "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )

    return ""


def calculate_score(text):
    skills = [
        "python",
        "java",
        "javascript",
        "react",
        "django",
        "flask",
        "spring boot",
        "sql",
        "mysql",
        "postgresql",
        "mongodb",
        "aws",
        "git",
        "html",
        "css",
        "power bi",
        "excel",
        "data analysis",
        "machine learning",
        "dsa",
    ]

    lower_text = text.lower()

    found = sum(
        1 for skill in skills
        if skill in lower_text
    )

    score = min(100, found * 5)

    if re.search(r"\b(b\.?tech|bachelor|degree|engineering)\b", lower_text):
        score += 10

    if re.search(
        r"\b(experience|internship|developer|engineer)\b",
        lower_text,
    ):
        score += 10

    return min(score, 100)


def extract_email(text):
    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )
    return match.group(0) if match else ""


def extract_phone(text):
    match = re.search(
        r"(?:\+91[-\s]?)?[6-9]\d{9}",
        text,
    )
    return match.group(0) if match else ""


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def current_user():
    if "user_id" not in session:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()

    conn.close()

    return user


# ---------------- UI ----------------

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>{{ title }} - TalentIQ</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            color: #172033;
        }

        nav {
            background: #111827;
            padding: 18px 7%;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        nav a {
            color: white;
            text-decoration: none;
            margin-left: 18px;
        }

        .logo {
            font-size: 25px;
            font-weight: bold;
            color: #8b5cf6;
        }

        .container {
            width: 86%;
            max-width: 1150px;
            margin: 40px auto;
        }

        .hero {
            padding: 65px 30px;
            background: linear-gradient(
                135deg,
                #111827,
                #4c1d95
            );
            color: white;
            border-radius: 25px;
            text-align: center;
        }

        .hero h1 {
            font-size: 48px;
            margin-bottom: 15px;
        }

        .hero p {
            font-size: 19px;
        }

        .btn {
            display: inline-block;
            background: #7c3aed;
            color: white;
            padding: 13px 22px;
            border-radius: 10px;
            text-decoration: none;
            border: none;
            cursor: pointer;
            margin-top: 12px;
        }

        .btn:hover {
            background: #6d28d9;
        }

        .card {
            background: white;
            padding: 25px;
            margin: 20px 0;
            border-radius: 18px;
            box-shadow: 0 5px 20px rgba(0,0,0,.06);
        }

        input, textarea, select {
            width: 100%;
            padding: 13px;
            margin: 8px 0 15px;
            border: 1px solid #d1d5db;
            border-radius: 9px;
        }

        .grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }

        .stat {
            background: white;
            padding: 25px;
            border-radius: 18px;
            text-align: center;
        }

        .stat h2 {
            color: #7c3aed;
            font-size: 34px;
        }

        .flash {
            padding: 14px;
            margin-bottom: 15px;
            background: #ede9fe;
            color: #4c1d95;
            border-radius: 10px;
        }

        .skill {
            display: inline-block;
            background: #ede9fe;
            color: #5b21b6;
            padding: 7px 11px;
            border-radius: 20px;
            margin: 4px;
        }

        footer {
            text-align: center;
            padding: 35px;
            color: #6b7280;
        }
    </style>
</head>

<body>

<nav>
    <div class="logo">TalentIQ</div>

    <div>
        <a href="{{ url_for('home') }}">Home</a>

        {% if session.get('user_id') %}
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('jobs') }}">Jobs</a>
            <a href="{{ url_for('profile') }}">Profile</a>
            <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
            <a href="{{ url_for('login') }}">Login</a>
            <a href="{{ url_for('register') }}">Register</a>
        {% endif %}
    </div>
</nav>

<div class="container">

{% with messages = get_flashed_messages() %}
    {% for message in messages %}
        <div class="flash">{{ message }}</div>
    {% endfor %}
{% endwith %}

{{ content|safe }}

</div>

<footer>
    TalentIQ © 2026 — Intelligent Recruitment Platform
</footer>

</body>
</html>
"""


def page(content, title="TalentIQ"):
    return render_template_string(
        BASE_HTML,
        content=content,
        title=title,
    )


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return page("""
        <section class="hero">
            <h1>TalentIQ</h1>
            <p>
                Intelligent Recruitment & Candidate Analytics
            </p>

            <p>
                Upload your resume, discover matching jobs,
                and build your professional profile.
            </p>

            <a class="btn" href="/register">
                Get Started
            </a>

            <a class="btn" href="/jobs">
                Explore Jobs
            </a>
        </section>

        <div class="grid">
            <div class="stat">
                <h2>AI</h2>
                <p>Resume Analysis</p>
            </div>

            <div class="stat">
                <h2>100%</h2>
                <p>Digital Applications</p>
            </div>

            <div class="stat">
                <h2>24/7</h2>
                <p>Job Discovery</p>
            </div>
        </div>
    """, "Home")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if existing:
            conn.close()
            flash("Email already registered.")
            return redirect(url_for("login"))

        password_hash = generate_password_hash(password)

        cursor = conn.execute("""
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
        """, (name, email, password_hash))

        user_id = cursor.lastrowid

        conn.execute("""
            INSERT INTO profiles
            (user_id)
            VALUES (?)
        """, (user_id,))

        conn.commit()
        conn.close()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return page("""
        <div class="card">
            <h1>Create TalentIQ Account</h1>

            <form method="POST">

                <label>Name</label>
                <input
                    type="text"
                    name="name"
                    required
                >

                <label>Email</label>
                <input
                    type="email"
                    name="email"
                    required
                >

                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    required
                >

                <button class="btn">
                    Create Account
                </button>

            </form>
        </div>
    """, "Register")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password,
        ):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return page("""
        <div class="card">
            <h1>Login</h1>

            <form method="POST">

                <label>Email</label>
                <input
                    type="email"
                    name="email"
                    required
                >

                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    required
                >

                <button class="btn">
                    Login
                </button>

            </form>
        </div>
    """, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    conn = get_db()

    if request.method == "POST":

        phone = request.form.get("phone", "")
        education = request.form.get("education", "")
        skills = request.form.get("skills", "")
        experience = request.form.get("experience", "")
        projects = request.form.get("projects", "")

        conn.execute("""
            UPDATE profiles
            SET phone = ?,
                education = ?,
                skills = ?,
                experience = ?,
                projects = ?
            WHERE user_id = ?
        """, (
            phone,
            education,
            skills,
            experience,
            projects,
            session["user_id"],
        ))

        conn.commit()
        flash("Profile updated.")

    profile_data = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()

    conn.close()

    return page(f"""
        <div class="card">

            <h1>My Profile</h1>

            <p>
                <strong>Name:</strong>
                {user["name"]}
            </p>

            <p>
                <strong>Email:</strong>
                {user["email"]}
            </p>

            <form method="POST">

                <label>Phone</label>
                <input
                    name="phone"
                    value="{profile_data["phone"] or ""}"
                >

                <label>Education</label>
                <textarea name="education">{profile_data["education"] or ""}</textarea>

                <label>Skills</label>
                <textarea name="skills">{profile_data["skills"] or ""}</textarea>

                <label>Experience</label>
                <textarea name="experience">{profile_data["experience"] or ""}</textarea>

                <label>Projects</label>
                <textarea name="projects">{profile_data["projects"] or ""}</textarea>

                <button class="btn">
                    Save Profile
                </button>

            </form>
        </div>
    """, "Profile")


@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()

    profile_data = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()

    applications = conn.execute("""
        SELECT applications.*, jobs.title, jobs.company
        FROM applications
        JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.user_id = ?
        ORDER BY applications.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    application_html = ""

    for application in applications:
        application_html += f"""
            <div class="card">
                <h3>{application["title"]}</h3>
                <p>{application["company"]}</p>
                <p>Status: <strong>
                    {application["status"]}
                </strong></p>
            </div>
        """

    score = profile_data["score"] or 0

    return page(f"""
        <section class="hero">
            <h1>Welcome, {user["name"]}</h1>
            <p>Your TalentIQ dashboard</p>
        </section>

        <div class="grid">

            <div class="stat">
                <h2>{score}</h2>
                <p>Resume Score</p>
            </div>

            <div class="stat">
                <h2>{len(applications)}</h2>
                <p>Applications</p>
            </div>

            <div class="stat">
                <h2>AI</h2>
                <p>Talent Matching</p>
            </div>

        </div>

        <div class="card">
            <h2>Resume Upload</h2>

            <form
                method="POST"
                action="/upload-resume"
                enctype="multipart/form-data"
            >
                <input
                    type="file"
                    name="resume"
                    accept=".pdf,.docx"
                    required
                >

                <button class="btn">
                    Analyze Resume
                </button>
            </form>
        </div>

        <h2>Your Applications</h2>

        {application_html if application_html else
        "<div class='card'>No applications yet. Explore jobs.</div>"}

    """, "Dashboard")


@app.route("/upload-resume", methods=["POST"])
@login_required
def upload_resume():

    file = request.files.get("resume")

    if not file or file.filename == "":
        flash("Please select a resume.")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Only PDF and DOCX files are supported.")
        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename,
    )

    file.save(filepath)

    try:
        resume_text = extract_resume_text(filepath)
    except Exception:
        flash("Could not read the resume.")
        return redirect(url_for("dashboard"))

    score = calculate_score(resume_text)
    phone = extract_phone(resume_text)

    conn = get_db()

    conn.execute("""
        UPDATE profiles
        SET phone = ?,
            resume_filename = ?,
            resume_text = ?,
            score = ?
        WHERE user_id = ?
    """, (
        phone,
        filename,
        resume_text,
        score,
        session["user_id"],
    ))

    conn.commit()
    conn.close()

    flash(
        f"Resume analyzed successfully. Score: {score}/100"
    )

    return redirect(url_for("dashboard"))


@app.route("/jobs")
def jobs():

    conn = get_db()

    jobs_data = conn.execute("""
        SELECT * FROM jobs
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    html = "<h1>Available Jobs</h1>"

    for job in jobs_data:

        skills = job["skills"].split(",")

        skill_html = ""

        for skill in skills:
            skill_html += (
                f'<span class="skill">{skill.strip()}</span>'
            )

        html += f"""
            <div class="card">

                <h2>{job["title"]}</h2>

                <p>
                    <strong>{job["company"]}</strong>
                    · {job["location"]}
                </p>

                <p>{job["description"]}</p>

                <div>
                    {skill_html}
                </div>

                <a
                    class="btn"
                    href="/apply/{job["id"]}"
                >
                    Apply Now
                </a>

            </div>
        """

    return page(html, "Jobs")


@app.route("/apply/<int:job_id>")
@login_required
def apply(job_id):

    conn = get_db()

    job = conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()

    if not job:
        conn.close()
        flash("Job not found.")
        return redirect(url_for("jobs"))

    existing = conn.execute("""
        SELECT id
        FROM applications
        WHERE user_id = ?
        AND job_id = ?
    """, (
        session["user_id"],
        job_id,
    )).fetchone()

    if existing:
        conn.close()
        flash("You already applied for this job.")
        return redirect(url_for("jobs"))

    conn.execute("""
        INSERT INTO applications
        (user_id, job_id)
        VALUES (?, ?)
    """, (
        session["user_id"],
        job_id,
    ))

    conn.commit()
    conn.close()

    flash(
        f"Application submitted for {job['title']}."
    )

    return redirect(url_for("dashboard"))


@app.route("/match/<int:job_id>")
@login_required
def match(job_id):

    conn = get_db()

    job = conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()

    profile_data = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (session["user_id"],),
    ).fetchone()

    conn.close()

    if not job:
        return "Job not found", 404

    resume_text = (
        profile_data["resume_text"] or ""
    ).lower()

    job_skills = [
        skill.strip().lower()
        for skill in job["skills"].split(",")
    ]

    matched = [
        skill
        for skill in job_skills
        if skill in resume_text
    ]

    percentage = 0

    if job_skills:
        percentage = int(
            len(matched) / len(job_skills) * 100
        )

    matched_html = ""

    for skill in matched:
        matched_html += (
            f'<span class="skill">{skill}</span>'
        )

    return page(f"""
        <div class="card">

            <h1>AI Job Match</h1>

            <h2>{job["title"]}</h2>

            <h3>Match Score: {percentage}%</h3>

            <p>
                Skills matched:
            </p>

            {matched_html or "No matching skills found."}

            <br>

            <a
                class="btn"
                href="/apply/{job["id"]}"
            >
                Apply
            </a>

        </div>
    """, "Job Match")


@app.route("/health")
def health():
    return {
        "status": "healthy",
        "application": "TalentIQ",
    }


# ---------------- STARTUP ----------------

init_database()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
