"""Run the SQL layer and print the headline findings for the current snapshot."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def connect():
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE TABLE jobs AS SELECT * FROM read_csv_auto('{ROOT / 'data/processed/jobs.csv'}')")
    con.execute((ROOT / "sql/insights.sql").read_text())
    return con


def skill_share(con, where="TRUE"):
    cols = [r[0] for r in con.execute("SELECT column_name FROM (DESCRIBE jobs) WHERE column_name LIKE 'skill_%'").fetchall()]
    sel = ", ".join(f"ROUND(100.0*AVG(\"{c}\"::INT),1) AS \"{c[6:]}\"" for c in cols)
    row = con.execute(f"SELECT COUNT(*), {sel} FROM fresher_flag WHERE {where}").fetchone()
    n, vals = row[0], row[1:]
    return n, sorted(zip([c[6:] for c in cols], vals), key=lambda x: -x[1])


if __name__ == "__main__":
    con = connect()
    total, fr = con.execute("SELECT COUNT(*), SUM(fresher_friendly::INT) FROM fresher_flag").fetchone()
    span = con.execute("SELECT MIN(date_added), MAX(date_added) FROM jobs").fetchone()
    print(f"Snapshot {span[0]} -> {span[1]}: {total} analyst postings, {fr} fresher-friendly ({100*fr/total:.1f}%)")
    print("\nExperience asked:\n", con.execute("SELECT * FROM experience_buckets ORDER BY bucket").df())
    print("\nCities:\n", con.execute("SELECT * FROM city_summary LIMIT 8").df())
    print("\nSalary:\n", con.execute("SELECT * FROM salary_by_level").df())
    n, all_sk = skill_share(con)
    nf, fr_sk = skill_share(con, "fresher_friendly AND role_family IN ('Data Analyst','Business Analyst','Product Analyst')")
    print(f"\nSkills, all postings (n={n}):", all_sk[:10])
    print(f"Skills, fresher-friendly DA/BA/PA (n={nf}):", fr_sk[:10])
    pb, tb = con.execute("SELECT SUM(\"skill_Power BI\"::INT), SUM(skill_Tableau::INT) FROM jobs").fetchone()
    print(f"\nPower BI {pb} vs Tableau {tb} postings")
    sp = con.execute("SELECT SUM(skill_SQL::INT), SUM(skill_Python::INT), SUM((skill_SQL AND skill_Python)::INT) FROM jobs").fetchone()
    print("SQL / Python / both:", sp)
    gen = con.execute("SELECT role_family, ROUND(100*AVG(\"skill_GenAI/LLM\"::INT),1) FROM jobs GROUP BY 1 ORDER BY 2 DESC").fetchall()
    print("GenAI mention by role:", gen)
