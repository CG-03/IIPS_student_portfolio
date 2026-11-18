"""Academic portfolio: CGPA, coursework, semester records and academic achievements."""
from datetime import date

import pandas as pd
import streamlit as st

from database import execute, query
from utils.helpers import clean, badge, flash, header, show_flash, to_date


def render(user):
    uid = user["id"]
    header("Academic Portfolio", "CGPA, semester records, coursework and academic achievements")
    show_flash()
    t1, t2, t3 = st.tabs(["Overview", "Semester records", "Academic achievements"])
    with t1:
        _overview(uid)
    with t2:
        _records(uid)
    with t3:
        _achievements(uid)


def _overview(uid):
    p = query("SELECT cgpa, coursework FROM student_profiles WHERE user_id = ?", (uid,), one=True)
    recs = query("SELECT sgpa, credits FROM academic_records WHERE user_id = ?", (uid,))
    if recs:
        total = sum(r["credits"] for r in recs)
        calc = (sum(r["sgpa"] * r["credits"] for r in recs) / total) if total else sum(r["sgpa"] for r in recs) / len(recs)
        st.info(f"Calculated from your semester records: **{calc:.2f}**")
    with st.form("overview_form"):
        cgpa = st.number_input("Current CGPA (out of 10)", min_value=0.0, max_value=10.0,
                               value=float(p["cgpa"] or 0.0), step=0.01, format="%.2f")
        coursework = st.text_area("Relevant coursework (comma separated)", value=p["coursework"] or "",
                                  max_chars=600, height=100,
                                  placeholder="Data Structures, DBMS, Operating Systems, Machine Learning")
        if st.form_submit_button("Save", type="primary"):
            items = [c.strip() for c in coursework.replace("\n", ",").split(",") if c.strip()]
            execute("UPDATE student_profiles SET cgpa = ?, coursework = ? WHERE user_id = ?",
                    (cgpa, ", ".join(items)[:600], uid))
            flash("Academic overview saved.")
            st.rerun()


def _records(uid):
    with st.form("add_record", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        sem = c1.selectbox("Semester", list(range(1, 11)))
        sgpa = c2.number_input("SGPA", min_value=0.0, max_value=10.0, step=0.01, format="%.2f")
        credits = c3.number_input("Credits", min_value=0, max_value=40, step=1)
        remarks = st.text_input("Remarks (optional)", max_chars=200)
        if st.form_submit_button("Add record", type="primary"):
            if query("SELECT 1 FROM academic_records WHERE user_id=? AND semester=?", (uid, sem), one=True):
                st.error(f"A record for semester {sem} already exists. Edit it below instead.")
            elif sgpa <= 0:
                st.error("SGPA must be greater than 0.")
            else:
                execute("INSERT INTO academic_records (user_id, semester, sgpa, credits, remarks) VALUES (?,?,?,?,?)",
                        (uid, sem, sgpa, credits, clean(remarks, 200)))
                flash(f"Semester {sem} record added.")
                st.rerun()

    rows = query("SELECT * FROM academic_records WHERE user_id = ? ORDER BY semester", (uid,))
    if not rows:
        st.info("No semester records yet.")
        return
    st.dataframe(pd.DataFrame(rows)[["semester", "sgpa", "credits", "remarks"]], hide_index=True)
    for r in rows:
        with st.expander(f"Edit semester {r['semester']}"):
            with st.form(f"edit_record_{r['id']}"):
                c1, c2 = st.columns(2)
                sgpa = c1.number_input("SGPA", 0.0, 10.0, float(r["sgpa"]), 0.01, format="%.2f")
                credits = c2.number_input("Credits", 0, 40, int(r["credits"] or 0))
                remarks = st.text_input("Remarks", value=r["remarks"] or "", max_chars=200)
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.form_submit_button("Save", type="primary"):
                    execute("UPDATE academic_records SET sgpa=?, credits=?, remarks=? WHERE id=? AND user_id=?",
                            (sgpa, credits, clean(remarks, 200), r["id"], uid))
                    flash("Record updated.")
                    st.rerun()
                if b2.form_submit_button("Delete"):
                    execute("DELETE FROM academic_records WHERE id=? AND user_id=?", (r["id"], uid))
                    flash("Record deleted.")
                    st.rerun()


def _achievements(uid):
    st.caption("Academic achievements are sent to the admin for verification, just like hackathons and awards.")
    with st.form("add_acad_ach", clear_on_submit=True):
        title = st.text_input("Achievement title *", max_chars=120, placeholder="e.g. Semester Topper, Merit Scholarship")
        c1, c2 = st.columns(2)
        org = c1.text_input("Awarded by", max_chars=120)
        when = c2.date_input("Date", value=date.today(), min_value=date(2000, 1, 1), max_value=date.today())
        desc = st.text_area("Details", max_chars=500, height=80)
        if st.form_submit_button("Add achievement", type="primary"):
            if not clean(title, 120):
                st.error("Title is required.")
            else:
                execute("INSERT INTO achievements (user_id, type, title, organization, event_date, description) "
                        "VALUES (?, 'Academic', ?, ?, ?, ?)",
                        (uid, clean(title, 120), clean(org, 120), when.isoformat(), clean(desc, 500)))
                flash("Academic achievement submitted for verification.")
                st.rerun()
    rows = query("SELECT * FROM achievements WHERE user_id=? AND type='Academic' ORDER BY id DESC", (uid,))
    for r in rows:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f"**{r['title']}** {badge(r['status'])}  \n{r['organization'] or ''} · {r['event_date'] or ''}",
                    unsafe_allow_html=True)
        if c2.button("Delete", key=f"del_acad_{r['id']}"):
            execute("DELETE FROM achievements WHERE id=? AND user_id=?", (r["id"], uid))
            flash("Achievement deleted.")
            st.rerun()
