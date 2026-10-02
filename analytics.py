
from database import connect
def top_skills():
    q="""SELECT s.name,COUNT(*) uses FROM skills s JOIN candidate_skills cs ON cs.skill_id=s.id
    GROUP BY s.id HAVING uses>0 ORDER BY uses DESC,s.name"""
    with connect() as c:return c.execute(q).fetchall()
def candidate_ranking():
    q="""WITH stats AS (SELECT c.name,c.experience,COUNT(cs.skill_id) skills
    FROM candidates c LEFT JOIN candidate_skills cs ON cs.candidate_id=c.id GROUP BY c.id)
    SELECT name,experience,skills,RANK() OVER(ORDER BY skills DESC,experience DESC) rank
    FROM stats ORDER BY rank"""
    with connect() as c:return c.execute(q).fetchall()
def job_report():
    q="""SELECT j.title,COUNT(a.id) applications,
    SUM(CASE WHEN a.status='hired' THEN 1 ELSE 0 END) hired
    FROM jobs j LEFT JOIN applications a ON a.job_id=j.id GROUP BY j.id ORDER BY applications DESC"""
    with connect() as c:return c.execute(q).fetchall()
