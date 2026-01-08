from flask import Flask
from flask import render_template, request, redirect, url_for, session
from flask import jsonify
from flask import Response

import db
import hike

app = Flask(__name__, template_folder=".")
app.secret_key = "testsecretkey"
hdb = db.HubDatabase()

@app.route('/', methods=['GET', 'POST'])
def get_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
         
        user = hdb.login_check(username, password)
        
        if user:
            session["username"]=username
            return redirect(url_for("get_home"))
        else:
            return "Invalid username or password."
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def get_register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        ok = hdb.create_user(username, password)
        if ok:
            session["username"] = username
            return redirect(url_for("get_home"))
        else:
            return "User already exists."

    return render_template('register.html')

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
    s = hike.HikeSession(
        id=data["id"],
        km=data["km"],
        steps=data["steps"],
        kcal=data["burnt_kcal"],
    )
    ok = hdb.save(s, username)
    return jsonify({"ok": ok})


if __name__ == "__main__":
    app.run('10.100.46.99', port=5001, debug=True)

