"""Student dashboard: summary cards, completion and simple charts."""
import pandas as pd
import streamlit as st

from database import query
from utils.helpers import count, header, profile_completion, stat_row


def render(user):
    uid = user["id"]
    p = query("SELECT * FROM student_profiles WHERE user_id = ?", (uid,), one=True)
    header(f"Welcome back, {user['full_name'].split()[0]}", "A quick snapshot of your academic portfolio")

    approved = query("SELECT COUNT(*) AS c FROM achievements WHERE user_id = ? AND status = 'Approved'",
                     (uid,), one=True)["c"]
    total_ach = count("achievements", uid)
    cgpa = f"{p['cgpa']:.2f}" if p["cgpa"] else "N/A"

    stat_row([
        ("Student", user["full_name"], p["enrollment_no"]),
        ("Course", p["course"] or "-", f"Semester {p['semester']}"),
        ("CGPA", cgpa, "out of 10"),
    ])
    stat_row([
        ("Projects", count("projects", uid), ""),
        ("Skills", count("skills", uid), ""),
        ("Certifications", count("certifications", uid), ""),
        ("Achievements", total_ach, f"{approved} verified"),
    ])

    pct = profile_completion(uid)
    st.markdown(f"**Profile completion: {pct}%**")
    st.progress(pct / 100)
    if pct < 100:
        st.caption("Tip: complete your profile, academics, skills, projects, certifications and achievements to reach 100%.")

    left, right = st.columns(2)
    with left:
        st.subheader("Skills by category")
        rows = query("SELECT category, COUNT(*) AS skills FROM skills WHERE user_id = ? GROUP BY category", (uid,))
        if rows:
            st.bar_chart(pd.DataFrame(rows).set_index("category"), color="#2F4FD8")
        else:
            st.info("Add skills to see this chart.")
    with right:
        st.subheader("SGPA trend")
        rows = query("SELECT semester, sgpa FROM academic_records WHERE user_id = ? ORDER BY semester", (uid,))
        if rows:
            st.line_chart(pd.DataFrame(rows).set_index("semester"), color="#6D4BD8")
        else:
            st.info("Add semester records to see this chart.")
