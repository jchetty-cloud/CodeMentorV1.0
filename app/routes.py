"""
app/routes.py
All URL routes for CodeMentor.

Imports come from the app package:
  - app        → the Flask application instance
  - app.db     → SQLAlchemy instance
  - app.csrf   → CSRFProtect instance (for @csrf.exempt on JSON endpoints)
  - app.client → Anthropic client
  - app.models → User, TutorSession
  - app.forms  → LoginForm, RegisterForm
"""

from flask import render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime, timezone, timedelta
import anthropic

from app import app, db, csrf, client
from app.models import User, TutorSession, TutorFollowUp
from app.forms import LoginForm, RegisterForm

import csv
import io
from flask import make_response


# ── Prompt engineering ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are CodeMentor, a patient and encouraging Python coding tutor for university students.

Your core principles:
- NEVER just give the full answer. Guide students to discover solutions themselves.
- Use the Socratic method: ask questions that lead students to think.
- Celebrate effort and progress, not just correct answers.
- Explain concepts clearly with relatable analogies.
- Adapt your language to the student's apparent level.
- When you see Python-specific concepts, use Python terminology and idioms.

When analysing code:
- First acknowledge what they've done WELL before addressing issues.
- Identify the single most important issue to fix (don't overwhelm).
- Ask a guiding question rather than stating the fix outright.
- If there are multiple issues, address them one at a time.

Format your responses using Markdown (headers, bullet points, code blocks) for readability.
Use ```python for all Python code examples.

Tone: warm, encouraging, like a knowledgeable friend — not a textbook.
"""

TUTOR_ACTIONS = {
    "explain": {
        "label": "Explain My Code",
        "icon": "🔍",
        "prompt": """The student wants you to explain what their {language} code does.

Walk through it step-by-step in plain English. Use an analogy if helpful.
Highlight any interesting Python features or patterns you spot.
End with: "What part would you like to explore further?"

Student's code:
```{language}
{code}
```
Additional context: {context}"""
    },
    "debug": {
        "label": "Help Me Debug",
        "icon": "🐛",
        "prompt": """The student needs help debugging their {language} code.

1. First, affirm something correct about their approach.
2. Ask them: "What do you *expect* this code to do, and what is it actually doing?"
3. Give ONE guiding hint — a question or observation — to help them spot the bug.
Do NOT fix the code for them. Do NOT show the corrected code.

Student's code:
```{language}
{code}
```
Student's description: {context}"""
    },
    "improve": {
        "label": "Suggest Improvements",
        "icon": "✨",
        "prompt": """The student wants to improve their {language} code.

Review and suggest improvements in this priority order:
1. Pythonic style (list comprehensions, f-strings, context managers, etc.)
2. Readability (naming, comments, structure, PEP 8)
3. One stretch goal to level them up

Frame each suggestion as a question: "What do you think would happen if you..."
Keep it to 2-3 suggestions maximum. Show brief before/after snippets only where essential.

Student's code:
```{language}
{code}
```
Student's notes: {context}"""
    },
    "concept": {
        "label": "Teach the Concept",
        "icon": "📚",
        "prompt": """The student wants to understand the underlying concept in their {language} code.

Identify the key Python concept(s) and teach them:
1. Clear, simple definition
2. Real-world analogy
3. How it appears in their specific code
4. A tiny alternative example of the concept

Student's code:
```{language}
{code}
```
Specific concept they're asking about: {context}"""
    },
    "quiz": {
        "label": "Quiz Me",
        "icon": "🎯",
        "prompt": """Create a short quiz (3 questions) about the student's {language} code.

- Q1: Comprehension — what does a specific line/function do?
- Q2: Prediction — what would happen if they changed something?
- Q3: Application — how would they modify it to do something new?

Make questions specific to THEIR code. Use Python-appropriate scenarios.
Tell them to answer in the chat for feedback.

Student's code:
```{language}
{code}
```
Topic focus: {context}"""
    },
    "review": {
        "label": "Code Review",
        "icon": "📋",
        "prompt": """Do a structured code review of the student's {language} code as a senior Pythonista reviewing a junior's work.

Use this format:
✅ **What's Working Well** (specific and genuine)
🤔 **Questions to Consider** (make them think)
💡 **One Key Suggestion** (most impactful change, with reasoning)
🐍 **Pythonic Tip** (one Python-specific improvement)
🚀 **Next Steps** (what to try next)

Be encouraging. This is a learning environment.

Student's code:
```{language}
{code}
```
Student's context: {context}"""
    }
}

LANGUAGE_DETECT_PROMPT = """Detect the programming language of this code. \
Reply with ONLY a single lowercase word. \
Choose from: python, javascript, java, html, css, cpp, csharp, sql, bash, other.

Code:
{code}"""


# ── Auth decorators ────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = db.session.get(User, session["user_id"])
        if not user or user.role != "teacher":
            flash("Teacher access only.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# ── Helper: language detection ─────────────────────────────────────────────────

def detect_language(code: str) -> str:
    """Ask Claude to identify the programming language. Falls back to 'python'."""
    try:
        msg = client.messages.create(
            #model="claude-sonnet-4-20250514",
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": LANGUAGE_DETECT_PROMPT.format(code=code[:500])
            }]
        )
        lang = msg.content[0].text.strip().lower()
        allowed = {"python", "javascript", "java", "html", "css",
                   "cpp", "csharp", "sql", "bash", "other"}
        return lang if lang in allowed else "python"
    except Exception:
        return "python"


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(form.password.data):
            session["user_id"] = user.id
            session["role"]    = user.role
            session["name"]    = user.display_name
            return redirect(url_for("dashboard") if user.role == "teacher" else url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username     = form.username.data.strip().lower(),
            display_name = form.display_name.data.strip(),
            cohort       = form.cohort.data.strip(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Student routes ─────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    actions = [
        {"key": k, "label": v["label"], "icon": v["icon"]}
        for k, v in TUTOR_ACTIONS.items()
    ]
    user = db.session.get(User, session["user_id"])
    recent = (TutorSession.query
              .filter_by(user_id=user.id)
              .order_by(TutorSession.created_at.desc())
              .limit(5).all())
    return render_template("index.html", actions=actions, user=user, recent=recent)


@app.route("/history")
@login_required
def history():
    user = db.session.get(User, session["user_id"])
    sessions = (TutorSession.query
                .filter_by(user_id=user.id)
                .order_by(TutorSession.created_at.desc())
                .all())
    return render_template("history.html", user=user, sessions=sessions)


@app.route("/history/<int:session_id>")
@login_required
def history_detail(session_id):
    ts = TutorSession.query.get_or_404(session_id)
    if ts.user_id != session["user_id"]:
        flash("Access denied.", "error")
        return redirect(url_for("history"))
    return render_template("history_detail.html", ts=ts)


# ── Tutor API (JSON — CSRF exempt, protected by session login) ─────────────────

@app.route("/api/detect-language", methods=["POST"])
@csrf.exempt
@login_required
def api_detect_language():
    data = request.get_json()
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"language": "python"})
    return jsonify({"language": detect_language(code)})


@app.route("/api/tutor", methods=["POST"])
@csrf.exempt
@login_required
def api_tutor():
    data     = request.get_json()
    code     = data.get("code", "").strip()
    action   = data.get("action", "explain")
    context  = data.get("context", "").strip() or "No additional context provided."
    language = data.get("language", "python")

    if not code:
        return jsonify({"error": "Please paste some code first!"}), 400
    if action not in TUTOR_ACTIONS:
        return jsonify({"error": "Unknown action."}), 400

    user_prompt = TUTOR_ACTIONS[action]["prompt"].format(
        code=code, context=context, language=language
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        response_text = message.content[0].text

        ts = TutorSession(
            user_id      = session["user_id"],
            action       = action,
            language     = language,
            code_snippet = code[:2000],
            context      = context[:500],
            response     = response_text,
        )
        db.session.add(ts)
        db.session.commit()

        return jsonify({"response": response_text, "action": action,
                        "language": language, "session_id": ts.id})

    except anthropic.APIError as e:
        return jsonify({"error": f"API error: {str(e)}"}), 500

@app.route("/api/followup", methods=["POST"])
@csrf.exempt
@login_required
def api_followup():

    data = request.get_json() or {}

    history = data.get("history", [])
    question = data.get("question", "").strip()
    code = data.get("code", "")
    session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "Please type a question."}), 400

    # Check that the original tutoring session belongs to this student
    ts = db.session.get(TutorSession, session_id)

    if not ts or ts.user_id != session["user_id"]:
        return jsonify({"error": "Invalid tutoring session."}), 403

    if not isinstance(history, list):
        return jsonify({"error": "Invalid conversation history."}), 400

    messages = []

    for item in history[-20:]:
        if (
                not isinstance(item, dict)
                or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str)
        ):
            return jsonify({"error": "Invalid conversation history."}), 400

        messages.append({
            "role": item["role"],
            "content": item["content"][:5000]
        })

    prompt_question = question

    if code and not messages:
        prompt_question = (
            f"Regarding this code:\n```python\n{code}\n```\n\n{question}"
        )

    messages.append({"role": "user", "content": prompt_question})

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        response_text = message.content[0].text

        # Save the complete follow-up exchange
        exchange = TutorFollowUp(
            tutor_session_id=ts.id,
            student_question=question,
            mentor_response=response_text
        )

        db.session.add(exchange)

        # Maintain the existing follow-up counter
        ts.followups = (ts.followups or 0) + 1

        db.session.commit()

        return jsonify({"response": response_text})

    except anthropic.APIError as e:
        db.session.rollback()
        return jsonify({"error": f"API error: {str(e)}"}), 500

# ── Teacher dashboard ──────────────────────────────────────────────────────────

@app.route("/dashboard")
@teacher_required
def dashboard():
    cohorts = [c[0] for c in
               db.session.query(User.cohort).filter_by(role="student").distinct().all()]
    students = User.query.filter_by(role="student").order_by(
        User.cohort, User.display_name).all()

    total_sessions = TutorSession.query.count()
    total_students = User.query.filter_by(role="student").count()

    action_counts = {a: TutorSession.query.filter_by(action=a).count()
                     for a in TUTOR_ACTIONS}
    lang_counts   = {row[0]: row[1] for row in
                     db.session.query(TutorSession.language,
                                      db.func.count(TutorSession.id))
                     .group_by(TutorSession.language).all()}

    recent_sessions = (TutorSession.query
                       .order_by(TutorSession.created_at.desc())
                       .limit(20).all())

    return render_template(
        "dashboard.html",
        cohorts=cohorts,
        students=students,
        total_sessions=total_sessions,
        total_students=total_students,
        action_counts=action_counts,
        lang_counts=lang_counts,
        recent_sessions=recent_sessions,
        tutor_actions=TUTOR_ACTIONS,
    )


@app.route("/dashboard/student/<int:student_id>")
@teacher_required
def student_detail(student_id):
    student  = User.query.get_or_404(student_id)
    sessions = (TutorSession.query
                .filter_by(user_id=student_id)
                .order_by(TutorSession.created_at.desc())
                .all())
    action_counts = {a: sum(1 for s in sessions if s.action == a)
                     for a in TUTOR_ACTIONS}
    return render_template(
        "student_detail.html",
        student=student,
        sessions=sessions,
        action_counts=action_counts,
        tutor_actions=TUTOR_ACTIONS,
    )


@app.route("/dashboard/api/stats")
@teacher_required
def dashboard_api_stats():
    cohort = request.args.get("cohort", "all")
    q = TutorSession.query
    if cohort != "all":
        q = q.join(User).filter(User.cohort == cohort)

    action_data = {a: q.filter(TutorSession.action == a).count()
                   for a in TUTOR_ACTIONS}
    lang_data   = {row[0]: row[1] for row in
                   db.session.query(TutorSession.language,
                                    db.func.count(TutorSession.id))
                   .group_by(TutorSession.language).all()}

    today = datetime.now(timezone.utc).date()
    daily = {
        (today - timedelta(days=i)).strftime("%d %b"): 0
        for i in range(13, -1, -1)
    }
    for ts in q.all():
        day_str = ts.created_at.strftime("%d %b")
        if day_str in daily:
            daily[day_str] += 1

    return jsonify({"action_data": action_data, "lang_data": lang_data,
                    "daily_activity": daily})

@app.route("/dashboard/export/conversations.csv")
@teacher_required
def export_conversations():

    output = io.StringIO()

    writer = csv.writer(output)

    # CSV column headings
    writer.writerow([
        "student_id",
        "session_id",
        "session_date",
        "tutoring_mode",
        "language",
        "interaction_number",
        "interaction_type",
        "student_input",
        "ai_response",
        "interaction_date"
    ])

    # Create consistent pseudonymous student IDs
    students = (
        User.query
        .filter_by(role="student")
        .order_by(User.id)
        .all()
    )

    student_codes = {
        student.id: f"STUDENT_{i:03d}"
        for i, student in enumerate(students, start=1)
    }

    # Retrieve all tutoring sessions
    sessions = (
        TutorSession.query
        .order_by(TutorSession.created_at, TutorSession.id)
        .all()
    )

    for ts in sessions:

        student_id = student_codes.get(
            ts.user_id, "UNKNOWN"
        )

        # Initial interaction
        writer.writerow([
            student_id,
            ts.id,
            ts.created_at,
            ts.action,
            ts.language,
            0,
            "initial_submission",
            ts.code_snippet,
            ts.response,
            ts.created_at
        ])

        # Subsequent student–AI exchanges
        followups = sorted(
            ts.followup_exchanges,
            key=lambda f: (f.created_at, f.id)
        )

        for number, exchange in enumerate(followups, start=1):

            writer.writerow([
                student_id,
                ts.id,
                ts.created_at,
                ts.action,
                ts.language,
                number,
                "followup",
                exchange.student_question,
                exchange.mentor_response,
                exchange.created_at
            ])

    # Prepare downloadable CSV
    response = make_response("\ufeff" + output.getvalue())

    response.headers["Content-Type"] = (
        "text/csv; charset=utf-8"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=codementor_research_data.csv"
    )

    return response