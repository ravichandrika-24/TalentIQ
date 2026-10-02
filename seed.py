
from database import connect, initialize
def seed():
    initialize()
    with connect() as con:
        con.executescript("""
        DELETE FROM applications; DELETE FROM job_skills; DELETE FROM candidate_skills;
        DELETE FROM jobs; DELETE FROM skills; DELETE FROM candidates;
        INSERT INTO candidates VALUES (1,'Ananya',4),(2,'Rahul',6),(3,'Meera',3),(4,'Vikram',8);
        INSERT INTO skills VALUES (1,'Python'),(2,'SQL'),(3,'DSA'),(4,'Django'),(5,'AWS'),(6,'Java');
        INSERT INTO candidate_skills VALUES
        (1,1),(1,2),(1,3),(2,1),(2,2),(2,5),(2,3),
        (3,1),(3,2),(4,1),(4,2),(4,3),(4,5),(4,6);
        INSERT INTO jobs VALUES
        (1,'Senior Python Engineer',5),(2,'Data Engineer',3),(3,'Backend Engineer',4);
        INSERT INTO job_skills VALUES
        (1,1),(1,2),(1,3),(2,1),(2,2),(2,5),(3,1),(3,2),(3,3);
        INSERT INTO applications VALUES
        (1,1,1,'applied','2026-09-01'),(2,2,1,'shortlisted','2026-09-02'),
        (3,3,2,'rejected','2026-09-03'),(4,4,1,'hired','2026-09-04'),
        (5,2,2,'shortlisted','2026-09-05'),(6,1,3,'applied','2026-09-06');
        """)
