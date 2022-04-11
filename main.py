from flask import Flask
from google.cloud import datastore
import google.oauth2.id_token
from flask import Flask, render_template, request
from google.auth.transport import requests
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="C:/Users/pnral/AppData/Local/Google/Cloud SDK/Cloud " \
                                             "Examples/examples-342715-be5d9216fda2.json "

app = Flask(__name__)

datastore_client = datastore.Client()

firebase_request_adapter = requests.Request()


@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
        except ValueError as exc:
            error_message = str(exc)

    return render_template('index.html', user_data=claims, error_message=error_message)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)