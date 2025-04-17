import os
from dotenv import load_dotenv
import psycopg2
import httpx
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify
)

# ─── Load Environment Variables ───────────────────────────────────────────────
load_dotenv()

# ─── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key    = os.environ["SUPER_SECRET_KEY"]
PROMPT_FILE      = os.environ["PROMPT_FILE"]
USE_TEST_SESSION = os.environ["USE_TEST_SESSION"].lower() in ("true", "1", "yes")

# ─── Database Configuration ───────────────────────────────────────────────────
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ["DB_PASS"]
DB_PORT = int(os.environ["DB_PORT"])

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )


# --- Authentication Routes ---
@app.route('/')
def index():
    return redirect(url_for('home') if 'user_id' in session else 'login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html')

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash("Email already registered.", "error")
                return render_template('register.html')

            cur.execute(
                "INSERT INTO users (email, username, password) VALUES (%s, %s, %s)",
                (email, username, password)
            )
            conn.commit()
            cur.close()
            conn.close()

            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print("Error:", e)
            flash("Server error. Try again.", "error")

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT id, username, password FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                user_id, username, db_password = user
                if password == db_password:
                    session['user_id'] = user_id
                    session['username'] = username
                    flash("Login successful!", "success")
                    return redirect(url_for('home'))
                else:
                    flash("Invalid password.", "error")
            else:
                flash("No account found. Please register.", "error")

        except Exception as e:
            print("Login error:", e)
            flash("Server error. Try again.", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


# --- Main Pages ---
@app.route('/home')
def home():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))
    return render_template('home.html', username=session.get('username', 'User'))


@app.route('/projects')
def projects():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))
    return render_template('projects.html', username=session.get('username'))


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))
    return render_template('settings.html', username=session.get('username'))


# --- OpenAI Session Integration ---
@app.route("/session", methods=["GET"])
def session_endpoint():
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_api_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500

    prompt_instructions = (
        "You are a persuasive and helpful vape shop employee. "
        "You also answer for all India products. "
        "You speak in Arabic with a friendly, respectful tone and as a female representative. "
        "Teach the client how to use the product, and when appropriate, ask if they would like to place an order or reserve it. "
        "Do not refer to any hardcoded inventory; rely on your existing knowledge base when helping the customer."
    )

    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r") as file:
            historical = file.read().strip()
            if historical:
                prompt_instructions += f"\n\nManager's Instructions:\n{historical}"

    with httpx.Client() as client:
        response = client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "verse",
                "instructions": prompt_instructions,
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {"type": "server_vad"}
            },
        )

        try:
            response_json = response.json()
        except Exception as e:
            print("Error parsing JSON:", e)
            return jsonify({"error": "Invalid response from OpenAI"}), 500

        client_secret = response_json.get("client_secret", {}).get("value")
        if not client_secret:
            return jsonify({"error": "No client_secret.value found in the /session response."}), 500

        return jsonify({"client_secret": {"value": client_secret}})


# --- Prompt Management ---
@app.route("/save_and_update_prompt", methods=["POST"])
def save_and_update_prompt():
    refined_text = request.json.get("refined_text")
    if refined_text:
        with open("refined_data.txt", "a") as file:
            file.write(refined_text + "\n")
        with open(PROMPT_FILE, "a") as prompt_file:
            prompt_file.write(refined_text + "\n")
        return jsonify({"status": "success", "message": "Prompt updated."})

    return jsonify({"status": "failed", "message": "No text received."}), 400


@app.route("/history", methods=["GET"])
def history():
    refined_history = ""
    if os.path.exists("refined_data.txt"):
        with open("refined_data.txt", "r") as f:
            refined_history = f.read()

    prompt_history = ""
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r") as f:
            prompt_history = f.read()

    return render_template("history.html", refined_history=refined_history, prompt_history=prompt_history)


@app.route("/reset_prompt", methods=["POST"])
def reset_prompt():
    prompt_deleted = False
    refined_deleted = False

    if os.path.exists(PROMPT_FILE):
        os.remove(PROMPT_FILE)
        prompt_deleted = True

    if os.path.exists("refined_data.txt"):
        os.remove("refined_data.txt")
        refined_deleted = True

    return jsonify({
        "status": "success",
        "message": "Prompt instructions and refined history cleared.",
        "prompt_deleted": prompt_deleted,
        "refined_deleted": refined_deleted
    })


# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)
