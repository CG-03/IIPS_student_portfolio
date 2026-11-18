"""Personal profile details."""
import sqlite3
from contextlib import closing

import streamlit as st

from database import get_conn, query
from utils.helpers import PHONE_RE, check_url, clean, flash, header, show_flash


def render(user):
    uid = user["id"]
    p = query("SELECT * FROM student_profiles WHERE user_id = ?", (uid,), one=True)
    header("My Profile", "Your personal and contact details")
    show_flash()

    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full name *", value=user["full_name"], max_chars=80)
        enrollment = c2.text_input("Enrollment number *", value=p["enrollment_no"], max_chars=20)
        c1, c2, c3 = st.columns([2, 1, 2])
        course = c1.text_input("Course *", value=p["course"] or "", max_chars=60)
        semester = c2.number_input("Semester", min_value=1, max_value=10, value=int(p["semester"] or 1))
        location = c3.text_input("Location", value=p["location"] or "", max_chars=60)
        c1, c2 = st.columns(2)
        c1.text_input("Email (login ID)", value=user["email"] or "", disabled=True)
        phone = c2.text_input("Phone", value=p["phone"] or "", max_chars=15)
        headline = st.text_input("Headline (e.g. MCA student | Python & AI enthusiast)",
                                 value=p["headline"] or "", max_chars=120)
        summary = st.text_area("About me / professional summary", value=p["summary"] or "",
                               max_chars=800, height=120)
        c1, c2 = st.columns(2)
        github = c1.text_input("GitHub profile URL", value=p["github"] or "")
        linkedin = c2.text_input("LinkedIn profile URL", value=p["linkedin"] or "")
        submitted = st.form_submit_button("Save profile", type="primary")

    if not submitted:
        return
    full_name, enrollment = clean(full_name, 80), clean(enrollment, 20).upper()
    course, location, phone = clean(course, 60), clean(location, 60), clean(phone, 15)
    headline, summary = clean(headline, 120), clean(summary, 800)
    github, linkedin = clean(github, 300), clean(linkedin, 300)

    errors = []
    if len(full_name) < 3:
        errors.append("Full name is required.")
    if len(enrollment) < 4:
        errors.append("Enrollment number is required.")
    if not course:
        errors.append("Course is required.")
    if phone and not PHONE_RE.match(phone):
        errors.append("Phone number looks invalid.")
    for label, url in (("GitHub URL", github), ("LinkedIn URL", linkedin)):
        e = check_url(url, label)
        if e:
            errors.append(e)
    if errors:
        for e in errors:
            st.error(e)
        return

    with closing(get_conn()) as conn:
        try:
            conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, uid))
            conn.execute(
                "UPDATE student_profiles SET enrollment_no=?, course=?, semester=?, location=?, phone=?, "
                "headline=?, summary=?, github=?, linkedin=? WHERE user_id=?",
                (enrollment, course, semester, location, phone, headline, summary, github, linkedin, uid),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            st.error("That enrollment number is already registered to another student.")
            return
    flash("Profile saved.")
    st.rerun()
