import calendar
from datetime import date, datetime, timedelta
from io import BytesIO

import bleach
from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import or_

from . import db
from .forms import LogbookEntryForm
from .models import Activity, LogbookEntry

main_bp = Blueprint("main", __name__)
ALLOWED_TAGS = ["p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "h2", "h3", "a"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


@main_bp.app_template_filter("hours")
def format_hours(minutes):
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} h {rest} min"
    return f"{hours} h" if hours else f"{rest} min"


@main_bp.app_template_filter("longdate")
def format_long_date(value, with_year=True):
    """Format a date as 'Monday, 2 November 2026' without a leading zero on the day."""
    text = f"{value:%A}, {value.day} {value:%B}"
    return f"{text} {value.year}" if with_year else text


def owned_entry(entry_id):
    return LogbookEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()


def clean_description(value):
    return bleach.clean(value or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


def submitted_rows():
    """Return the activity rows sent by the editor, so they can be shown again after an error."""
    return [
        {"start": start, "end": end, "text": text}
        for text, start, end in zip(
            request.form.getlist("activity[]"),
            request.form.getlist("start_time[]"),
            request.form.getlist("end_time[]"),
        )
    ]


def entry_rows(entry):
    if entry is None:
        return [{"start": "", "end": "", "text": ""}]
    return [
        {"start": a.start_time.strftime("%H:%M"), "end": a.end_time.strftime("%H:%M"), "text": a.activity}
        for a in entry.activities
    ]


def save_activities(entry):
    """Replace an entry's activities with validated rows sent by the editor."""
    entry.activities.clear()
    for order, row in enumerate(submitted_rows()):
        activity_text, start, end = row["text"].strip(), row["start"], row["end"]
        if not any((activity_text, start, end)):
            continue
        number = order + 1
        try:
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
        except ValueError as error:
            raise ValueError(f"Activity {number} needs a start and end time.") from error
        if end_time <= start_time:
            raise ValueError(f"Activity {number} ends before it starts. Check the times.")
        if not activity_text:
            raise ValueError(f"Activity {number} needs a description.")
        entry.activities.append(Activity(
            start_time=start_time, end_time=end_time, activity=activity_text, display_order=order
        ))


@main_bp.route("/")
@login_required
def dashboard():
    today = date.today()
    entries = current_user.logbook_entries.order_by(LogbookEntry.date.desc())
    week_start = today - timedelta(days=today.weekday())
    week_days = [week_start + timedelta(days=offset) for offset in range(7)]
    week_entries = {entry.date: entry for entry in entries.filter(
        LogbookEntry.date >= week_start, LogbookEntry.date <= week_days[-1]
    ).all()}
    days_this_month = entries.filter(
        db.extract("year", LogbookEntry.date) == today.year,
        db.extract("month", LogbookEntry.date) == today.month,
    ).count()
    return render_template(
        "dashboard.html", today=today, today_entry=week_entries.get(today), week_days=week_days,
        week_entries=week_entries, latest_entries=entries.limit(5).all(), total_entries=entries.count(),
        days_this_month=days_this_month,
    )


@main_bp.route("/entries")
@login_required
def entries():
    query = request.args.get("q", "").strip()
    entry_query = current_user.logbook_entries
    if query:
        filters = [
            LogbookEntry.title.ilike(f"%{query}%"),
            LogbookEntry.description.ilike(f"%{query}%"),
            LogbookEntry.activities.any(Activity.activity.ilike(f"%{query}%")),
        ]
        try:
            filters.append(LogbookEntry.date == datetime.strptime(query, "%Y-%m-%d").date())
        except ValueError:
            pass
        entry_query = entry_query.filter(or_(*filters))
    return render_template("entries.html", entries=entry_query.order_by(LogbookEntry.date.desc()).all(), query=query,
                           today_iso=date.today().isoformat())


@main_bp.route("/entries/new", methods=["GET", "POST"])
@login_required
def create_entry():
    selected_date = request.args.get("date")
    form = LogbookEntryForm()
    if request.method == "GET":
        try:
            form.date.data = datetime.strptime(selected_date, "%Y-%m-%d").date() if selected_date else date.today()
        except ValueError:
            abort(404)
    if form.validate_on_submit():
        existing = LogbookEntry.query.filter_by(user_id=current_user.id, date=form.date.data).first()
        if existing:
            flash("A logbook entry already exists for this date.", "warning")
            return redirect(url_for("main.edit_entry", entry_id=existing.id))
        entry = LogbookEntry(user=current_user, date=form.date.data, title=form.title.data.strip(),
                             description=clean_description(form.description.data))
        try:
            save_activities(entry)
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("entry_form.html", form=form, entry=None, rows=submitted_rows())
        db.session.add(entry)
        db.session.commit()
        flash("Logbook entry created.", "success")
        return redirect(url_for("main.view_entry", entry_id=entry.id))
    rows = submitted_rows() if request.method == "POST" else entry_rows(None)
    return render_template("entry_form.html", form=form, entry=None, rows=rows)


@main_bp.route("/entries/<int:entry_id>")
@login_required
def view_entry(entry_id):
    return render_template("entry_detail.html", entry=owned_entry(entry_id))


@main_bp.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry = owned_entry(entry_id)
    form = LogbookEntryForm(obj=entry)
    if form.validate_on_submit():
        existing = LogbookEntry.query.filter(
            LogbookEntry.user_id == current_user.id,
            LogbookEntry.date == form.date.data,
            LogbookEntry.id != entry.id,
        ).first()
        if existing:
            flash("A logbook entry already exists for this date.", "warning")
            return redirect(url_for("main.edit_entry", entry_id=existing.id))
        entry.date, entry.title = form.date.data, form.title.data.strip()
        entry.description = clean_description(form.description.data)
        try:
            save_activities(entry)
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("entry_form.html", form=form, entry=entry, rows=submitted_rows())
        db.session.commit()
        flash("Logbook entry updated.", "success")
        return redirect(url_for("main.view_entry", entry_id=entry.id))
    rows = submitted_rows() if request.method == "POST" else entry_rows(entry)
    return render_template("entry_form.html", form=form, entry=entry, rows=rows)


@main_bp.post("/entries/<int:entry_id>/delete")
@login_required
def delete_entry(entry_id):
    entry = owned_entry(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Logbook entry deleted.", "info")
    return redirect(url_for("main.entries"))


@main_bp.post("/entries/<int:entry_id>/activities/reorder")
@login_required
def reorder_activities(entry_id):
    entry = owned_entry(entry_id)
    ids = request.get_json(silent=True, force=True).get("activity_ids", [])
    activities = {activity.id: activity for activity in entry.activities}
    if set(ids) != set(activities):
        return jsonify({"error": "Invalid activity order."}), 400
    for order, activity_id in enumerate(ids):
        activities[activity_id].display_order = order
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/calendar")
@login_required
def calendar_view():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if not 1 <= month <= 12:
        abort(404)
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    existing = {entry.date: entry for entry in current_user.logbook_entries.filter(
        db.extract("year", LogbookEntry.date) == year, db.extract("month", LogbookEntry.date) == month
    ).all()}
    previous_month = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return render_template("calendar.html", weeks=weeks, entries_by_date=existing, year=year, month=month,
                           month_label=calendar.month_name[month], previous_month=previous_month,
                           next_month=next_month, today=today)


@main_bp.route("/entries/<int:entry_id>/print")
@login_required
def print_entry(entry_id):
    return render_template("print_entry.html", entry=owned_entry(entry_id))


@main_bp.route("/entries/<int:entry_id>/export.pdf")
@login_required
def export_pdf(entry_id):
    entry = owned_entry(entry_id)
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm,
                                 topMargin=1.6 * cm, bottomMargin=1.6 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph("INTERNSHIP LOGBOOK", styles["Title"]), Spacer(1, 10),
             Paragraph(f"<b>Date:</b> {entry.date.strftime('%d %B %Y')}", styles["BodyText"]),
             Paragraph(f"<b>Title:</b> {bleach.clean(entry.title)}", styles["BodyText"]), Spacer(1, 12)]
    table_data = [["Start", "End", "Activity"]] + [
        [a.start_time.strftime("%H:%M"), a.end_time.strftime("%H:%M"), a.activity] for a in entry.activities
    ]
    table = Table(table_data, colWidths=[2.4 * cm, 2.4 * cm, 11.4 * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.grey),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story += [table, Spacer(1, 16), Paragraph("Remarks", styles["Heading2"]),
              Paragraph(bleach.clean(entry.description, tags=[]).replace("\n", "<br/>"), styles["BodyText"])]
    document.build(story)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="logbook-{entry.date.isoformat()}.pdf"'
    return response
