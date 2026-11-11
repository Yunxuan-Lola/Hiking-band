from flask import Flask
from flask import render_template, request, redirect, url_for, session
from flask import jsonify
from flask import Response

import db
import hike
import time
import os
import secrets

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get('HIKING_SECRET_KEY') or secrets.token_hex(32)
hdb = db.HubDatabase()


@app.route('/', methods=['GET', 'POST'])
def get_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = hdb.login_check(username, password)

        if user:
            session["username"] = username
            return redirect(url_for("get_home"))
        else:
            return "Invalid username or password."

    return render_template('login.html')


@app.route('/home')
def get_home():
    if "username" not in session:
        return redirect(url_for("get_login"))

    username = session["username"]
    sessions = hdb.get_sessions(username)
    return render_template('home.html', sessions=sessions, user=username)


@app.route('/home/logout')
def get_logout():
    session.pop("username", None)
    return redirect(url_for("get_login"))


@app.route('/api/session', methods=['POST'])
def post_session():
    if "username" not in session:
        return jsonify({"error": "login required"}), 401

    username = session["username"]

    data = request.get_json(force=True)
    s = hike.HikeSession()
    s.id = data.get("id")
    s.km = data.get("km")
    s.steps = data.get("steps")
    s.kcal = data.get("burnt_kcal")
    s.activity_mode = data.get("activity_mode", "unknown")
    s.activity_distribution = data.get("activity_distribution", {})

    hdb.save(s, username)
    return jsonify({"ok": True})


@app.route('/api/sessions_timing')
def sessions_timing():
    if "username" not in session:
        return jsonify({"error": "login required"}), 401

    username = session["username"]

    t0 = time.perf_counter()
    t_db0 = time.perf_counter()
    sessions_list = hdb.get_sessions(username)
    db_ms = (time.perf_counter() - t_db0) * 1000
    total_ms = (time.perf_counter() - t0) * 1000

    return jsonify({
        "user": username,
        "count": len(sessions_list),
        "db_ms": round(db_ms, 3),
        "total_ms": round(total_ms, 3),
    })


@app.route('/api/model_status')
def model_status():
    model_exists = os.path.exists(os.path.join(os.path.dirname(__file__), 'activity_model.pkl'))
    return jsonify({
        "model_exists": model_exists,
        "model_path": "activity_model.pkl"
    })


if __name__ == "__main__":
    hdb.migrate_database()
    app.run(os.environ.get('HIKING_BIND', '127.0.0.1'), port=5001, debug=False)
