import random
from google.cloud import datastore
import google.oauth2.id_token
from flask import Flask, render_template, request
from google.auth.transport import requests
import os

from werkzeug.utils import redirect

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
        'task_list': [],
        'invited_users': []
    })
    datastore_client.put(entity)
    return id


def createTask(claims, board_id, name, due_date, user, finish_date):
    id = random.getrandbits(63)
    #board_key = datastore_client.key('Board', board_id)
    entity_key = datastore_client.key('Tasks', id)
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'task_name': name,
        'deadline': due_date,
        'statue': 0,
        'assigned_user': user,
        'finish_date': finish_date
    })
    datastore_client.put(entity)
    return id


def retrieveTasks(board_info):
    task_ids = board_info['task_list']
    task_keys = []
    for i in range(len(task_ids)):
        task_keys.append(datastore_client.key('Tasks', task_ids[i]))
    task_list = datastore_client.get_multi(task_keys)
    return task_list


def addTaskToBoard(board_info, id):
    print(board_info)
    task_keys = board_info['task_list']
    task_keys.append(id)
    board_info.update({
        'task_list': task_keys
    })
    datastore_client.put(board_info)


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


def retrieve_all_users():
    query = datastore_client.query(kind='UserInfo')
    all_keys = list(query.fetch())
    return all_keys


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


@app.route('/home')
def home():
    return redirect('/')


@app.route('/add_user/<int:id>')
def addUser_page(id):
    id_token = request.cookies.get("token")
    claims = None
    error_message = None
    users = retrieve_all_users()

    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('addUser.html', users=users, user_data=claims, error_message=error_message, id=id, add=True)


@app.route('/add_task/<int:id>')
def addtask_page(id):
    id_token = request.cookies.get("token")
    claims = None
    error_message = None

    users = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            users = entity['invited_users']

        except ValueError as exc:
            error_message = str(exc)
    return render_template('addTask.html', user_data=claims, users=users, error_message=error_message, id=id, add=True)


@app.route('/add_task/<int:id>', methods=['POST'])
def addTask(id):
    id_token = request.cookies.get("token")
    claims = None
    tasks = []
    invite_users = []
    board_tasks = []
    error_message = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            chckbx = request.form.getlist('checkboxtask')
            print(chckbx)
            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            invited_users = entity['invited_users']

            if len(chckbx)!=1:
                return render_template('addTask.html', users=invited_users, user_data=claims,
                                       error_message=error_message, id=id, add=False)

            task_id = createTask(claims, id, request.form['name'], request.form['deadline'], chckbx[0])

            tasks = entity['task_list']
            tasks.append(task_id)
            entity.update({
                'task_list': tasks
            })
            datastore_client.put(entity)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)

        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks, result=result, id=id)


@app.route('/complete_tasks<int:id>', methods=['POST'])
def completeTasks():
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


@app.route('/board-page<int:id>')
def board_page(id):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)

        except ValueError as exc:
            error_message = str(exc)
    entity_key = datastore_client.key('Board', id)
    result = datastore_client.get(entity_key)
    board_tasks = retrieveTasks(result)
    print(board_tasks)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks , result=result, id=id)


@app.route('/invite_users/<int:id>', methods=['POST'])
def inviteUser(id):
    id_token = request.cookies.get("token")
    claims = None
    board_tasks = []
    error_message = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            chckbx = request.form.getlist('checkboxes')
            print(chckbx)
            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            invited_users = entity['invited_users']

            for user in chckbx:
                    exists = invited_users.count(user)
                    if exists != 0:
                        users = retrieve_all_users()
                        return render_template('addUser.html', users=users, user_data=claims, id=id, add=False)
            for user in chckbx:
                invited_users.append(user)
                user_key = datastore_client.key('UserInfo', user)
                userinfo = datastore_client.get(user_key)
                print(userinfo)
                addBoardToUser(userinfo, id)
            entity.update({
                'invited_users': invited_users
            })
            datastore_client.put(entity)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks, result=result, id=id)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
