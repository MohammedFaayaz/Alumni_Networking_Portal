from flask import (
    Flask, render_template, render_template_string, request, redirect,
    url_for, flash, jsonify, session
)
import subprocess
import re
from transformers import pipeline
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from flask_cors import CORS



app = Flask(__name__)

# ---------------- APP CONFIG ----------------
app.secret_key = 'secretkey'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'fayaz28'
app.config['MYSQL_DB'] = 'alumnidb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL AFTER config
mysql = MySQL(app)

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)

# # ---------------- AI MODEL (FLAN-T5) ----------------
# chat_model = None
# try:
#     chat_model = pipeline("text2text-generation", model="google/flan-t5-small")
#     app.logger.info("Loaded flan-t5-small model.")
# except Exception as e:
#     chat_model = None
#     app.logger.warning("Could not load flan-t5-small model. AI fallback will be limited. Error: %s", e)

# def generate_ai_reply(prompt: str) -> str:
#     """Generate a concise reply using local model if available."""
#     if not prompt:
#         return "Please provide a message."
#     if chat_model is None:
#         # Simple heuristic fallback if model isn't available
#         return ("(AI unavailable) I can search alumni. Try asking 'Who works at TCS?' "
#                 "or 'Show alumni at Google'.")
#     try:
#         result = chat_model(prompt, max_length=200, do_sample=True)
#         return result[0].get('generated_text', '').strip()
#     except Exception as e:
#         app.logger.exception("AI generation failed")
#         return "Sorry — couldn't generate an AI reply right now."

# # ---------------- OLLAMA (optional) ----------------
# def chat_with_ollama(prompt: str) -> str:
#     """Run Ollama if installed; otherwise return informative message."""
#     try:
#         # Note: adjust the command if your Ollama usage differs
#         result = subprocess.run(
#             ["ollama", "run", "gemma3:1b", prompt],
#             capture_output=True,
#             text=True,
#             timeout=20
#         )
#         if result.returncode != 0:
#             app.logger.warning("Ollama returned non-zero exit: %s", result.stderr)
#             return "Ollama error: " + (result.stderr.strip() or "non-zero exit")
#         return result.stdout.strip() or "Ollama returned no output."
#     except FileNotFoundError:
#         return "Ollama not installed or not in PATH. Install Ollama to use this feature."
#     except Exception as e:
#         app.logger.exception("Ollama call failed")
#         return f"Ollama error: {e}"
# def generate_ai_reply(prompt: str) -> str:
#     full_prompt = f"""
#     You are an alumni networking assistant. Be detailed, polite, and give useful advice.
#     Student message: {prompt}
#     """
#     if chat_model:
#         result = chat_model(full_prompt, max_length=300, do_sample=True)
#         return result[0].get('generated_text', '').strip()
#     return "(AI unavailable)"

# ---------------- DB HELPERS ----------------
def get_cursor():
    """Return a new DB cursor (DictCursor). Remember to close it after use."""
    return mysql.connection.cursor()

def search_alumni_by_company(company: str):
    """Return rows (list of dicts) for alumni matched by company (safe)."""
    cursor = get_cursor()
    try:
        sql = "SELECT id, name, email, job_title, location, company FROM alumniinfo WHERE company LIKE %s"
        cursor.execute(sql, (f"%{company}%",))
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()

# # ---------------- NLP HELPERS ----------------
# # improved company extraction (handles: at/in/from/with/company: X)
# COMPANY_RE = re.compile(r"(?:at|in|from|with)\s+([A-Z][\w&.\- ]{1,80})")
# COMPANY_COLON_RE = re.compile(r"company\s*[:\-]\s*([A-Za-z0-9&.\- ]+)", re.I)

# def extract_company_name(message: str):
#     if not message:
#         return None
#     # search for patterns like "at Google" or "in Microsoft"
#     m = COMPANY_RE.search(message)
#     if m:
#         return m.group(1).strip()
#     m2 = COMPANY_COLON_RE.search(message)
#     if m2:
#         return m2.group(1).strip()
#     # fallback: look for last capitalized token (not great, but a fallback)
#     tokens = re.findall(r"[A-Z][a-zA-Z0-9&.\-]{1,40}", message)
#     if tokens:
#         return tokens[-1]
#     return None

# # ---------------- GLOBAL ERROR HANDLER (prevent resets) ----------------
# @app.errorhandler(Exception)
# def handle_exception(e):
#     app.logger.exception("Unhandled exception: %s", e)
#     # if AJAX/JSON expected, return JSON
#     if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
#         return jsonify({"error": "Server error", "details": str(e)}), 500
#     # otherwise render a simple page (you can improve)
#     flash("An internal server error occurred.")
#     return redirect(url_for('index'))

# ---------------- ROUTES ----------------
@app.route('/')
def root():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

# # ---------------- Ollama chat route (optional) ----------------
# @app.route('/chatbot')
# def chatbot_page():
#     return render_template('chatbot.html')

# @app.route('/chat', methods=['POST'])
# def chat():
#     # Ollama-powered endpoint (safe wrapped)
#     data = request.get_json(silent=True) or {}
#     user_message = (data.get("message") or "").strip()
#     if not user_message:
#         return jsonify({"response": "Please enter a message."}), 400
#     reply = chat_with_ollama(user_message)
#     return jsonify({"response": reply})

# # ---------------- WhatsApp-like chat (alumni search + AI fallback) ----------------
# @app.route('/chatb')
# def chatb():
#     # Serve local chatb.html file contents to avoid file:// issues.
#     # Make sure chatb.html exists in the same folder as app.py
#     try:
#         with open("chatb.html", "r", encoding="utf-8") as f:
#             content = f.read()
#         return render_template_string(content)
#     except FileNotFoundError:
#         return "<h3>chatb.html not found. Please add the chatb.html file in the project folder.</h3>"

# ---------------- ALUMNI INFO PAGES ----------------
@app.route('/displayall')
def displayall():
    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM alumniinfo")
        alumni_data = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('displayall.html', alumni=alumni_data)

@app.route('/addalumini')
def addalumini():
    return render_template('addalumini.html')

@app.route('/submit_alumni', methods=['POST'])
def submit_alumni():
    name = request.form.get('name')
    email = request.form.get('email')
    grad_yr = request.form.get('grad_yr')
    company = request.form.get('company')
    job_title = request.form.get('job_title')
    location = request.form.get('location')

    cursor = get_cursor()
    try:
        cursor.execute(
            "INSERT INTO alumniinfo (name, email, grad_yr, company, job_title, location) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, email, grad_yr, company, job_title, location)
        )
        mysql.connection.commit()
    finally:
        cursor.close()

    flash('Your information is stored. THANK YOU FOR HELPING YOUR JUNIORS')
    return redirect(url_for('login'))

# ---------------- ALUMNI LOGIN ----------------
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/loginn', methods=['POST'])
def loginn():
    email = request.form.get('email')
    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM alumniinfo WHERE email = %s", (email,))
        alumni_profile = cursor.fetchall()
    finally:
        cursor.close()

    if not alumni_profile:
        flash("No alumni found with that email. Please register first.")
        return redirect(url_for('addalumini'))

    session['email'] = email
    return render_template('profile.html', alumni_results=alumni_profile)

@app.route('/profile')
def profile():
    return render_template('profile.html')

# ---------------- STUDENT REGISTRATION / LOGIN / PROFILE ----------------
@app.route('/addstudent', methods=['GET', 'POST'])
def addstudent():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')  # not stored in DB in your original design
        department = request.form.get('department')
        year = request.form.get('year')

        if not (name and email and password and department and year):
            flash("All fields are required.")
            return redirect(url_for('addstudent'))

        if not re.match(r"^[A-Za-z0-9._%+-]+@student\.tce\.edu$", email):
            flash("Only @student.tce.edu emails are allowed.")
            return redirect(url_for('addstudent'))

        cursor = get_cursor()
        try:
            cursor.execute("""
                INSERT INTO studentinfo (name, email, department, year)
                VALUES (%s, %s, %s, %s)
            """, (name, email, department, year))
            mysql.connection.commit()
        finally:
            cursor.close()

        flash("Student registered successfully! Please login.")
        return redirect(url_for('studentlogin'))

    return render_template('addstudent.html')

@app.route('/studentlogin', methods=['GET'])
def studentlogin():
    return render_template('studentlogin.html')

@app.route('/studentloginn', methods=['POST'])
def studentloginn():
    email = request.form.get('email')
    password = request.form.get('password')  # not used

    if not email:
        flash("Please enter your email.")
        return redirect(url_for('studentlogin'))

    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM studentinfo WHERE email = %s", (email,))
        student = cursor.fetchone()
    finally:
        cursor.close()

    if not student:
        flash("No student found with that email. Please register first.")
        return redirect(url_for('addstudent'))

    session['student_id'] = student['id']
    session['student_email'] = student['email']
    flash("Logged in successfully!")

    return redirect(url_for('studentprofile'))

@app.route('/studentprofile')
def studentprofile():
    if 'student_id' not in session:
        flash("Please login first.")
        return redirect(url_for('studentlogin'))

    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM studentinfo WHERE id = %s", (session['student_id'],))
        student = cursor.fetchone()
    finally:
        cursor.close()

    if not student:
        flash("Student not found.")
        return redirect(url_for('studentlogin'))

    return render_template('studentprofile.html', student=student)

@app.route('/studentlogout')
def studentlogout():
    session.pop('student_id', None)
    session.pop('student_email', None)
    flash("Logged out successfully.")
    return redirect(url_for('studentlogin'))

# ---------------- SEARCH ALUMNI ----------------
@app.route('/searchalumini')
def searchalumini():
    return render_template('search.html')

@app.route('/search', methods=['POST'])
def search():
    name = request.form.get('Name') or ""
    location = request.form.get('Location') or ""
    company = request.form.get('company') or ""
    grad_yr = request.form.get('grad_yr') or ""

    cursor = get_cursor()
    try:
        cursor.execute("""SELECT * FROM alumniinfo 
                          WHERE name LIKE %s AND location LIKE %s AND company LIKE %s AND grad_yr LIKE %s""",
                       ('%' + name + '%', '%' + location + '%', '%' + company + '%', '%' + grad_yr + '%'))
        alumni_results = cursor.fetchall()
    finally:
        cursor.close()

    return render_template('search_alumni.html', alumni_results=alumni_results)

# ---------------- STUDENT VIEW EVENTS ----------------
@app.route('/student/viewevents')
def student_viewevents():
    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
        events_list = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('student_viewevents.html', events_list=events_list)

# ---------------- STUDENT VIEW JOBS ----------------
@app.route('/student/viewjobs', methods=['GET', 'POST'])
def student_viewjobs():
    search_role = request.form.get("search_role", "") if request.method == "POST" else ""
    cursor = get_cursor()
    try:
        if search_role:
            cursor.execute(
                "SELECT * FROM job_opportunities WHERE job_role LIKE %s ORDER BY posted_date DESC",
                ('%' + search_role + '%',)
            )
        else:
            cursor.execute("SELECT * FROM job_opportunities ORDER BY posted_date DESC")
        jobs = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('student_viewjobs.html', jobs=jobs, search_role=search_role)

# ---------------- EVENTS ----------------
@app.route("/addevents", methods=["GET", "POST"])
def addevents():
    if "email" not in session:
        flash("Please log in to add events.")
        return redirect(url_for("login"))

    if request.method == "POST":
        alumni_email = session["email"]
        event_name = request.form.get("event_name")
        event_date = request.form.get("event_date")
        event_desc = request.form.get("event_desc")

        cursor = get_cursor()
        try:
            cursor.execute(
                "INSERT INTO events (alumni_email, event_name, event_date, event_desc) VALUES (%s, %s, %s, %s)",
                (alumni_email, event_name, event_date, event_desc)
            )
            mysql.connection.commit()
        finally:
            cursor.close()
        flash("Event added successfully!")
        return redirect(url_for("viewevents"))

    return render_template("addevents.html")

@app.route("/viewevents")
def viewevents():
    if "email" not in session:
        flash("Please log in to view your events.")
        return redirect(url_for("login"))

    alumni_email = session["email"]
    cursor = get_cursor()
    try:
        cursor.execute("SELECT event_name, event_date, event_desc FROM events WHERE alumni_email = %s", (alumni_email,))
        events_list = cursor.fetchall()
    finally:
        cursor.close()
    return render_template("viewevents.html", events_list=events_list)

# ---------------- JOB OPPORTUNITIES ----------------
@app.route("/addjob", methods=["GET", "POST"])
def addjob():
    if "email" not in session:
        flash("Please log in to post a job opportunity.")
        return redirect(url_for("login"))

    if request.method == "POST":
        posted_by = session["email"]
        job_title = request.form.get("job_title")
        company_name = request.form.get("company_name")
        location = request.form.get("location")
        job_role = request.form.get("job_role")
        description = request.form.get("description")
        application_link = request.form.get("application_link")
        contact_email = request.form.get("contact_email")

        cursor = get_cursor()
        try:
            cursor.execute("""
                INSERT INTO job_opportunities
                (posted_by, job_title, company_name, location, job_role, description, application_link, contact_email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (posted_by, job_title, company_name, location, job_role, description, application_link, contact_email))
            mysql.connection.commit()
        finally:
            cursor.close()
        flash("Job posted successfully!")
        return redirect(url_for("viewjobs"))

    return render_template("addjob.html")

@app.route("/viewjobs", methods=["GET", "POST"])
def viewjobs():
    if "email" not in session:
        flash("Please log in to view job opportunities.")
        return redirect(url_for("login"))

    search_role = request.form.get("search_role", "") if request.method == "POST" else ""
    cursor = get_cursor()
    try:
        if search_role:
            cursor.execute("SELECT * FROM job_opportunities WHERE job_role LIKE %s ORDER BY posted_date DESC", ('%' + search_role + '%',))
        else:
            cursor.execute("SELECT * FROM job_opportunities ORDER BY posted_date DESC")
        jobs = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('viewjobs.html', jobs=jobs, search_role=search_role)

# ---------------- MENTORSHIP ----------------
@app.route("/register_mentor", methods=["GET", "POST"])
def register_mentor():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        expertise = request.form["expertise"]
        bio = request.form["bio"]
        linkedin_link = request.form["linkedin"]
        available_slots = request.form["available_slots"]

        cursor = get_cursor()
        try:
            cursor.execute("""
                INSERT INTO mentors (name, email, expertise, bio, linkedin_link, available_slots)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, expertise, bio, linkedin_link, available_slots))
            mysql.connection.commit()
        finally:
            cursor.close()

        flash("Mentor registered successfully!", "success")
        return redirect(url_for("view_mentors"))

    return render_template("register_mentor.html")

@app.route("/view_mentors")
def view_mentors():
    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM mentors")
        mentors = cursor.fetchall()
    finally:
        cursor.close()
    return render_template("view_mentors.html", mentors=mentors)

@app.route("/request_mentorship/<int:mentor_id>", methods=["GET", "POST"])
def request_mentorship(mentor_id):
    if request.method == "POST":
        student_name = request.form["student_name"]
        student_email = request.form["student_email"]
        topic = request.form["topic"]
        preferred_date = request.form["preferred_date"]

        cursor = get_cursor()
        try:
            cursor.execute("""
                INSERT INTO mentorship_requests (student_name, student_email, mentor_id, topic, preferred_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_name, student_email, mentor_id, topic, preferred_date))
            mysql.connection.commit()
        finally:
            cursor.close()

        flash("Mentorship request sent!", "success")
        return redirect(url_for("view_mentors"))

    cursor = get_cursor()
    try:
        cursor.execute("SELECT * FROM mentors WHERE mentor_id=%s", (mentor_id,))
        mentor = cursor.fetchone()
    finally:
        cursor.close()
    return render_template("request_mentorship.html", mentor=mentor)

# @app.route("/mentor_dashboard/<int:mentor_id>", methods=["GET", "POST"])
# def mentor_dashboard(mentor_id):
#     cursor = get_cursor()
#     try:
#         if request.method == "POST":
#             request_id = request.form.get("request_id")
#             action = request.form.get("action")  # "Accepted" or "Rejected"

#             cursor.execute("""
#                 UPDATE mentorship_requests
#                 SET status = %s
#                 WHERE request_id = %s AND mentor_id = %s
#             """, (action, request_id, mentor_id))
#             mysql.connection.commit()
#             flash(f"Request has been {action.lower()} successfully!", "success")

#         cursor.execute("""
#             SELECT mr.request_id, mr.student_name, mr.student_email, mr.topic, 
#                    mr.preferred_date, mr.status, m.name AS mentor_name
#             FROM mentorship_requests mr
#             JOIN mentors m ON mr.mentor_id = m.mentor_id
#             WHERE mr.mentor_id = %s
#             ORDER BY mr.status, mr.preferred_date
#         """, (mentor_id,))
#         requests_data = cursor.fetchall()
#     finally:
#         cursor.close()

#     return render_template("mentor_dashboard.html", requests=requests_data)

# @app.route("/send_message", methods=["POST"])
# def send_message():
#     try:
#         data = request.get_json(silent=True) or {}
#         user_msg = (data.get("message") or "").strip()

#         if not user_msg:
#             return jsonify({"reply": "⚠️ Please type a message."}), 200

#         # Try extracting company name
#         company = extract_company_name(user_msg)

#         if company:
#             try:
#                 rows = search_alumni_by_company(company)
#             except Exception as db_err:
#                 app.logger.exception("Database query failed")
#                 return jsonify({"reply": f"⚠️ Database error: {db_err}"}), 200

#             if rows:
#                 lines = [
#                     f"- {r.get('name')} • {r.get('job_title') or '—'} • {r.get('location') or '—'} | {r.get('email')}"
#                     for r in rows
#                 ]
#                 reply = f"📌 Alumni at {company}:\n" + "\n".join(lines)
#                 return jsonify({"reply": reply}), 200
#             else:
#                 return jsonify({"reply": f"ℹ️ No alumni found in {company}."}), 200

#         # If no company found → AI fallback
#         ai_reply = generate_ai_reply(user_msg)
#         return jsonify({"reply": ai_reply}), 200

#     except Exception as e:
#         app.logger.exception("Unexpected error in /send_message")
#         return jsonify({"reply": f"⚠️ Server error: {str(e)}"}), 200


# ---------------- CONTACT ----------------
@app.route('/contact')
def contact():
    return render_template('contact.html')

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
