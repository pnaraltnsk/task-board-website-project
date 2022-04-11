import random
from google.cloud import datastore
import google.oauth2.id_token
from flask import Flask, render_template, request
from google.auth.transport import requests
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="C:/Users/pnral/AppData/Local/Google/Cloud SDK/Assignment2/assignment2-346918-448cc0bc3739.json "

app = Flask(__name__)

datastore_client = datastore.Client()

firebase_request_adapter = requests.Request()


def retrieveUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    return entity


def createUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'name': claims['name'],
        'board_list': []
    })
    datastore_client.put(entity)


def createBoard(claims, boardName):
    id = random.getrandbits(63)
    entity_key = datastore_client.key('Board', id)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'creator_name': claims['name'],
        'board_name': boardName,
        'task_list': []
    })
    datastore_client.put(entity)
    return id


def retrieveBoard(user_info):
    board_ids = user_info['board_list']
    board_keys = []
    for i in range(len(board_ids)):
        board_keys.append(datastore_client.key('Board', board_ids[i]))
    board_list = datastore_client.get_multi(board_keys)
    return board_list


def addBoardToUser(user_info, id):
    print(user_info)
    board_keys = user_info['board_list']
    board_keys.append(id)
    user_info.update({
        'board_list': board_keys
    })
    datastore_client.put(user_info)


# these functions below will be for rendering templates

@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    boards = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            if user_info is None:
                createUserInfo(claims)
                user_info = retrieveUserInfo(claims)
            boards = retrieveBoard(user_info)
        except ValueError as exc:
            error_message = str(exc)

    return render_template('index.html', user_data=claims, user_info=user_info,
                           boards=boards, error_message=error_message)


@app.route('/add_board')
def createBoardPage():
    return render_template('addBoard.html', add=True)


@app.route('/create_board', methods=['POST'])
def create_board():
    id_token = request.cookies.get("token")
    claims = None
    boards = None
    error_message = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            # boards = retrieveBoard(user_info) for car in boards: if car['obj_name'] == request.form['obj_name'] and
            # car['manufacturer'] == request.form['manufacturer'] \ and car['year'] == request.form['year']: return
            # render_template('addEV.html', add=False)

            id = createBoard(
                claims,
                str(request.form['board_name'])
            )
            addBoardToUser(user_info, id)
            boards = retrieveBoard(user_info)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, error_message=error_message,
                           boards=boards)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
