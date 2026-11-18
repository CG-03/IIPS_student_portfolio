"""Technical skills grouped by category."""
import streamlit as st

from database import execute, query
from utils.helpers import clean, flash, header, show_flash

CATEGORIES = ["Programming Languages", "Databases", "Web Development", "AI/ML", "Tools", "Soft Skills"]
LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]


def render(user):
    uid = user["id"]
    header("Technical Skills", "Organise your skills by category")
    show_flash()

    with st.form("add_skill", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Category", CATEGORIES)
        name = c2.text_input("Skill name *", max_chars=60)
        level = c3.selectbox("Proficiency", LEVELS, index=1)
        if st.form_submit_button("Add skill", type="primary"):
            name = clean(name, 60)
            if not name:
                st.error("Skill name is required.")
            elif query("SELECT 1 FROM skills WHERE user_id=? AND category=? AND LOWER(name)=LOWER(?)",
                       (uid, category, name), one=True):
                st.error("You have already added this skill in that category.")
            else:
                execute("INSERT INTO skills (user_id, category, name, level) VALUES (?,?,?,?)",
                        (uid, category, name, level))
                flash(f"Added {name}.")
                st.rerun()

    skills = query("SELECT * FROM skills WHERE user_id = ? ORDER BY name", (uid,))
    if not skills:
        st.info("No skills added yet.")
        return
    for cat in CATEGORIES:
        items = [s for s in skills if s["category"] == cat]
        if not items:
            continue
        st.subheader(f"{cat} ({len(items)})")
        for s in items:
            with st.expander(f"{s['name']} · {s['level']}"):
                with st.form(f"edit_skill_{s['id']}"):
                    c1, c2, c3 = st.columns(3)
                    new_cat = c1.selectbox("Category", CATEGORIES, index=CATEGORIES.index(s["category"]))
                    new_name = c2.text_input("Skill name", value=s["name"], max_chars=60)
                    new_level = c3.selectbox("Proficiency", LEVELS, index=LEVELS.index(s["level"]))
                    b1, b2, _ = st.columns([1, 1, 4])
                    if b1.form_submit_button("Save", type="primary"):
                        if not clean(new_name, 60):
                            st.error("Skill name is required.")
                        else:
                            execute("UPDATE skills SET category=?, name=?, level=? WHERE id=? AND user_id=?",
                                    (new_cat, clean(new_name, 60), new_level, s["id"], uid))
                            flash("Skill updated.")
                            st.rerun()
                    if b2.form_submit_button("Delete"):
                        execute("DELETE FROM skills WHERE id=? AND user_id=?", (s["id"], uid))
                        flash("Skill deleted.")
                        st.rerun()
