"""Offline PDF resume generation with ReportLab."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1F4B")
ROYAL = colors.HexColor("#2F4FD8")
GREY = colors.HexColor("#4B5563")

NAME = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NAVY)
HEADLINE = ParagraphStyle("headline", fontName="Helvetica", fontSize=11, leading=14, textColor=ROYAL)
CONTACT = ParagraphStyle("contact", fontName="Helvetica", fontSize=9, leading=12, textColor=GREY)
SECTION = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY, spaceBefore=8)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.black)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=9, textColor=GREY)
RIGHT = ParagraphStyle("right", parent=BODY, alignment=2, textColor=GREY)


def _p(text, style=BODY):
    return Paragraph(escape(str(text)), style)


def _rich(markup, style=BODY):
    """Paragraph from markup the caller has already escaped."""
    return Paragraph(markup, style)


def _section(title):
    return [Spacer(1, 3), Paragraph(escape(title.upper()), SECTION),
            HRFlowable(width="100%", thickness=0.8, color=ROYAL, spaceAfter=4)]


def generate_resume(data, options, institution):
    """data: dict with user, profile, records, skills, projects, certs, achievements. Returns PDF bytes."""
    buf = BytesIO()
    user, prof = data["user"], data["profile"]
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f"{user['full_name']} - Resume", author=user["full_name"])
    story = [_p(user["full_name"], NAME)]
    if prof["headline"]:
        story.append(_p(prof["headline"], HEADLINE))
    if options.get("personal"):
        parts = [x for x in (user["email"], prof["phone"], prof["location"], prof["github"], prof["linkedin"]) if x]
        if parts:
            story += [Spacer(1, 2), _p("  |  ".join(parts), CONTACT)]
        if prof["summary"]:
            story += _section("Professional Summary") + [_p(prof["summary"])]

    if options.get("education"):
        story += _section("Education")
        left = _rich(f"<b>{escape(prof['course'] or 'Course')}</b><br/>{escape(institution)}")
        cg = f"CGPA: {prof['cgpa']:.2f}/10" if prof["cgpa"] else ""
        right = _p(f"Semester {prof['semester']}" + (f"  |  {cg}" if cg else ""), RIGHT)
        t = Table([[left, right]], colWidths=[120 * mm, 54 * mm], hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(t)
        if data["records"]:
            line = "  ·  ".join(f"Sem {r['semester']}: {r['sgpa']:.2f}" for r in data["records"])
            story += [Spacer(1, 3), _p(f"SGPA - {line}", SMALL)]
        if prof["coursework"]:
            story += [Spacer(1, 2), _rich(f"<b>Relevant coursework:</b> {escape(prof['coursework'])}", SMALL)]

    if options.get("skills") and data["skills"]:
        story += _section("Technical Skills")
        groups = {}
        for s in data["skills"]:
            groups.setdefault(s["category"], []).append(s["name"])
        for cat, names in groups.items():
            story.append(_rich(f"<b>{escape(cat)}:</b> {escape(', '.join(names))}"))

    if options.get("projects") and data["projects"]:
        story += _section("Projects")
        for p in data["projects"]:
            story.append(_rich(f"<b>{escape(p['title'])}</b>  <font color='#2F4FD8'>| {escape(p['technologies'])}</font>"))
            story.append(_p(p["description"]))
            links = [u for u in (p["github_url"], p["demo_url"]) if u]
            if links:
                story.append(_p("  ·  ".join(links), SMALL))
            story.append(Spacer(1, 4))

    if options.get("certs") and data["certs"]:
        story += _section("Certifications")
        for c in data["certs"]:
            extra = f" ({c['completion_date']})" if c["completion_date"] else ""
            cred = f"  ·  Credential ID: {escape(c['credential_id'])}" if c["credential_id"] else ""
            story.append(_rich(f"<b>{escape(c['name'])}</b> - {escape(c['issuer'])}{escape(extra)}{cred}"))

    if options.get("achievements") and data["achievements"]:
        story += _section("Achievements")
        for a in data["achievements"]:
            bits = [x for x in (a["position"], a["organization"], a["event_date"]) if x]
            tail = f" - {escape(', '.join(bits))}" if bits else ""
            story.append(_rich(f"<b>{escape(a['title'])}</b>{tail}"))
            if a["description"]:
                story.append(_p(a["description"], SMALL))
            story.append(Spacer(1, 3))

    doc.build(story)
    return buf.getvalue()
