"""Admin: platform statistics, student directory and achievement review."""
from datetime import datetime

import pandas as pd
import streamlit as st

from database import execute, query
from modules.portfolio import show_portfolio
from utils.helpers import badge, download_file, flash, header, show_flash, show_image, stat_row


def _n(sql):
    return query(sql, one=True)["c"]


def render_overview(user):
    header("Platform Overview", "Statistics across all students")
    stat_row([
        ("Students", _n("SELECT COUNT(*) c FROM users WHERE role='student'"), ""),
        ("Public portfolios", _n("SELECT COUNT(*) c FROM student_profiles WHERE is_public=1"), ""),
        ("Average CGPA", f"{(query('SELECT AVG(cgpa) a FROM student_profiles WHERE cgpa > 0', one=True)['a'] or 0):.2f}", ""),
    ])
    stat_row([
        ("Projects", _n("SELECT COUNT(*) c FROM projects"), ""),
        ("Skills", _n("SELECT COUNT(*) c FROM skills"), ""),
        ("Certifications", _n("SELECT COUNT(*) c FROM certifications"), ""),
        ("Achievements", _n("SELECT COUNT(*) c FROM achievements"), ""),
    ])
    pending = _n("SELECT COUNT(*) c FROM achievements WHERE status='Pending'")
    if pending:
        st.warning(f"{pending} achievement(s) are waiting for review.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Achievements by status")
        rows = query("SELECT status, COUNT(*) AS count FROM achievements GROUP BY status")
        if rows:
            st.bar_chart(pd.DataFrame(rows).set_index("status"), color="#2F4FD8")
        else:
            st.info("No achievements submitted yet.")
    with c2:
        st.subheader("Achievements by type")
        rows = query("SELECT type, COUNT(*) AS count FROM achievements GROUP BY type")
        if rows:
            st.bar_chart(pd.DataFrame(rows).set_index("type"), color="#6D4BD8")
        else:
            st.info("No achievements submitted yet.")


def render_students(user):
    header("Registered Students", "Search students and open their full profiles")
    rows = query(
        "SELECT u.id, u.full_name AS Name, sp.enrollment_no AS Enrollment, sp.course AS Course, "
        "sp.semester AS Semester, sp.cgpa AS CGPA, "
        "(SELECT COUNT(*) FROM projects WHERE user_id=u.id) AS Projects, "
        "(SELECT COUNT(*) FROM skills WHERE user_id=u.id) AS Skills, "
        "(SELECT COUNT(*) FROM certifications WHERE user_id=u.id) AS Certifications, "
        "(SELECT COUNT(*) FROM achievements WHERE user_id=u.id) AS Achievements, "
        "CASE sp.is_public WHEN 1 THEN 'Yes' ELSE 'No' END AS Public "
        "FROM users u JOIN student_profiles sp ON sp.user_id = u.id WHERE u.role = 'student' ORDER BY u.full_name")
    if not rows:
        st.info("No students have registered yet.")
        return
    term = st.text_input("Search by name or enrollment number").strip().lower()
    if term:
        rows = [r for r in rows if term in f"{r['Name']} {r['Enrollment']}".lower()]
    if not rows:
        st.warning("No matching students.")
        return
    st.dataframe(pd.DataFrame(rows).drop(columns=["id"]), hide_index=True)
    choice = st.selectbox("Open student profile", [r["id"] for r in rows],
                          format_func=lambda i: next(f"{r['Name']} ({r['Enrollment']})" for r in rows if r["id"] == i))
    st.divider()
    show_portfolio(choice, "admin")


def _review(aid, status, remark):
    execute("UPDATE achievements SET status=?, admin_remark=?, reviewed_at=? WHERE id=?",
            (status, remark.strip()[:300], datetime.now().isoformat(timespec="seconds"), aid))
    flash(f"Achievement {status.lower()}.")
    st.rerun()


def render_reviews(user):
    header("Review Achievements", "Approve or reject achievements submitted by students")
    show_flash()
    status = st.radio("Show", ["Pending", "Approved", "Rejected", "All"], horizontal=True)
    where = "" if status == "All" else "WHERE a.status = ?"
    rows = query("SELECT a.*, u.full_name, sp.enrollment_no FROM achievements a "
                 "JOIN users u ON u.id = a.user_id JOIN student_profiles sp ON sp.user_id = a.user_id "
                 f"{where} ORDER BY a.id DESC", () if status == "All" else (status,))
    if not rows:
        st.info(f"No {status.lower()} achievements.")
        return
    for r in rows:
        with st.expander(f"{r['title']} — {r['full_name']} ({r['enrollment_no']}) · {r['status']}",
                         expanded=(status == "Pending")):
            st.markdown(f"{badge(r['status'])}", unsafe_allow_html=True)
            st.caption(f"{r['type']} · {r['organization'] or '-'} · {r['event_date'] or '-'} · {r['position'] or '-'}")
            if r["description"]:
                st.write(r["description"])
            if r["proof_path"] and r["proof_path"].lower().endswith((".png", ".jpg", ".jpeg")):
                show_image(r["proof_path"], width=320)
            download_file(r["proof_path"], "Download proof", key=f"adm_dl_{r['id']}")
            if not r["proof_path"]:
                st.caption("No proof uploaded.")
            remark = st.text_input("Remark (required when rejecting)", value=r["admin_remark"] or "",
                                   max_chars=300, key=f"remark_{r['id']}")
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Approve", key=f"approve_{r['id']}", type="primary"):
                _review(r["id"], "Approved", remark)
            if c2.button("Reject", key=f"reject_{r['id']}"):
                if not remark.strip():
                    st.error("Please add a remark explaining the rejection.")
                else:
                    _review(r["id"], "Rejected", remark)
