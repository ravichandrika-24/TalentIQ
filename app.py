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
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader
from docx import Document


# =========================================================
# TALENTIQ
# Intelligent Recruitment & Candidate Analytics
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "talentiq-change-this-secret"
)

DATABASE = "talentiq.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


ALLOWED_EXTENSIONS = {
    "pdf",
    "docx"
}


SKILLS = [
    "python",
    "java",
    "javascript",
    "html",
    "css",
    "react",
    "angular",
    "spring",
    "spring boot",
    "django",
    "flask",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "git",
    "github",
    "docker",
    "aws",
    "azure",
    "machine learning",
    "data analytics",
    "data science",
    "excel",
    "power bi",
    "c",
    "c++",
    "dsa"
]


# =========================================================
# DATABASE
# =========================================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'candidate'
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            education TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            resume TEXT DEFAULT '',
            resume_score INTEGER DEFAULT 0
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            skills TEXT NOT NULL,
            description TEXT DEFAULT ''
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Applied',
            UNIQUE(user_id, job_id)
        )
    """)

    # Add demo jobs only if database is empty
    job_count = connection.execute(
        "SELECT COUNT(*) FROM jobs"
    ).fetchone()[0]

    if job_count == 0:

        jobs = [

            (
                "Java Full Stack Developer",
                "TalentIQ Technologies",
                "java,spring boot,html,css,javascript,sql",
                "Build modern Java full-stack applications."
            ),

            (
                "Python Developer",
                "TalentIQ Technologies",
                "python,django,flask,sql,git",
                "Develop scalable Python applications."
            ),

            (
                "Data Analyst",
                "TalentIQ Analytics",
                "python,sql,excel,power bi,data analytics",
                "Analyze data and build business dashboards."
            ),

            (
                "Software Engineer",
                "TalentIQ Labs",
                "java,python,git,sql,docker",
                "Develop and maintain software products."
            )

        ]

        connection.executemany("""
            INSERT INTO jobs
            (title, company, skills, description)
            VALUES (?, ?, ?, ?)
        """, jobs)

    connection.commit()

    connection.close()


# =========================================================
# AUTHENTICATION
# =========================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# FILE FUNCTIONS
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower() in ALLOWED_EXTENSIONS
    )


def extract_resume_text(filepath):

    extension = filepath.rsplit(
        ".",
        1
    )[1].lower()

    # PDF
    if extension == "pdf":

        reader = PdfReader(filepath)

        text = ""

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"

        return text

    # DOCX
    if extension == "docx":

        document = Document(filepath)

        text = []

        for paragraph in document.paragraphs:

            if paragraph.text.strip():

                text.append(
                    paragraph.text
                )

        return "\n".join(text)

    return ""


# =========================================================
# RESUME ANALYSIS
# =========================================================

def analyze_resume(text):

    lower_text = text.lower()

    detected_skills = []

    for skill in SKILLS:

        if skill in lower_text:

            detected_skills.append(skill)

    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    phone_match = re.search(
        r"(?:\+91[\s-]?)?[6-9]\d{9}",
        text
    )

    education_found = any(
        word in lower_text
        for word in [
            "education",
            "b.tech",
            "btech",
            "bachelor",
            "degree",
            "university",
            "college"
        ]
    )

    experience_found = any(
        word in lower_text
        for word in [
            "experience",
            "internship",
            "intern",
            "employment",
            "worked"
        ]
    )

    project_found = any(
        word in lower_text
        for word in [
            "project",
            "projects"
        ]
    )

    skills_section_found = (
        "skills" in lower_text
        or "technical skills" in lower_text
    )

    score = 0

    if email_match:
        score += 10

    if phone_match:
        score += 10

    if education_found:
        score += 15

    if experience_found:
        score += 15

    if project_found:
        score += 15

    if skills_section_found:
        score += 10

    score += min(
        len(detected_skills) * 3,
        25
    )

    score = min(
        score,
        100
    )

    return {
        "score": score,
        "skills": detected_skills,
        "email": (
            email_match.group(0)
            if email_match
            else "Not detected"
        ),
        "phone": (
            phone_match.group(0)
            if phone_match
            else "Not detected"
        ),
        "education": education_found,
        "experience": experience_found,
        "projects": project_found,
        "skills_section": skills_section_found
    }


# =========================================================
# JOB MATCHING
# =========================================================

def match_score(
    candidate_skills,
    required_skills
):

    candidate = {
        skill.strip().lower()
        for skill in candidate_skills.split(",")
        if skill.strip()
    }

    required = {
        skill.strip().lower()
        for skill in required_skills.split(",")
        if skill.strip()
    }

    if not required:

        return 0

    matched = candidate.intersection(
        required
    )

    return int(
        len(matched)
        / len(required)
        * 100
    )


# =========================================================
# COMMON HTML
# =========================================================

BASE_HTML = """

<!DOCTYPE html>

<html>

<head>

<title>TalentIQ</title>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    font-family:
    Arial,
    Helvetica,
    sans-serif;

    background:
    linear-gradient(
        135deg,
        #f5f7ff,
        #eef2ff
    );

    color: #111827;
}

nav {

    background:
    linear-gradient(
        90deg,
        #111827,
        #312e81
    );

    padding: 18px 7%;

    display: flex;

    align-items: center;

    gap: 25px;

    flex-wrap: wrap;
}

nav a {

    color: white;

    text-decoration: none;

    font-weight: bold;
}

.logo {

    font-size: 25px;

    margin-right: auto;
}

.container {

    max-width: 1150px;

    margin: auto;

    padding: 35px 20px;
}

.card {

    background: white;

    border-radius: 18px;

    padding: 28px;

    margin-bottom: 22px;

    box-shadow:
    0 10px 35px
    rgba(0,0,0,.08);
}

.hero {

    text-align: center;

    padding:
    80px 25px;
}

.hero h1 {

    font-size: 55px;

    margin-bottom: 10px;

    color: #4f46e5;
}

.hero h2 {

    font-size: 28px;
}

input,
textarea,
select {

    width: 100%;

    padding: 13px;

    margin:
    8px 0 18px;

    border:
    1px solid #d1d5db;

    border-radius: 9px;

    font-size: 15px;
}

textarea {

    min-height: 120px;

    resize: vertical;
}

button {

    background:
    linear-gradient(
        135deg,
        #4f46e5,
        #7c3aed
    );

    color: white;

    border: none;

    padding:
    13px 22px;

    border-radius: 9px;

    cursor: pointer;

    font-weight: bold;

    font-size: 15px;
}

button:hover {

    opacity: .9;
}

.btn {

    display: inline-block;

    background: #4f46e5;

    color: white;

    padding:
    12px 20px;

    border-radius: 8px;

    text-decoration: none;

    font-weight: bold;
}

.score {

    font-size: 52px;

    font-weight: bold;

    color: #4f46e5;
}

.match {

    font-size: 28px;

    font-weight: bold;

    color: #4f46e5;
}

.skill {

    display: inline-block;

    background: #eef2ff;

    color: #3730a3;

    padding:
    8px 13px;

    margin: 4px;

    border-radius: 20px;
}

.alert {

    background: #ecfdf5;

    color: #065f46;

    padding: 14px;

    border-radius: 10px;

    margin-bottom: 20px;
}

.grid {

    display: grid;

    grid-template-columns:
    repeat(
        auto-fit,
        minmax(250px, 1fr)
    );

    gap: 20px;
}

.stat {

    text-align: center;
}

.stat h2 {

    color: #4f46e5;

    font-size: 35px;
}

table {

    width: 100%;

    border-collapse: collapse;
}

th,
td {

    padding: 14px;

    border-bottom:
    1px solid #e5e7eb;

    text-align: left;
}

</style>

</head>

<body>

<nav>

<a class="logo" href="/">
TalentIQ
</a>

<a href="/">Home</a>

{% if session.get("user_id") %}

<a href="/dashboard">Dashboard</a>

<a href="/profile">Resume</a>

<a href="/jobs">Jobs</a>

<a href="/logout">Logout</a>

{% else %}

<a href="/login">Login</a>

<a href="/register">Register</a>

{% endif %}

</nav>

<div class="container">

{% with messages =
get_flashed_messages() %}

{% for message in messages %}

<div class="alert">
{{ message }}
</div>

{% endfor %}

{% endwith %}

{{ content|safe }}

</div>

</body>

</html>

"""


def page(content):

    return render_template_string(
        BASE_HTML,
        content=content
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    content = """

    <div class="card hero">

        <h1>TalentIQ</h1>

        <h2>
        Intelligent Recruitment &
        Candidate Analytics
        </h2>

        <p>
        AI-ready talent intelligence platform
        for resumes, skills, job matching and
        recruitment analytics.
        </p>

        <br>

        <a
        class="btn"
        href="/register">
        Get Started
        </a>

    </div>


    <div class="grid">

        <div class="card stat">

            <h2>📄</h2>

            <h3>Resume Analysis</h3>

            <p>
            Upload PDF or DOCX resumes
            and automatically analyze skills.
            </p>

        </div>


        <div class="card stat">

            <h2>🎯</h2>

            <h3>Job Matching</h3>

            <p>
            Calculate candidate-job
            compatibility scores.
            </p>

        </div>


        <div class="card stat">

            <h2>📊</h2>

            <h3>Analytics</h3>

            <p>
            Track resume quality,
            applications and matches.
            </p>

        </div>

    </div>

    """

    return page(content)


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "Please fill all fields."
            )

            return redirect(
                url_for("register")
            )

        connection = get_db()

        try:

            cursor = connection.execute(
                """
                INSERT INTO users
                (name,email,password)
                VALUES (?,?,?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(
                        password
                    )
                )
            )

            user_id = cursor.lastrowid

            connection.execute(
                """
                INSERT INTO profiles
                (user_id)
                VALUES (?)
                """,
                (user_id,)
            )

            connection.commit()

            flash(
                "Registration successful. Please login."
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Email already registered."
            )

        finally:

            connection.close()

    content = """

    <div class="card">

    <h1>Create TalentIQ Account</h1>

    <form method="POST">

    <label>Name</label>

    <input
    name="name"
    placeholder="Full Name"
    required>

    <label>Email</label>

    <input
    type="email"
    name="email"
    placeholder="Email"
    required>

    <label>Password</label>

    <input
    type="password"
    name="password"
    placeholder="Password"
    required>

    <button>
    Create Account
    </button>

    </form>

    </div>

    """

    return page(content)


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if (
            user
            and check_password_hash(
                user["password"],
                password
            )
        ):

            session["user_id"] = user["id"]

            session["name"] = user["name"]

            session["role"] = user["role"]

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password."
        )

    content = """

    <div class="card">

    <h1>Login to TalentIQ</h1>

    <form method="POST">

    <label>Email</label>

    <input
    type="email"
    name="email"
    placeholder="Email"
    required>

    <label>Password</label>

    <input
    type="password"
    name="password"
    placeholder="Password"
    required>

    <button>
    Login
    </button>

    </form>

    </div>

    """

    return page(content)


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# PROFILE + RESUME
# =========================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
@login_required
def profile():

    connection = get_db()

    profile_data = connection.execute(
        """
        SELECT *
        FROM profiles
        WHERE user_id=?
        """,
        (session["user_id"],)
    ).fetchone()

    analysis = None

    if request.method == "POST":

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        education = request.form.get(
            "education",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        resume = request.files.get(
            "resume"
        )

        resume_filename = (
            profile_data["resume"]
            or ""
        )

        resume_score = (
            profile_data["resume_score"]
            or 0
        )

        if resume and resume.filename:

            if not allowed_file(
                resume.filename
            ):

                flash(
                    "Only PDF and DOCX files are supported."
                )

                connection.close()

                return redirect(
                    url_for("profile")
                )

            filename = secure_filename(
                resume.filename
            )

            filename = (
                str(session["user_id"])
                + "_"
                + filename
            )

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            resume.save(filepath)

            try:

                resume_text = (
                    extract_resume_text(
                        filepath
                    )
                )

                if not resume_text.strip():

                    flash(
                        "Could not read text from this resume."
                    )

                else:

                    analysis = analyze_resume(
                        resume_text
                    )

                    detected = analysis[
                        "skills"
                    ]

                    if detected:

                        skills = ",".join(
                            detected
                        )

                    resume_score = analysis[
                        "score"
                    ]

                    resume_filename = filename

                    session[
                        "resume_analysis"
                    ] = analysis

                    flash(
                        "Resume analyzed successfully!"
                    )

            except Exception as error:

                print(
                    "Resume error:",
                    error
                )

                flash(
                    "Resume analysis failed."
                )

        connection.execute(
            """
            UPDATE profiles

            SET
            phone=?,
            education=?,
            skills=?,
            resume=?,
            resume_score=?

            WHERE user_id=?
            """,
            (
                phone,
                education,
                skills,
                resume_filename,
                resume_score,
                session["user_id"]
            )
        )

        connection.commit()

        profile_data = connection.execute(
            """
            SELECT *
            FROM profiles
            WHERE user_id=?
            """,
            (session["user_id"],)
        ).fetchone()

    connection.close()

    analysis = session.get(
        "resume_analysis"
    )

    analysis_html = ""

    if analysis:

        skill_html = ""

        for skill in analysis["skills"]:

            skill_html += (
                '<span class="skill">'
                + skill
                + '</span>'
            )

        education_status = (
            "✅ Found"
            if analysis["education"]
            else "❌ Missing"
        )

        experience_status = (
            "✅ Found"
            if analysis["experience"]
            else "❌ Missing"
        )

        project_status = (
            "✅ Found"
            if analysis["projects"]
            else "❌ Missing"
        )

        skills_status = (
            "✅ Found"
            if analysis["skills_section"]
            else "❌ Missing"
        )

        analysis_html = f"""

        <div class="card">

        <h2>Resume Analysis</h2>

        <div class="score">
        {analysis["score"]}%
        </div>

        <p>Resume Quality Score</p>

        <h3>Detected Skills</h3>

        {skill_html or "No skills detected"}

        <h3>Contact Detection</h3>

        <p>
        Email:
        <b>{analysis["email"]}</b>
        </p>

        <p>
        Phone:
        <b>{analysis["phone"]}</b>
        </p>

        <h3>Resume Sections</h3>

        <p>
        Education:
        {education_status}
        </p>

        <p>
        Experience:
        {experience_status}
        </p>

        <p>
        Projects:
        {project_status}
        </p>

        <p>
        Skills:
        {skills_status}
        </p>

        </div>

        """

    content = f"""

    <div class="card">

    <h1>My Resume</h1>

    <form
    method="POST"
    enctype="multipart/form-data">

    <label>Phone</label>

    <input
    name="phone"
    value="{profile_data["phone"] or ""}"
    placeholder="Phone number">

    <label>Education</label>

    <input
    name="education"
    value="{profile_data["education"] or ""}"
    placeholder="B.Tech CSE">

    <label>Skills</label>

    <input
    name="skills"
    value="{profile_data["skills"] or ""}"
    placeholder="Java, Python, SQL">

    <label>
    Upload Resume
    </label>

    <input
    type="file"
    name="resume"
    accept=".pdf,.docx"
    required>

    <button>
    Upload & Analyze Resume
    </button>

    </form>

    </div>

    {analysis_html}

    """

    return page(content)


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db()

    profile_data = connection.execute(
        """
        SELECT *
        FROM profiles
        WHERE user_id=?
        """,
        (session["user_id"],)
    ).fetchone()

    applications = connection.execute(
        """
        SELECT
        applications.*,
        jobs.title,
        jobs.company

        FROM applications

        JOIN jobs
        ON jobs.id = applications.job_id

        WHERE applications.user_id=?

        ORDER BY applications.id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    application_html = ""

    for application in applications:

        application_html += f"""

        <div class="card">

        <h3>
        {application["title"]}
        </h3>

        <p>
        Company:
        {application["company"]}
        </p>

        <p>
        Match:
        <b>{application["score"]}%</b>
        </p>

        <p>
        Status:
        <b>{application["status"]}</b>
        </p>

        </div>

        """

    content = f"""

    <div class="card">

    <h1>
    Welcome, {session["name"]} 👋
    </h1>

    <div class="grid">

        <div class="stat">

        <h2>
        {profile_data["resume_score"] or 0}%
        </h2>

        <p>Resume Score</p>

        </div>

        <div class="stat">

        <h2>
        {len(applications)}
        </h2>

        <p>Applications</p>

        </div>

    </div>

    <p>
    <b>Skills:</b>
    {profile_data["skills"] or "Upload your resume"}
    </p>

    <a
    class="btn"
    href="/jobs">
    Find Jobs
    </a>

    </div>

    <h2>
    My Applications
    </h2>

    {application_html or
    '<div class="card">No applications yet.</div>'}

    """

    return page(content)


# =========================================================
# JOBS
# =========================================================

@app.route("/jobs")
@login_required
def jobs():

    connection = get_db()

    jobs_list = connection.execute(
        "SELECT * FROM jobs"
    ).fetchall()

    profile_data = connection.execute(
        """
        SELECT *
        FROM profiles
        WHERE user_id=?
        """,
        (session["user_id"],)
    ).fetchone()

    connection.close()

    cards = ""

    candidate_skills = (
        profile_data["skills"]
        or ""
    )

    for job in jobs_list:

        score = match_score(
            candidate_skills,
            job["skills"]
        )

        cards += f"""

        <div class="card">

        <h2>
        {job["title"]}
        </h2>

        <h3>
        {job["company"]}
        </h3>

        <p>
        {job["description"]}
        </p>

        <p>
        Required skills:
        <b>{job["skills"]}</b>
        </p>

        <div class="match">
        {score}% Match
        </div>

        <br>

        <a
        class="btn"
        href="/apply/{job["id"]}">
        Apply Now
        </a>

        </div>

        """

    content = f"""

    <h1>Job Recommendations</h1>

    <p>
    Jobs are ranked using your detected
    skills.
    </p>

    {cards}

    """

    return page(content)


# =========================================================
# APPLY
# =========================================================

@app.route("/apply/<int:job_id>")
@login_required
def apply(job_id):

    connection = get_db()

    job = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE id=?
        """,
        (job_id,)
    ).fetchone()

    profile_data = connection.execute(
        """
        SELECT *
        FROM profiles
        WHERE user_id=?
        """,
        (session["user_id"],)
    ).fetchone()

    if not job:

        connection.close()

        return "Job not found", 404

    score = match_score(
        profile_data["skills"] or "",
        job["skills"]
    )

    existing = connection.execute(
        """
        SELECT *
        FROM applications

        WHERE user_id=?
        AND job_id=?
        """,
        (
            session["user_id"],
            job_id
        )
    ).fetchone()

    if existing:

        flash(
            "You already applied for this job."
        )

    else:

        connection.execute(
            """
            INSERT INTO applications
            (user_id,job_id,score,status)

            VALUES (?,?,?,?)
            """,
            (
                session["user_id"],
                job_id,
                score,
                "Applied"
            )
        )

        connection.commit()

        flash(
            f"Application submitted! "
            f"Your match score is {score}%."
        )

    connection.close()

    return redirect(
        url_for("jobs")
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "application": "TalentIQ",
        "resume_upload": True,
        "pdf_analysis": True,
        "docx_analysis": True,
        "skill_detection": True,
        "job_matching": True,
        "applications": True
    }


# =========================================================
# START
# =========================================================

init_database()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
