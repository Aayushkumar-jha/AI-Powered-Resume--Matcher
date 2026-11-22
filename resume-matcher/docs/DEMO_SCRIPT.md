# Demo Video Script (~6 minutes)

Before recording, make sure PostgreSQL is running and **both servers are started** (`scripts/start.sh`). Open
http://localhost:5173 and use a clean database (delete old jobs on the Jobs page). Have `sample_data/` open in
Finder.

| Time | Screen | Say / do |
|---|---|---|
| 0:00 | Jobs page | "This is TalentMatch AI, an explainable resume matching and ranking system built with React, FastAPI, PostgreSQL and open-source NLP." |
| 0:20 | New Job | Paste `sample_data/jds/python_developer.txt` and click **Extract requirements**. |
| 0:40 | Requirements | "The JD was converted to structured JSON: mandatory vs preferred skills, 4+ years, Bachelor's in CS/IT, and responsibilities. I can edit everything." Add a skill, show the weight sliders (40/30/20/10), and click **Save**. |
| 1:30 | Resumes | Drag **all 12 resumes + all 8 edge-case files** at once and click **Upload**. "Each file is processed independently: 12 parsed, and the corrupted, empty, scanned, renamed, unsupported and duplicate files each get a clear reason." Scroll the status table. |
| 2:30 | Resumes | Click **Start analysis** and point out the progress bar. "Sentence embeddings with all-MiniLM-L6-v2 plus skill, experience and education scoring." |
| 2:50 | Dashboard | KPI cards, score distribution, fit categories, component averages and most-missing skills. |
| 3:20 | Ranking table | Search "FastAPI", filter "Strong match", sort by experience, then clear the filters. |
| 3:45 | Candidate: Priya Nair | "Moderate match: she has Flask and MySQL, which earn 50% related credit for FastAPI and PostgreSQL. Here's the exact calculation, the semantic evidence linking JD requirements to her resume sentences, and the gaps." |
| 4:30 | Candidate: Fatima Sheikh | "Her freelance work overlapped a full-time job. Overlapping periods are counted once. The fairness filter also removed her DOB and gender lines." |
| 5:00 | Compare | Tick the top 3 and click **Compare** to show the radar chart and side-by-side skills. |
| 5:20 | Export | Click **Export CSV** and open the file. |
| 5:35 | Requirements | Set weights to 100% skills, save, show the "outdated" banner, re-run, and show the changed ranking. |
| 5:55 | Close | "Scores are decision support, not hiring probabilities. Nothing is auto-rejected, sensitive attributes are never used, and everything is covered by 70 automated tests." |
