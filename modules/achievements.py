"""Hackathons, competitions, participation and awards, with admin verification status."""
from datetime import date

import streamlit as st

from database import execute, query
from utils.helpers import (DOC_EXT, MAX_DOC_MB, badge, clean, delete_file, download_file, flash, header,
                           save_upload, show_flash, show_image, to_date)

TYPES = ["Hackathon", "Competition", "Participation", "Award", "Academic"]
MIN_DATE = date(2000, 1, 1)


def render(user):
    uid = user["id"]
    header("Hackathons & Achievements", "Add achievements with proof; the admin verifies them")
    show_flash()
    tab_add, tab_list = st.tabs(["Add achievement", "My achievements"])

    with tab_add:
        with st.form("add_ach", clear_on_submit=True):
            c1, c2 = st.columns(2)
            typ = c1.selectbox("Type", TYPES)
            title = c2.text_input("Title / event name *", max_chars=120)
            c1, c2 = st.columns(2)
            org = c1.text_input("Organizer / institution", max_chars=120)
            when = c2.date_input("Date", value=date.today(), min_value=MIN_DATE, max_value=date.today())
            pos = st.text_input("Result / position (e.g. Winner, Runner-up, Participant)", max_chars=80)
            desc = st.text_area("Description (what you built / did)", max_chars=600, height=100)
            proof = st.file_uploader(f"Proof (PDF/PNG/JPG, max {MAX_DOC_MB} MB)", type=DOC_EXT)
            if st.form_submit_button("Submit achievement", type="primary"):
                title = clean(title, 120)
                errs = [] if title else ["Title is required."]
                path = None
                if not errs:
                    try:
                        path = save_upload(proof, uid, DOC_EXT, MAX_DOC_MB)
                    except ValueError as e:
                        errs.append(str(e))
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    execute("INSERT INTO achievements (user_id, type, title, organization, event_date, position, "
                            "description, proof_path) VALUES (?,?,?,?,?,?,?,?)",
                            (uid, typ, title, clean(org, 120), when.isoformat(), clean(pos, 80),
                             clean(desc, 600), path))
                    flash("Achievement submitted. It will appear as verified once the admin approves it.")
                    st.rerun()

    with tab_list:
        rows = query("SELECT * FROM achievements WHERE user_id = ? ORDER BY id DESC", (uid,))
        if not rows:
            st.info("No achievements yet.")
        for r in rows:
            with st.expander(f"{r['title']} · {r['type']} · {r['status']}"):
                st.markdown(f"Status: {badge(r['status'])}", unsafe_allow_html=True)
                if r["admin_remark"]:
                    st.info(f"Admin remark: {r['admin_remark']}")
                st.caption(f"{r['organization'] or '-'} · {r['event_date'] or '-'} · {r['position'] or '-'}")
                if r["description"]:
                    st.write(r["description"])
                if r["proof_path"] and r["proof_path"].lower().endswith((".png", ".jpg", ".jpeg")):
                    show_image(r["proof_path"], width=320)
                download_file(r["proof_path"], "Download proof", key=f"dl_ach_{r['id']}")
                st.markdown("**Edit achievement** (editing sends it for verification again)")
                with st.form(f"edit_ach_{r['id']}"):
                    c1, c2 = st.columns(2)
                    typ = c1.selectbox("Type", TYPES, index=TYPES.index(r["type"]) if r["type"] in TYPES else 0)
                    title = c2.text_input("Title *", value=r["title"], max_chars=120)
                    c1, c2 = st.columns(2)
                    org = c1.text_input("Organizer", value=r["organization"] or "", max_chars=120)
                    when = c2.date_input("Date", value=min(max(to_date(r["event_date"]), MIN_DATE), date.today()),
                                         min_value=MIN_DATE, max_value=date.today())
                    pos = st.text_input("Result / position", value=r["position"] or "", max_chars=80)
                    desc = st.text_area("Description", value=r["description"] or "", max_chars=600, height=100)
                    proof = st.file_uploader("Replace proof", type=DOC_EXT, key=f"proof_{r['id']}")
                    b1, b2, _ = st.columns([1, 1, 4])
                    save = b1.form_submit_button("Save", type="primary")
                    delete = b2.form_submit_button("Delete")
                if delete:
                    delete_file(r["proof_path"])
                    execute("DELETE FROM achievements WHERE id=? AND user_id=?", (r["id"], uid))
                    flash("Achievement deleted.")
                    st.rerun()
                if save:
                    title = clean(title, 120)
                    errs = [] if title else ["Title is required."]
                    new_path = r["proof_path"]
                    if not errs:
                        try:
                            new_path = save_upload(proof, uid, DOC_EXT, MAX_DOC_MB) or new_path
                        except ValueError as e:
                            errs.append(str(e))
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        execute("UPDATE achievements SET type=?, title=?, organization=?, event_date=?, position=?, "
                                "description=?, proof_path=?, status='Pending', admin_remark='', reviewed_at=NULL "
                                "WHERE id=? AND user_id=?",
                                (typ, title, clean(org, 120), when.isoformat(), clean(pos, 80), clean(desc, 600),
                                 new_path, r["id"], uid))
                        if new_path != r["proof_path"]:
                            delete_file(r["proof_path"])
                        flash("Achievement updated and sent for verification.")
                        st.rerun()
