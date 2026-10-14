"""Turn raw job listings into a clean, analysis-ready table.

Only derived fields are kept (title, company, city, experience asked, skills
mentioned, salary if stated, seniority, role family, link). Full job
descriptions are NOT stored or redistributed.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROLE_RULES = [
    ("Data Analyst", r"\bdata analyst|\bdata analytics\b|\banalyst[- ,]+data\b|reporting analyst|\bmis\b|bi analyst|business intelligence|power ?bi|\bbi developer"),
    ("Business Analyst", r"business analyst|\bba\b"),
    ("Product Analyst", r"product analyst|growth analyst"),
    ("Data Scientist", r"data scien"),
    ("Analytics (other)", r"analytics|insights"),
]
EXCLUDE = r"trainer|instructor|mentor|teacher|faculty|financial plan|fp&a|record to report|order to cash|procure to pay|cyber|security analyst|qa analyst|quality analyst|service desk|recruit|tax|audit|credit analyst|equity research"

SKILLS = {
    "SQL": r"\bsql\b|mysql|postgres|t-sql|pl/sql|snowflake sql",
    "Excel": r"\bexcel\b|spreadsheets?|vlookup|xlookup|pivot table",
    "Python": r"\bpython\b",
    "Power BI": r"power ?bi",
    "Tableau": r"\btableau\b",
    "Looker": r"\blooker\b",
    "R": r"(?<![\w-])R(?![\w-])(?= (?:programming|language|studio)|,| or | and |/)",
    "Statistics": r"statistic",
    "Machine Learning": r"machine learning|\bml\b",
    "A/B Testing": r"a/b test|ab test|experimentation",
    "ETL": r"\betl\b|\belt\b|data pipeline",
    "Data Modeling": r"data model|star schema|dimensional model",
    "Cloud (AWS/Azure/GCP)": r"\baws\b|azure|\bgcp\b|google cloud|bigquery|redshift|databricks|snowflake",
    "Spark": r"\bspark\b|pyspark",
    "dbt": r"\bdbt\b",
    "Jira/Agile": r"\bjira\b|agile|scrum",
    "Communication": r"communication skills|stakeholder",
    "GenAI/LLM": r"\bllm|generative ai|gen ?ai|chatgpt|prompt engineering",
    "SAS": r"\bsas\b",
    "Google Analytics": r"google analytics|\bga4\b",
}

EXP_PATTERNS = [
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years|yrs)",
    r"(\d{1,2})\s*\+\s*(?:years|yrs)",
    r"(?:minimum|min\.?|at least)\s*(?:of\s*)?(\d{1,2})\s*(?:years|yrs)",
    r"(\d{1,2})\s*(?:years|yrs)\s*(?:of)?\s*(?:relevant|professional|hands-on|work|industry)?\s*experience",
]
FRESHER = r"fresher|freshers|0\s*(?:-|–|to)\s*1\s*(?:years|yrs)|entry[- ]level|graduate (?:program|trainee)|no experience required|recent graduates?"
SAL = r"(?:₹|inr|rs\.?)\s*([\d.,]+)\s*(?:-|–|to)\s*(?:₹|inr|rs\.?)?\s*([\d.,]+)\s*(lpa|lakhs?|per annum|/month|per month)?"


def role_family(title):
    t = title.lower()
    if re.search(EXCLUDE, t):
        return None
    for name, pat in ROLE_RULES:
        if re.search(pat, t):
            return name
    return None


def seniority(title):
    t = title.lower()
    if re.search(r"intern", t):
        return "Intern"
    if re.search(r"\b(senior|sr\.?|lead|principal|staff|manager|head|director|vice president|avp|l4|l5|4a|4b|4c)\b", t):
        return "Senior"
    if re.search(r"\b(junior|jr\.?|associate|trainee|entry|graduate|l1|l2)\b", t):
        return "Junior"
    return "Mid / unspecified"


def min_experience(text):
    """Lower bound of the FIRST experience requirement stated in the posting."""
    t = text.lower()
    hits = []
    for p in EXP_PATTERNS:
        for m in re.finditer(p, t):
            n = int(m.group(1))
            if 0 <= n <= 20:
                hits.append((m.start(), n))
    return min(hits)[1] if hits else None


def annual_salary_lpa(m):
    """Convert a matched salary range to (low, high) in lakhs per annum."""
    def num(x):
        return float(x.replace(",", ""))
    lo, hi = num(m.group(1)), num(m.group(2))
    unit = (m.group(3) or "").strip()
    monthly = "month" in unit or hi < 200000 and hi >= 1000 and "lpa" not in unit and "lakh" not in unit
    if "lpa" in unit or "lakh" in unit:
        return lo, hi
    if monthly:
        lo, hi = lo * 12, hi * 12
    return round(lo / 1e5, 2), round(hi / 1e5, 2)


def main(src, out):
    raw = json.load(open(src, encoding="utf-8"))["job_listings"]
    rows = []
    for j in raw:
        title = (j.get("title") or "").strip()
        fam = role_family(title)
        if not fam:
            continue
        desc = j.get("description") or ""
        low = desc.lower()
        row = {
            "job_id": j.get("crustdata_job_id"),
            "title": title,
            "role_family": fam,
            "seniority": seniority(title),
            "company": j.get("company_name"),
            "company_size": j.get("company_headcount_range"),
            "industry": (j.get("company_industries") or [None])[0],
            "city": j.get("city") or "Unspecified",
            "workplace": j.get("workplace_type"),
            "date_added": (j.get("date_added") or "")[:10],
            "url": j.get("url"),
            "min_years": min_experience(desc),
            "says_fresher": bool(re.search(FRESHER, low)),
            "desc_words": len(desc.split()),
        }
        for s, pat in SKILLS.items():
            flags = 0 if s == "R" else re.I
            row["skill_" + s] = bool(re.search(pat, desc if s == "R" else low, flags))
        m = re.search(SAL, low)
        row["salary_text"] = m.group(0) if m else None
        row["salary_lpa_low"], row["salary_lpa_high"] = annual_salary_lpa(m) if m else (None, None)
        rows.append(row)
    df = pd.DataFrame(rows).drop_duplicates(subset=["title", "company", "city"])
    df.to_csv(out, index=False)
    print(f"kept {len(df)} of {len(raw)} listings -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
