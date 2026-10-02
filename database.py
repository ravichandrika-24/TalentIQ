
import sqlite3
from pathlib import Path
DB = Path(__file__).with_name("talentiq.db")
def connect(): return sqlite3.connect(DB)
def initialize():
    with connect() as con:
        con.executescript(Path(__file__).with_name("schema.sql").read_text())
