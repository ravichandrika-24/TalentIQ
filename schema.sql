
CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY,name TEXT,experience INTEGER);
CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY,name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS candidate_skills(candidate_id INTEGER,skill_id INTEGER,PRIMARY KEY(candidate_id,skill_id));
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,title TEXT,min_experience INTEGER);
CREATE TABLE IF NOT EXISTS job_skills(job_id INTEGER,skill_id INTEGER,PRIMARY KEY(job_id,skill_id));
CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,candidate_id INTEGER,job_id INTEGER,status TEXT,applied_at TEXT);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill ON candidate_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
