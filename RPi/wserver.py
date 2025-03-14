from flask import Flask
from flask import render_template, request, redirect, url_for, session
from flask import jsonify
from flask import Response

import db
import hike

app = Flask(__name__, template_folder=".")
hdb = db.HubDatabase()


@app.route('/')
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


@app.route('/home')
def get_home():
    if "username" not in session:
        return redirect(url_for("get_login"))
    
    username = session["username"]
    sessions = hdb.get_sessions(username, password) 
    return render_template('home.html', sessions=sessions)

@app.route('/logout')
def get_logout():
    session.pop("username", None)
    return redirect(url_for("get_login"))


'''
@app.route('/sessions')
def get_sessions():
    sessions = hdb.get_sessions() 
    sessions = list(map(lambda s: hike.to_list(s), sessions))
    print(sessions)
    return jsonify(sessions)


@app.route('/<id>')
def get_session_by_id(id):
    session = hdb.get_session(id)
    return jsonify(hike.to_list(session))

@app.route('/<id>/delete')
def delete_session(id):
    hdb.delete(id)
    print(f'DELETED SESSION WITH ID: {id}')
    return Response(status=202)
'''

if __name__ == "__main__":
    #app.run('10.100.62.114', port=5006, debug=True)
    app.run('192.168.91.60', port=5001, debug=True)

