-- Stage 6a, author step G — GDELT 2.0 in Google BigQuery (author's Google Cloud; free BigQuery sandbox is enough).
-- Used for: Bangladesh census (X5, amended 2), GDELT check on every outlet (plan P1 completeness ratio), event matching
-- for timing following (V3a, codebook C3), weekly issue-event counts for event-adjusted salience (V1, A25; A31).
-- GDELT is open data; cite and attribute GDELT (A2). Estimated scan, all steps: ~400 GB (sandbox allowance: 1 TB/month).
-- Before each step BigQuery shows "This query will process … GB" (top right): if a step shows more than 300 GB, stop and tell me.
--
-- ONE-TIME SETUP (console.cloud.google.com/bigquery):
--   1. Explorer → your project → ⋮ → Create dataset → Dataset ID: periphery · Location: US (multi-region) → Create.
--   2. periphery → ⋮ → Create table → Source: Upload → file: data/sampling/census_urls.csv
--      → Table: mc_urls → Schema: Auto detect → Advanced: Header rows to skip = 1 → Create table.
-- Then paste and run ONE step at a time (G1 … G6). Steps that end in SELECT are downloaded as CSV:
--   results pane → Save results → CSV (local file) if < 10 MB, otherwise "CSV (Google Drive)", then download from Drive.
--   Put every CSV in data/raw/gdelt/ with the file name given at the step.

-- ── G1 · GKG articles of the 25 outlet hosts (creates a small table; ~200 GB scan, the largest step) ──────────────
CREATE OR REPLACE TABLE periphery.gkg_outlets AS
SELECT DISTINCT
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS day,
  SourceCommonName AS domain,
  REGEXP_REPLACE(LOWER(NET.HOST(DocumentIdentifier)), r'^www\.', '') AS host,
  REGEXP_REPLACE(REGEXP_REPLACE(LOWER(REGEXP_REPLACE(DocumentIdentifier, r'^https?://', '')), r'^www\.', ''), r'[?#].*$', '') AS url_raw,
  REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2022-02-24') AND TIMESTAMP('2025-01-01')
  AND SourceCommonName IN ('thedailystar.net','bdnews24.com','newagebd.net',
    'the-star.co.ke','nation.africa','tuko.co.ke','iol.co.za','citizen.co.za','timeslive.co.za',
    'punchng.com','dailypost.ng','tribuneonlineng.com','indiatimes.com','hindustantimes.com','thehindu.com',
    'malaymail.com','newsarawaktribune.com.my','malaysiakini.com',
    'nytimes.com','washingtonpost.com','theguardian.com','bbc.com','bbc.co.uk','apnews.com','reuters.com');

-- ── G2 · title matches with the codebook C1 terms (a view used by G3–G5; no scan cost) ───────────────────────────
CREATE OR REPLACE VIEW periphery.gkg_issue AS
SELECT *, REGEXP_REPLACE(url_raw, r'/$', '') AS url_norm,
  (REGEXP_CONTAINS(LOWER(title), r'\b(ukraine|ukrainian|kyiv|kiev|zelensky)\b')
     OR (REGEXP_CONTAINS(LOWER(title), r'\brussia\b') AND REGEXP_CONTAINS(LOWER(title), r'\binvasion\b'))) AS ukraine,
  (REGEXP_CONTAINS(LOWER(title), r'\b(gaza|hamas)\b')
     OR (REGEXP_CONTAINS(LOWER(title), r'\bisrael\b') AND REGEXP_CONTAINS(LOWER(title), r'\b(war|strike|ceasefire|hostages)\b'))) AS gaza,
  (REGEXP_CONTAINS(LOWER(title), r'\b(cop27|cop28)\b')
     OR (REGEXP_CONTAINS(LOWER(title), r'\bclimate\b') AND REGEXP_CONTAINS(LOWER(title), r'\b(summit|conference)\b')
         AND REGEXP_CONTAINS(LOWER(title), r'\b(sharm|dubai|unfccc)\b'))) AS cop
FROM periphery.gkg_outlets;

-- ── G3 · Bangladesh census → save as  data/raw/gdelt/g3_bangladesh_census.csv ─────────────────────────────────────
SELECT domain, host, day, url_norm, title, ukraine, gaza, cop
FROM periphery.gkg_issue
WHERE domain IN ('thedailystar.net','bdnews24.com','newagebd.net') AND (ukraine OR gaza OR cop)
ORDER BY domain, day;

-- ── G4 · weekly totals and title matches, every host → save as  data/raw/gdelt/g4_host_weeks.csv ─────────────────
SELECT domain, host, DATE_TRUNC(day, WEEK(THURSDAY)) AS week_start,
  COUNT(DISTINCT url_norm) AS articles,
  COUNT(DISTINCT IF(ukraine, url_norm, NULL)) AS ukraine_title,
  COUNT(DISTINCT IF(gaza, url_norm, NULL)) AS gaza_title,
  COUNT(DISTINCT IF(cop, url_norm, NULL)) AS cop_title
FROM periphery.gkg_issue
GROUP BY domain, host, week_start
ORDER BY domain, host, week_start;

-- ── G5 · event mentions of every issue story (Media Cloud census + Bangladesh), ~150 GB scan ─────────────────────
--        → save as  data/raw/gdelt/g5_story_events.csv  (likely > 10 MB: use Google Drive)
CREATE OR REPLACE TABLE periphery.story_events AS
WITH stories AS (
  SELECT outlet, issue, url_norm FROM periphery.mc_urls
  UNION ALL
  SELECT domain AS outlet, issue, url_norm
  FROM periphery.gkg_issue,
       UNNEST(ARRAY_CONCAT(IF(ukraine, ['ukraine'], []), IF(gaza, ['gaza'], []), IF(cop, ['cop'], []))) AS issue
  WHERE domain IN ('thedailystar.net','bdnews24.com','newagebd.net')
),
m AS (
  SELECT GLOBALEVENTID,
    PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(MentionTimeDate AS STRING)) AS mention_time,
    PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(EventTimeDate AS STRING)) AS event_time,
    REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(LOWER(REGEXP_REPLACE(MentionIdentifier, r'^https?://', '')), r'^www\.', ''), r'[?#].*$', ''), r'/$', '') AS url_norm
  FROM `gdelt-bq.gdeltv2.eventmentions_partitioned`
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2022-02-24') AND TIMESTAMP('2025-01-15')
    AND MentionSourceName IN ('thedailystar.net','bdnews24.com','newagebd.net','the-star.co.ke','nation.africa','tuko.co.ke',
      'iol.co.za','citizen.co.za','timeslive.co.za','punchng.com','dailypost.ng','tribuneonlineng.com','indiatimes.com',
      'hindustantimes.com','thehindu.com','malaymail.com','newsarawaktribune.com.my','malaysiakini.com',
      'nytimes.com','washingtonpost.com','theguardian.com','bbc.com','bbc.co.uk')
)
SELECT s.outlet, s.issue, m.GLOBALEVENTID, m.event_time, MIN(m.mention_time) AS first_mention, COUNT(DISTINCT s.url_norm) AS stories
FROM m JOIN stories s USING (url_norm)
GROUP BY 1, 2, 3, 4;
SELECT * FROM periphery.story_events ORDER BY GLOBALEVENTID, outlet;

-- ── G6 · events: attributes of matched events + weekly issue-event counts (A31), ~40 GB scan ───────────────────────
--        two downloads: data/raw/gdelt/g6a_event_attributes.csv  and  data/raw/gdelt/g6b_issue_event_weeks.csv
CREATE OR REPLACE TABLE periphery.events_small AS
SELECT GLOBALEVENTID, SQLDATE, Actor1CountryCode, Actor2CountryCode, EventCode, EventRootCode, QuadClass, IsRootEvent,
       NumMentions, ActionGeo_CountryCode, ActionGeo_FullName
FROM `gdelt-bq.gdeltv2.events_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2022-02-20') AND TIMESTAMP('2025-01-15')
  AND SQLDATE BETWEEN 20220224 AND 20241231;
-- G6a
SELECT e.* FROM periphery.events_small e
WHERE GLOBALEVENTID IN (SELECT DISTINCT GLOBALEVENTID FROM periphery.story_events);
-- G6b
SELECT DATE_TRUNC(PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING)), WEEK(THURSDAY)) AS week_start,
  COUNTIF(IsRootEvent = 1 AND ((Actor1CountryCode = 'RUS' AND Actor2CountryCode = 'UKR') OR (Actor1CountryCode = 'UKR' AND Actor2CountryCode = 'RUS') OR ActionGeo_CountryCode = 'UP')) AS ukraine_events,
  COUNTIF(IsRootEvent = 1 AND ((Actor1CountryCode = 'ISR' AND Actor2CountryCode = 'PSE') OR (Actor1CountryCode = 'PSE' AND Actor2CountryCode = 'ISR') OR ActionGeo_CountryCode = 'GZ')) AS gaza_events,
  COUNTIF(IsRootEvent = 1 AND (ActionGeo_FullName LIKE '%Sharm%' OR ActionGeo_FullName LIKE '%Dubai%')) AS cop_place_events,
  COUNT(*) AS all_events
FROM periphery.events_small
GROUP BY week_start ORDER BY week_start;
