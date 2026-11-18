"""IIPS Student Portfolio & Achievement Management System - run with: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="IIPS Student Portfolio", page_icon="🎓", layout="wide")

import auth
import database
from modules import (academics, achievements, admin, certifications, dashboard, portfolio, profile,
                     projects, resume_builder, skills)
from utils.helpers import esc, flash, header, load_css, show_flash


@st.cache_resource(show_spinner=False)
def bootstrap():
    database.init_db()
    auth.ensure_default_admin()
    return True


def login_view():
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown("<h1 style='margin-bottom:0'>🎓 IIPS Student Portfolio</h1>"
                    "<p style='color:#6B7280'>Portfolio & Achievement Management System · IIPS, DAVV Indore</p>",
                    unsafe_allow_html=True)
        show_flash()
        tab_login, tab_reg = st.tabs(["Login", "Register"])
        with tab_login:
            with st.form("login_form"):
                ident = st.text_input("Email (students) or username (admin)")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary"):
                    if not ident.strip() or not pw:
                        st.error("Enter your email or username and password.")
                        return
                    user = auth.authenticate(ident, pw)
                    if user:
                        st.session_state["uid"] = user["id"]
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
        with tab_reg:
            with st.form("register_form", clear_on_submit=True):
                name = st.text_input("Full name", max_chars=80)
                enr = st.text_input("Enrollment number", max_chars=20)
                email = st.text_input("Email", max_chars=120)
                pw1 = st.text_input("Password (min 8 chars, letters + numbers)", type="password")
                pw2 = st.text_input("Confirm password", type="password")
                if st.form_submit_button("Create account", type="primary"):
                    ok, msg = auth.register_student(name, enr, email, pw1, pw2)
                    (st.success if ok else st.error)(msg)


def password_page(user, forced=False):
    header("Change Password", "Keep your account secure")
    show_flash()
    if forced:
        st.warning("You are using the default password. Please set a new one to continue.")
    with st.form("pw_form", clear_on_submit=True):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        conf = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update password", type="primary"):
            ok, msg = auth.change_password(user["id"], old, new, conf)
            if ok:
                flash(msg)
                st.rerun()
            else:
                st.error(msg)


def main():
    try:
        bootstrap()
    except Exception as exc:
        st.error(f"Could not initialise the application: {exc}. "
                 "Check that the project folder is writable (the data/ and uploads/ folders are created automatically).")
        st.stop()
    load_css()

    uid = st.session_state.get("uid")
    user = auth.get_user(uid) if uid else None
    if not user:
        st.session_state.clear()
        login_view()
        return

    if user["role"] == "admin":
        pages = {"📊  Overview": admin.render_overview, "👥  Students": admin.render_students,
                 "✅  Review Achievements": admin.render_reviews,
                 "🔒  Change Password": password_page}
    else:
        pages = {"🏠  Dashboard": dashboard.render, "👤  My Profile": profile.render,
                 "🎓  Academics": academics.render, "💻  Technical Skills": skills.render,
                 "🚀  Projects": projects.render, "📜  Certifications": certifications.render,
                 "🏆  Hackathons & Achievements": achievements.render,
                 "📄  Resume Builder": resume_builder.render, "🌐  My Portfolio": portfolio.render_own,
                 "🔎  Browse Portfolios": portfolio.render_browse,
                 "🔒  Change Password": password_page}

    with st.sidebar:
        st.markdown('<div class="brand">🎓 IIPS Portfolio<small>Achievement Management System</small></div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="user-box"><b>{esc(user["full_name"])}</b><br/>{esc(user["role"].title())}</div>',
                    unsafe_allow_html=True)
        st.divider()
        choice = None if user["must_change_password"] else st.radio("Navigation", list(pages), label_visibility="collapsed")
        st.divider()
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()

    if user["must_change_password"]:
        password_page(user, forced=True)
        return
    try:
        if choice == "🔒  Change Password":
            password_page(user)
        else:
            pages[choice](user)
    except Exception as exc:  # friendly message instead of a raw traceback
        st.error(f"Something went wrong while loading this page: {exc}")


main()
