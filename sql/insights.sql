-- India Data Analyst Job Market Tracker: analysis layer (DuckDB)
-- Source table: jobs  (data/processed/jobs.csv, one row per unique posting)

-- Q1. How many postings are genuinely open to freshers?
--     "fresher-friendly" = not a senior title AND (intern/junior title, OR first stated
--     requirement is 0-1 years, OR the text says fresher/entry level and states no years).
CREATE OR REPLACE VIEW fresher_flag AS
SELECT *,
       (seniority <> 'Senior'
        AND (seniority IN ('Intern', 'Junior')
             OR min_years <= 1
             OR (says_fresher AND min_years IS NULL))) AS fresher_friendly
FROM jobs;

-- Q2. Experience asked, bucketed (only postings that state a number).
CREATE OR REPLACE VIEW experience_buckets AS
SELECT CASE
         WHEN min_years <= 1 THEN '0-1 yrs'
         WHEN min_years <= 2 THEN '2 yrs'
         WHEN min_years <= 4 THEN '3-4 yrs'
         WHEN min_years <= 7 THEN '5-7 yrs'
         ELSE '8+ yrs'
       END AS bucket,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM jobs
WHERE min_years IS NOT NULL
GROUP BY 1;

-- Q3. Cities: total vs fresher-friendly share.
CREATE OR REPLACE VIEW city_summary AS
SELECT city,
       COUNT(*) AS postings,
       SUM(fresher_friendly::INT) AS fresher_friendly,
       ROUND(100.0 * SUM(fresher_friendly::INT) / COUNT(*), 1) AS fresher_pct
FROM fresher_flag
GROUP BY city
ORDER BY postings DESC;

-- Q4. Salary bands (annual, lakhs) for postings that publish a salary,
--     excluding internships (stipends are a different market).
CREATE OR REPLACE VIEW salary_by_level AS
SELECT CASE WHEN fresher_friendly THEN 'Fresher-friendly' ELSE 'Experienced' END AS level,
       COUNT(*) AS postings_with_salary,
       ROUND(MEDIAN((salary_lpa_low + salary_lpa_high) / 2), 1) AS median_mid_lpa,
       ROUND(MIN(salary_lpa_low), 1) AS min_lpa,
       ROUND(MAX(salary_lpa_high), 1) AS max_lpa
FROM fresher_flag
WHERE salary_lpa_low IS NOT NULL AND seniority <> 'Intern'
GROUP BY 1;
