"""Shared helpers: validation, safe file uploads and small UI snippets."""
import html
import io
import re
import uuid
from datetime import date
from pathlib import Path

import streamlit as st

from database import BASE_DIR, UPLOAD_DIR, query

IMAGE_EXT = ["png", "jpg", "jpeg"]
DOC_EXT = ["pdf", "png", "jpg", "jpeg"]
MAX_IMAGE_MB = 2
MAX_DOC_MB = 5
MIME = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")


# ---------- text / validation ----------
def esc(value):
    return html.escape("" if value is None else str(value))


def clean(value, max_len=500):
    return (value or "").strip()[:max_len]


def check_url(url, label="Link"):
    """Return an error message, or '' when the URL is empty or a valid http(s) URL."""
    if not url:
        return ""
    if len(url) > 300 or not re.match(r"^https?://[^\s/$.?#][^\s]*$", url):
        return f"{label} must be a valid http(s) URL."
    return ""


def to_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def count(table, user_id):
    return query(f"SELECT COUNT(*) AS c FROM {table} WHERE user_id = ?", (user_id,), one=True)["c"]


def profile_completion(user_id):
    p = query("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,), one=True)
    if not p:
        return 0
    checks = [bool(p[f]) for f in ("phone", "location", "headline", "summary", "github", "linkedin")]
    checks.append((p["cgpa"] or 0) > 0)
    for table in ("academic_records", "skills", "projects", "certifications", "achievements"):
        checks.append(count(table, user_id) > 0)
    return round(100 * sum(checks) / len(checks))


# ---------- files ----------
def save_upload(file, user_id, allowed, max_mb):
    """Validate and store an uploaded file. Returns a relative path or None. Raises ValueError."""
    if file is None:
        return None
    ext = Path(file.name).suffix.lower().lstrip(".")
    if ext not in allowed:
        raise ValueError(f"Unsupported file type. Allowed: {', '.join(allowed).upper()}.")
    data = file.getvalue()
    if len(data) > max_mb * 1024 * 1024:
        raise ValueError(f"File is too large (maximum {max_mb} MB).")
    if ext == "pdf" and not data.startswith(b"%PDF"):
        raise ValueError("The uploaded file is not a valid PDF.")
    if ext in ("png", "jpg", "jpeg"):
        try:
            from PIL import Image
            Image.open(io.BytesIO(data)).verify()
        except ImportError:
            pass
        except Exception:
            raise ValueError("The uploaded file is not a valid image.")
    folder = UPLOAD_DIR / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(file.name).stem)[:40] or "file"
    name = f"{uuid.uuid4().hex[:10]}_{stem}.{ext}"
    (folder / name).write_bytes(data)
    return f"uploads/{user_id}/{name}"


def abs_path(rel):
    return (BASE_DIR / rel).resolve() if rel else None


def file_exists(rel):
    path = abs_path(rel)
    return bool(path and path.is_file() and UPLOAD_DIR.resolve() in path.parents)


def delete_file(rel):
    if file_exists(rel):
        abs_path(rel).unlink()


def show_image(rel, width=260):
    if file_exists(rel):
        st.image(str(abs_path(rel)), width=width)


def download_file(rel, label, key):
    if not file_exists(rel):
        return
    path = abs_path(rel)
    ext = path.suffix.lower().lstrip(".")
    st.download_button(label, path.read_bytes(), file_name=path.name,
                       mime=MIME.get(ext, "application/octet-stream"), key=key)


# ---------- UI ----------
def load_css():
    css = (BASE_DIR / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def flash(message, kind="success"):
    st.session_state["_flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def header(title, subtitle=""):
    st.markdown(
        f'<div class="page-header"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def stat_row(items):
    cols = st.columns(len(items))
    for col, (label, value, hint) in zip(cols, items):
        col.markdown(
            f'<div class="stat-card"><div class="stat-label">{esc(label)}</div>'
            f'<div class="stat-value">{esc(value)}</div><div class="stat-hint">{esc(hint)}</div></div>',
            unsafe_allow_html=True,
        )


def badge(status):
    return f'<span class="badge badge-{esc(status).lower()}">{esc(status)}</span>'


def chips(values):
    return "".join(f'<span class="chip">{esc(v)}</span>' for v in values)
