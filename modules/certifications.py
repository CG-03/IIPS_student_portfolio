"""Certifications with optional certificate file upload."""
from datetime import date

import streamlit as st

from database import execute, query
from utils.helpers import (DOC_EXT, MAX_DOC_MB, check_url, clean, delete_file, download_file, flash,
                           header, save_upload, show_flash, show_image, to_date)

MIN_DATE = date(2000, 1, 1)


def _errors(name, issuer, url):
    errs = []
    if not name:
        errs.append("Certification name is required.")
    if not issuer:
        errs.append("Issuing organization is required.")
    e = check_url(url, "Verification link")
    if e:
        errs.append(e)
    return errs


def render(user):
    uid = user["id"]
    header("Certifications", "Courses and credentials you have completed")
    show_flash()
    tab_add, tab_list = st.tabs(["Add certification", "My certifications"])

    with tab_add:
        with st.form("add_cert", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Certification name *", max_chars=120)
            issuer = c2.text_input("Issuing organization *", max_chars=120)
            c1, c2 = st.columns(2)
            done = c1.date_input("Completion date", value=date.today(), min_value=MIN_DATE, max_value=date.today())
            cred = c2.text_input("Credential ID", max_chars=80)
            url = st.text_input("Verification link")
            file = st.file_uploader(f"Certificate file (PDF/PNG/JPG, max {MAX_DOC_MB} MB)", type=DOC_EXT)
            if st.form_submit_button("Add certification", type="primary"):
                name, issuer, cred, url = clean(name, 120), clean(issuer, 120), clean(cred, 80), clean(url, 300)
                errs = _errors(name, issuer, url)
                path = None
                if not errs:
                    try:
                        path = save_upload(file, uid, DOC_EXT, MAX_DOC_MB)
                    except ValueError as e:
                        errs.append(str(e))
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    execute("INSERT INTO certifications (user_id, name, issuer, completion_date, credential_id, "
                            "verify_url, file_path) VALUES (?,?,?,?,?,?,?)",
                            (uid, name, issuer, done.isoformat(), cred, url, path))
                    flash("Certification added.")
                    st.rerun()

    with tab_list:
        rows = query("SELECT * FROM certifications WHERE user_id = ? ORDER BY completion_date DESC, id DESC", (uid,))
        if not rows:
            st.info("No certifications yet.")
        for r in rows:
            with st.expander(f"{r['name']} · {r['issuer']}"):
                st.caption(f"Completed: {r['completion_date'] or '-'}  |  Credential ID: {r['credential_id'] or '-'}")
                if r["file_path"] and r["file_path"].lower().endswith((".png", ".jpg", ".jpeg")):
                    show_image(r["file_path"], width=320)
                c1, c2, _ = st.columns([1, 1, 4])
                if r["verify_url"]:
                    c1.link_button("Verify", r["verify_url"])
                if r["file_path"]:
                    download_file(r["file_path"], "Download file", key=f"dl_cert_{r['id']}")
                st.markdown("**Edit certification**")
                with st.form(f"edit_cert_{r['id']}"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Certification name *", value=r["name"], max_chars=120)
                    issuer = c2.text_input("Issuing organization *", value=r["issuer"], max_chars=120)
                    c1, c2 = st.columns(2)
                    done = c1.date_input("Completion date", value=min(max(to_date(r["completion_date"]), MIN_DATE), date.today()),
                                         min_value=MIN_DATE, max_value=date.today())
                    cred = c2.text_input("Credential ID", value=r["credential_id"] or "", max_chars=80)
                    url = st.text_input("Verification link", value=r["verify_url"] or "")
                    file = st.file_uploader("Replace certificate file", type=DOC_EXT, key=f"certfile_{r['id']}")
                    b1, b2, _ = st.columns([1, 1, 4])
                    save = b1.form_submit_button("Save", type="primary")
                    delete = b2.form_submit_button("Delete")
                if delete:
                    delete_file(r["file_path"])
                    execute("DELETE FROM certifications WHERE id=? AND user_id=?", (r["id"], uid))
                    flash("Certification deleted.")
                    st.rerun()
                if save:
                    name, issuer, cred, url = clean(name, 120), clean(issuer, 120), clean(cred, 80), clean(url, 300)
                    errs = _errors(name, issuer, url)
                    new_path = r["file_path"]
                    if not errs:
                        try:
                            new_path = save_upload(file, uid, DOC_EXT, MAX_DOC_MB) or new_path
                        except ValueError as e:
                            errs.append(str(e))
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        execute("UPDATE certifications SET name=?, issuer=?, completion_date=?, credential_id=?, "
                                "verify_url=?, file_path=? WHERE id=? AND user_id=?",
                                (name, issuer, done.isoformat(), cred, url, new_path, r["id"], uid))
                        if new_path != r["file_path"]:
                            delete_file(r["file_path"])
                        flash("Certification updated.")
                        st.rerun()
