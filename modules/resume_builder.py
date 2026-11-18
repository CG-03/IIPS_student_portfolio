"""Resume builder: pick what to include and download a PDF."""
import re

import streamlit as st

from database import get_setting, query
from utils.helpers import header
from utils.resume_generator import generate_resume


def _collect(uid):
    return {
        "user": query("SELECT full_name, email FROM users WHERE id = ?", (uid,), one=True),
        "profile": query("SELECT * FROM student_profiles WHERE user_id = ?", (uid,), one=True),
        "records": query("SELECT * FROM academic_records WHERE user_id = ? ORDER BY semester", (uid,)),
        "skills": query("SELECT * FROM skills WHERE user_id = ? ORDER BY category, name", (uid,)),
        "projects": query("SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC", (uid,)),
        "certs": query("SELECT * FROM certifications WHERE user_id = ? ORDER BY completion_date DESC", (uid,)),
        "achievements": query("SELECT * FROM achievements WHERE user_id = ? AND status = 'Approved' "
                              "ORDER BY event_date DESC", (uid,)),
    }


def _pick(label, rows, key, title_key):
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    titles = {r["id"]: r[title_key] for r in rows}
    chosen = st.multiselect(label, ids, default=ids, format_func=lambda i: titles[i], key=key)
    return [r for r in rows if r["id"] in chosen]


def render(user):
    uid = user["id"]
    header("Resume Builder", "Generate a clean PDF resume from your portfolio data, fully offline")
    data = _collect(uid)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Choose what to include")
        opts = {
            "personal": st.checkbox("Personal details & summary", True),
            "education": st.checkbox("Education", True),
            "skills": st.checkbox("Technical skills", True),
            "projects": st.checkbox("Projects", True),
            "certs": st.checkbox("Certifications", True),
            "achievements": st.checkbox("Achievements (verified only)", True),
        }
        sel = dict(data)
        if opts["projects"]:
            sel["projects"] = _pick("Projects to include", data["projects"], "rb_projects", "title")
        if opts["certs"]:
            sel["certs"] = _pick("Certifications to include", data["certs"], "rb_certs", "name")
        if opts["achievements"]:
            sel["achievements"] = _pick("Achievements to include", data["achievements"], "rb_ach", "title")
    with right:
        st.subheader("Readiness")
        p = data["profile"]
        for ok, text in [
            (bool(p["summary"]), "Professional summary"),
            (bool(p["phone"]), "Phone number"),
            ((p["cgpa"] or 0) > 0, "CGPA"),
            (bool(data["skills"]), "At least one skill"),
            (bool(data["projects"]), "At least one project"),
        ]:
            st.write(("✅ " if ok else "⬜ ") + text)
        if not data["achievements"]:
            st.caption("Only admin-approved achievements can appear on the resume.")

    if st.button("Generate PDF resume", type="primary"):
        try:
            st.session_state["resume_pdf"] = generate_resume(sel, opts, get_setting("institution"))
            st.session_state["resume_owner"] = uid
        except Exception as exc:
            st.error(f"Could not generate the resume: {exc}")

    if st.session_state.get("resume_pdf") and st.session_state.get("resume_owner") == uid:
        fname = re.sub(r"[^A-Za-z0-9]+", "_", user["full_name"]).strip("_") or "Resume"
        st.success("Your resume is ready.")
        st.download_button("Download resume (PDF)", st.session_state["resume_pdf"],
                           file_name=f"{fname}_Resume.pdf", mime="application/pdf")
