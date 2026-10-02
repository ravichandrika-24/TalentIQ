
from flask import Flask, render_template, request
from database import connect, initialize
from seed import seed
from matcher import candidates_for_job
from analytics import top_skills, candidate_ranking, job_report

app = Flask(__name__)
initialize()
seed()

@app.route("/")
def home():
    return render_template("index.html",
        skills=top_skills(), rankings=candidate_ranking(), jobs=job_report())

@app.route("/match/<int:job_id>")
def match(job_id):
    skills, ranked = candidates_for_job(job_id)
    return render_template("match.html", skills=skills, ranked=ranked, job_id=job_id)

@app.route("/health")
def health():
    try:
        with connect() as con:
            con.execute("SELECT 1")
        return {"application":"TalentIQ","status":"running","database":"OK","version":"1.0.0"}
    except Exception as e:
        return {"application":"TalentIQ","status":"error","database":"ERROR","message":str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
