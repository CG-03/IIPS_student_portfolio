# IIPS Student Portfolio & Achievement Management System

A lightweight, fully offline web application where students of **IIPS, DAVV (Indore)** maintain their academic portfolio, skills, projects, certifications and hackathon achievements, generate a PDF resume, and where an admin verifies achievements.

Built with **Python + Streamlit + SQLite**. No external APIs, no API keys, no Node.js, no Docker, no ML models, and no internet needed after installation.

## Quick start

```bash
# 1. clone or download this repository, then open the folder
cd IIPS-Student-Portfolio

# 2. (optional but recommended) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate

# 3. install dependencies (only 3 small packages)
pip install -r requirements.txt

# 4. run
streamlit run app.py
```

The browser opens at `http://localhost:8501`. The database (`data/student_portfolio.db`), tables and upload folders are created automatically on first run.

## Demo admin account

| Username | Password |
|---|---|
| `admin` | `Admin@123` |

The app forces you to **change this password on first admin login**. Students register themselves from the **Register** tab.

## Features

| Module | What it does |
|---|---|
| Authentication | Student registration/login, admin login, PBKDF2-SHA256 password hashing with per-user salt, role-based access |
| Dashboard | Profile summary, counts, completion %, skills and SGPA charts |
| Academics | CGPA, relevant coursework, semester-wise SGPA records, academic achievements |
| Technical Skills | Six categories, add / edit / delete, proficiency levels |
| Projects | Title, description, technologies, GitHub/demo links, thumbnail, edit / delete |
| Certifications | Issuer, date, credential ID, verification link, certificate upload |
| Hackathons & Achievements | Competitions, participation, awards with proof upload and verification status |
| Resume Builder | Choose sections and items, generate a PDF offline with ReportLab |
| Portfolio | Own preview, public visibility toggle, browse other students' public portfolios |
| Admin | Platform statistics, student directory with full profiles, approve/reject achievements with remarks |

## Security notes

- Every student query is filtered by the logged-in user's ID, so students cannot read or edit another student's records.
- Public portfolios hide email and phone and show only admin-approved achievements.
- Uploads are validated by extension, size (images 2 MB, documents 5 MB) and content (PDF header, real image check) and stored under `uploads/<user_id>/` with randomised names.
- Links must be valid `http(s)` URLs. All user text is HTML-escaped where custom HTML is used.
- Streamlit usage telemetry is switched off in `.streamlit/config.toml`.

## Project structure

```
IIPS-Student-Portfolio/
├── app.py                 # entry point: login, navigation, routing
├── database.py            # SQLite schema and query helpers
├── auth.py                # hashing, registration, login, password change
├── requirements.txt
├── modules/               # one file per feature (dashboard, profile, academics, skills,
│                          #   projects, certifications, achievements, resume_builder,
│                          #   portfolio, admin)
├── utils/
│   ├── helpers.py         # validation, safe uploads, UI snippets
│   └── resume_generator.py
├── assets/style.css       # navy / royal blue / lilac theme
├── .streamlit/config.toml # theme and server settings
├── uploads/               # user files (git-ignored)
└── data/                  # SQLite database (git-ignored)
```

## Troubleshooting

- **`streamlit` not found**: run `python -m streamlit run app.py`.
- **Port already in use**: `streamlit run app.py --server.port 8502`.
- **"Could not initialise the application"**: make sure the project folder is writable.
- **Reset everything**: stop the app and delete `data/student_portfolio.db` and the contents of `uploads/`.
- **Backup**: copy the `data/` and `uploads/` folders.
- The PDF resume uses the built-in Helvetica font, so it supports Latin characters only.

## Requirements

Python 3.10+ and the packages in `requirements.txt` (`streamlit`, `reportlab`, `pillow`). Works on Windows, macOS and Linux.
