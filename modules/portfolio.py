"""Portfolio view (own preview, public browsing) shared with the admin."""
import pandas as pd
import streamlit as st

from database import execute, query
from utils.helpers import badge, chips, esc, header, show_flash, show_image


def show_portfolio(uid, mode="owner"):
    """mode: 'owner' | 'admin' (full view) or 'public' (visible portfolios, approved achievements only)."""
    p = query("SELECT u.full_name, u.email, sp.* FROM users u JOIN student_profiles sp ON sp.user_id = u.id "
              "WHERE u.id = ? AND u.role = 'student'", (uid,), one=True)
    if not p:
        st.warning("Student record not found.")
        return
    if mode == "public" and not p["is_public"]:
        st.info("This portfolio is private.")
        return
    full_view = mode in ("owner", "admin")

    links = "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer">{label}</a>'
                    for label, u in (("GitHub", p["github"]), ("LinkedIn", p["linkedin"])) if u)
    contact = " · ".join(esc(x) for x in ((p["email"], p["phone"]) if full_view else ()) if x)
    cgpa = f" · CGPA {p['cgpa']:.2f}" if p["cgpa"] else ""
    st.markdown(
        f'<div class="hero"><h2>{esc(p["full_name"])}</h2>'
        f'<div class="sub">{esc(p["headline"] or "Student, IIPS DAVV")}</div>'
        f'<div>{esc(p["course"])} · Semester {p["semester"]}{cgpa}'
        f'{" · " + esc(p["location"]) if p["location"] else ""}</div>'
        f'<div style="margin-top:.6rem">{links}</div>'
        f'{"<div class=sub>" + contact + "</div>" if contact else ""}</div>',
        unsafe_allow_html=True)
    if p["summary"]:
        st.write(p["summary"])

    st.subheader("Education")
    recs = query("SELECT semester, sgpa, credits, remarks FROM academic_records WHERE user_id = ? ORDER BY semester", (uid,))
    st.markdown(f"**{p['course']}** · International Institute of Professional Studies, DAVV, Indore")
    if recs:
        st.dataframe(pd.DataFrame(recs).rename(columns={"semester": "Semester", "sgpa": "SGPA",
                                                         "credits": "Credits", "remarks": "Remarks"}), hide_index=True)
    if p["coursework"]:
        st.markdown(chips([c.strip() for c in p["coursework"].split(",") if c.strip()]), unsafe_allow_html=True)

    skills = query("SELECT category, name FROM skills WHERE user_id = ? ORDER BY category, name", (uid,))
    if skills:
        st.subheader("Technical Skills")
        for cat in dict.fromkeys(s["category"] for s in skills):
            st.markdown(f"**{cat}**  \n" + chips([s["name"] for s in skills if s["category"] == cat]),
                        unsafe_allow_html=True)

    projects = query("SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC", (uid,))
    if projects:
        st.subheader("Projects")
        cols = st.columns(2)
        for i, pr in enumerate(projects):
            with cols[i % 2]:
                with st.container(border=True):
                    show_image(pr["thumbnail_path"], width=280)
                    st.markdown(f"**{pr['title']}**")
                    st.write(pr["description"])
                    st.markdown(chips([t.strip() for t in pr["technologies"].split(",") if t.strip()]),
                                unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if pr["github_url"]:
                        b1.link_button("GitHub", pr["github_url"])
                    if pr["demo_url"]:
                        b2.link_button("Live demo", pr["demo_url"])

    certs = query("SELECT * FROM certifications WHERE user_id = ? ORDER BY completion_date DESC", (uid,))
    if certs:
        st.subheader("Certifications")
        for c in certs:
            line = f"**{c['name']}** — {c['issuer']} ({c['completion_date'] or '-'})"
            if c["credential_id"]:
                line += f" · ID: {c['credential_id']}"
            st.markdown(line)
            if c["verify_url"]:
                st.markdown(f"[Verify credential]({c['verify_url']})")

    clause = "" if full_view else " AND status = 'Approved'"
    achs = query(f"SELECT * FROM achievements WHERE user_id = ?{clause} ORDER BY event_date DESC", (uid,))
    if achs:
        st.subheader("Achievements")
        for a in achs:
            tag = badge(a["status"]) if full_view else badge("Approved")
            st.markdown(f"**{esc(a['title'])}** {tag}<br/>"
                        f"<span style='color:#6B7280'>{esc(a['type'])} · {esc(a['organization'])} · "
                        f"{esc(a['event_date'])} {('· ' + esc(a['position'])) if a['position'] else ''}</span>",
                        unsafe_allow_html=True)
            if a["description"]:
                st.caption(a["description"])


def render_own(user):
    uid = user["id"]
    header("My Portfolio", "Preview your portfolio and control who can see it")
    show_flash()
    p = query("SELECT is_public FROM student_profiles WHERE user_id = ?", (uid,), one=True)
    public = st.toggle("Make my portfolio visible to other logged-in users (shows only admin-approved achievements)",
                       value=bool(p["is_public"]))
    if public != bool(p["is_public"]):
        execute("UPDATE student_profiles SET is_public = ? WHERE user_id = ?", (1 if public else 0, uid))
        st.rerun()
    st.divider()
    show_portfolio(uid, "owner")


def render_browse(user):
    header("Browse Portfolios", "Portfolios shared by IIPS students")
    rows = query("SELECT u.id, u.full_name, sp.enrollment_no, sp.course, sp.headline FROM users u "
                 "JOIN student_profiles sp ON sp.user_id = u.id WHERE sp.is_public = 1 AND u.role = 'student' "
                 "ORDER BY u.full_name")
    if not rows:
        st.info("No student has made their portfolio public yet.")
        return
    term = st.text_input("Search by name or headline").strip().lower()
    rows = [r for r in rows if term in (r["full_name"] + " " + (r["headline"] or "")).lower()]
    if not rows:
        st.warning("No matching portfolios.")
        return
    choice = st.selectbox("Select a student", [r["id"] for r in rows],
                          format_func=lambda i: next(f"{r['full_name']} ({r['course']})" for r in rows if r["id"] == i))
    st.divider()
    show_portfolio(choice, "public")
