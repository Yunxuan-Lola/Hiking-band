from flask import Flask
from flask import render_template
from flask import jsonify
from flask import Response

import db
import hike

app = Flask(__name__, template_folder=".")
hdb = db.HubDatabase()

@app.route('/')
def get_home():
    sessions = hdb.get_sessions() 
    return render_template('home.html', sessions=sessions)

'''
@app.route('/sessions')
def get_sessions():
    sessions = hdb.get_sessions() 
    sessions = list(map(lambda s: hike.to_list(s), sessions))
    print(sessions)
    return jsonify(sessions)
'''

@app.route('/<id>')
def get_session_by_id(id):
    session = hdb.get_session(id)
    return jsonify(hike.to_list(session))

@app.route('/<id>/delete')
def delete_session(id):
    hdb.delete(id)
    print(f'DELETED SESSION WITH ID: {id}')
    return Response(status=202)

if __name__ == "__main__":
    app.run('10.100.62.114', port=5005, debug=True)
    #get_session_by_id(20250310151314193420)

