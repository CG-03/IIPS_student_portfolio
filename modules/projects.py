"""Projects: full CRUD with optional thumbnail."""
import streamlit as st

from database import execute, query
from utils.helpers import (IMAGE_EXT, MAX_IMAGE_MB, check_url, clean, delete_file, flash, header,
                           save_upload, show_flash, show_image)


def _errors(title, desc, tech, gh, demo):
    errs = []
    if not title:
        errs.append("Project title is required.")
    if not desc:
        errs.append("Description is required.")
    if not tech:
        errs.append("Technologies are required.")
    for label, url in (("GitHub link", gh), ("Live demo link", demo)):
        e = check_url(url, label)
        if e:
            errs.append(e)
    return errs


def render(user):
    uid = user["id"]
    header("Projects", "Showcase what you have built")
    show_flash()
    tab_add, tab_list = st.tabs(["Add project", "My projects"])

    with tab_add:
        with st.form("add_project", clear_on_submit=True):
            title = st.text_input("Project title *", max_chars=100)
            desc = st.text_area("Description *", max_chars=1500, height=120)
            tech = st.text_input("Technologies * (comma separated)", max_chars=200)
            c1, c2 = st.columns(2)
            gh = c1.text_input("GitHub link")
            demo = c2.text_input("Live demo link")
            thumb = st.file_uploader(f"Thumbnail (PNG/JPG, max {MAX_IMAGE_MB} MB)", type=IMAGE_EXT)
            if st.form_submit_button("Add project", type="primary"):
                title, desc, tech = clean(title, 100), clean(desc, 1500), clean(tech, 200)
                gh, demo = clean(gh, 300), clean(demo, 300)
                errs = _errors(title, desc, tech, gh, demo)
                path = None
                if not errs:
                    try:
                        path = save_upload(thumb, uid, IMAGE_EXT, MAX_IMAGE_MB)
                    except ValueError as e:
                        errs.append(str(e))
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    execute("INSERT INTO projects (user_id, title, description, technologies, github_url, "
                            "demo_url, thumbnail_path) VALUES (?,?,?,?,?,?,?)",
                            (uid, title, desc, tech, gh, demo, path))
                    flash("Project added.")
                    st.rerun()

    with tab_list:
        rows = query("SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC", (uid,))
        if not rows:
            st.info("No projects yet. Add your first one in the other tab.")
        for r in rows:
            with st.expander(r["title"]):
                show_image(r["thumbnail_path"])
                st.write(r["description"])
                st.caption(f"Technologies: {r['technologies']}")
                lc1, lc2, _ = st.columns([1, 1, 4])
                if r["github_url"]:
                    lc1.link_button("GitHub", r["github_url"])
                if r["demo_url"]:
                    lc2.link_button("Live demo", r["demo_url"])
                st.markdown("**Edit project**")
                with st.form(f"edit_project_{r['id']}"):
                    title = st.text_input("Project title *", value=r["title"], max_chars=100)
                    desc = st.text_area("Description *", value=r["description"], max_chars=1500, height=120)
                    tech = st.text_input("Technologies *", value=r["technologies"], max_chars=200)
                    c1, c2 = st.columns(2)
                    gh = c1.text_input("GitHub link", value=r["github_url"] or "")
                    demo = c2.text_input("Live demo link", value=r["demo_url"] or "")
                    thumb = st.file_uploader("Replace thumbnail", type=IMAGE_EXT, key=f"thumb_{r['id']}")
                    remove = st.checkbox("Remove current thumbnail", key=f"rmthumb_{r['id']}")
                    b1, b2, _ = st.columns([1, 1, 4])
                    save = b1.form_submit_button("Save", type="primary")
                    delete = b2.form_submit_button("Delete")
                if delete:
                    delete_file(r["thumbnail_path"])
                    execute("DELETE FROM projects WHERE id=? AND user_id=?", (r["id"], uid))
                    flash("Project deleted.")
                    st.rerun()
                if save:
                    title, desc, tech = clean(title, 100), clean(desc, 1500), clean(tech, 200)
                    gh, demo = clean(gh, 300), clean(demo, 300)
                    errs = _errors(title, desc, tech, gh, demo)
                    new_path = r["thumbnail_path"]
                    if not errs:
                        try:
                            uploaded = save_upload(thumb, uid, IMAGE_EXT, MAX_IMAGE_MB)
                            if uploaded:
                                new_path = uploaded
                            elif remove:
                                new_path = None
                        except ValueError as e:
                            errs.append(str(e))
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        execute("UPDATE projects SET title=?, description=?, technologies=?, github_url=?, "
                                "demo_url=?, thumbnail_path=? WHERE id=? AND user_id=?",
                                (title, desc, tech, gh, demo, new_path, r["id"], uid))
                        if new_path != r["thumbnail_path"]:
                            delete_file(r["thumbnail_path"])
                        flash("Project updated.")
                        st.rerun()
