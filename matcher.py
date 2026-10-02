
from database import connect
from dsa import rank_candidates
def candidates_for_job(job_id):
    with connect() as con:
        job=con.execute("SELECT title,min_experience FROM jobs WHERE id=?",(job_id,)).fetchone()
        if not job:return [],[]
        skills=[r[0] for r in con.execute(
            "SELECT s.name FROM skills s JOIN job_skills js ON js.skill_id=s.id WHERE js.job_id=?",(job_id,))]
        candidates=[]
        for cid,name,exp in con.execute("SELECT id,name,experience FROM candidates"):
            cs=[r[0] for r in con.execute(
                "SELECT s.name FROM skills s JOIN candidate_skills x ON x.skill_id=s.id WHERE x.candidate_id=?",(cid,))]
            candidates.append({"id":cid,"name":name,"experience":exp,"skills":cs})
    return skills,rank_candidates(candidates,skills,job[1])
