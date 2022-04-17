import random
import datetime

from google.cloud import datastore
import google.oauth2.id_token
from flask import Flask, render_template, request
from google.auth.transport import requests
import os

from werkzeug.utils import redirect

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/pnral/AppData/Local/Google/Cloud SDK/Assignment2/assignment2-346918-448cc0bc3739.json "

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
    # board_key = datastore_client.key('Board', board_id)
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


def deleteTask(board, id):
    entity_key = datastore_client.key('Tasks', id)
    datastore_client.delete(entity_key)
    task_ids = board['task_list']
    task_ids.remove(id)
    board.update({
        'task_list': task_ids
    })
    datastore_client.put(board)


def counters(id):
    entity_key = datastore_client.key('Board', id)
    entity = datastore_client.get(entity_key)

    list = [0] * 4
    active_tasks = 0
    completed_tasks = 0
    total_tasks = 0
    completed_today = 0
    today = datetime.datetime.now().date()
    print(entity['task_list'])
    task_list = entity['task_list']
    for task_id in task_list:
        task_key = datastore_client.key('Tasks', task_id)
        task = datastore_client.get(task_key)
        if task['statue'] == 0:
            active_tasks += 1
        else:
            completed_tasks += 1
            print(completed_tasks)
            finish_date = datetime.datetime.date(task['finish_date'])
            if finish_date == today:
                completed_today += 1
    total_tasks = active_tasks + completed_tasks
    list[0] = active_tasks
    list[1] = completed_tasks
    list[2] = total_tasks
    list[3] = completed_today
    return list


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


def retrieveUncompletedTasks(tasks):
    c_tasks = []
    for task in tasks:
        if task['statue'] == 0:
            c_tasks.append(task)
    return c_tasks


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
                           boards=boards, error_message=error_message, bool=0)


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
    return render_template('addUser.html', users=users, user_data=claims, error_message=error_message, id=id, add=0)


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
            users.append(entity['email'])

        except ValueError as exc:
            error_message = str(exc)
    return render_template('addTask.html', user_data=claims, users=users, error_message=error_message, id=id, add=0)


@app.route('/add_task/<int:id>', methods=['POST'])
def addTask(id):
    id_token = request.cookies.get("token")
    claims = None
    tasks = []
    result = None
    invite_users = []
    board_tasks = []
    uncompleted_tasks = []
    error_message = None
    counter_list = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            chckbx = request.form.getlist('checkboxtask')

            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            invited_users = entity['invited_users']

            for task_idd in entity['task_list']:
                t_key = datastore_client.key('Tasks', task_idd)
                tt = datastore_client.get(t_key)
                if tt['task_name'] == request.form['name']:
                    invited_users.append(entity['email'])
                    return render_template('addTask.html', users=invited_users, user_data=claims,
                                           error_message=error_message, id=id, add=4)

            if len(chckbx) != 1:
                invited_users.append(entity['email'])
                return render_template('addTask.html', users=invited_users, user_data=claims,
                                       error_message=error_message, id=id, add=1)

            datenow = datetime.datetime.now().date()
            selected_date = datetime.datetime.strptime(request.form['deadline'], '%Y-%m-%d')

            if datenow > selected_date.date():
                invited_users.append(entity['email'])
                return render_template('addTask.html', users=invited_users, user_data=claims,
                                       error_message=error_message, id=id, add=2)
            task_id = createTask(claims, id, request.form['name'], request.form['deadline'], chckbx[0], 0)

            tasks = entity['task_list']
            tasks.append(task_id)
            entity.update({
                'task_list': tasks
            })
            datastore_client.put(entity)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=id, add=0)


@app.route('/remove_users/<int:id>', methods=['POST'])
def remove_users(id):
    id_token = request.cookies.get("token")
    claims = None
    boards = None
    invited_users = None
    board_tasks = None
    result = None
    uncompleted_tasks = None
    error_message = None
    counter_list = None
    users = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            users = retrieve_all_users()
            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            invited_users = entity['invited_users']
            board_tasks = retrieveTasks(entity)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            chckbx = request.form.getlist('checkboxp')
            counter_list = counters(id)
            if len(chckbx) != 1:

                return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                                       uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=entity, id=id, add=3)
            invited_users.remove(chckbx[0])
            entity.update({
                'invited_users': invited_users
            })
            datastore_client.put(entity)
            for tasks in entity['task_list']:
                task_key = datastore_client.key('Tasks', tasks)
                task = datastore_client.get(task_key)
                if task['assigned_user'] == chckbx[0]:
                    task.update({
                        'assigned_user': ""
                    })
                    datastore_client.put(task)
            print("----", chckbx[0])
            user_key = datastore_client.key('UserInfo', chckbx[0])
            user = datastore_client.get(user_key)
            print(user,"----", chckbx[0])
            board = user['board_list']
            board.remove(id)
            user.update({
                'board_list': board
            })

            datastore_client.put(user)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=id, add=0)


@app.route('/editname_page/<int:board_id>')
def editname_page(board_id):
    return render_template('edit-boardname.html', board_id=board_id, add=True)


@app.route('/edit_bname/<int:board_id>', methods=['POST'])
def edit_bname(board_id):
    id_token = request.cookies.get("token")
    claims = None
    boards = None
    counter_list = None
    error_message = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            entity_key = datastore_client.key('Board', board_id)
            entity = datastore_client.get(entity_key)
            board_name = request.form['board_name']
            entity.update({
                'board_name': board_name
            })
            datastore_client.put(entity)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(board_id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=board_id, add=0)


@app.route('/delete_task/<int:id>/<int:board_id>')
def delete_task(id, board_id):
    id_token = request.cookies.get("token")
    error_message = None
    tasks = None
    board_tasks = []
    counter_list = None
    uncompleted_tasks = []
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            entity_key = datastore_client.key('Board', board_id)
            entity = datastore_client.get(entity_key)
            deleteTask(entity, id)
            result = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(result)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(board_id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=board_id, add=0)


@app.route('/delete_board/<int:id>')
def delete_board(id):
    id_token = request.cookies.get("token")
    error_message = None
    board_tasks = []
    user_info = None
    boards = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_key = datastore_client.key('UserInfo', claims['email'])
            user_info = datastore_client.get(user_key)

            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)

            boards = retrieveBoard(user_info)
            invited_users = entity['invited_users']
            board_tasks = entity['task_list']
            print(invited_users,"----", board_tasks)
            if invited_users or board_tasks:
                return render_template('index.html', user_data=claims, user_info=user_info,
                                       boards=boards, error_message=error_message, bool=1)
            else:
                datastore_client.delete(entity_key)
                board_list = user_info['board_list']
                board_list.remove(id)
                user_info.update({
                    'board_list': board_list
                })
                datastore_client.put(user_info)
            result = retrieveUserInfo(claims)
            entity = retrieveBoard(result)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', user_data=claims, user_info=result,
                           boards=entity, error_message=error_message, bool=0)


@app.route('/edit_task_page/<int:id>/<int:board_id>')
def edit_task_page(id, board_id):
    id_token = request.cookies.get("token")
    claims = None
    error_message = None

    users = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            entity_key = datastore_client.key('Board', board_id)
            entity = datastore_client.get(entity_key)
            users = entity['invited_users']
            users.append(entity['email'])
            print(id, "----", board_id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('editTask.html', user_data=claims, users=users, error_message=error_message, id=id,
                           board_id=board_id, add=0)


@app.route('/edit_task/<int:id>', methods=['POST'])
def edit_task(id):
    id_token = request.cookies.get("token")
    error_message = None
    tasks = None
    claims = None
    result = None
    board_tasks = []
    invited_users = []
    board_id = None
    uncompleted_tasks = []
    counter_list = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            board_id = int(request.form['board_id'])

            entity_key = datastore_client.key('Board', board_id)
            entity = datastore_client.get(entity_key)

            invited_users = entity['invited_users']
            chckbx = request.form.getlist('checkboxtask')

            if len(chckbx) > 1:
                invited_users.append(entity['email'])
                return render_template('addTask.html', users=invited_users, user_data=claims,
                                       error_message=error_message, id=id, add=1)

            if request.form['deadline']:
                datenow = datetime.datetime.now().date()
                selected_date = datetime.datetime.strptime(request.form['deadline'], '%Y-%m-%d')

                if datenow > selected_date.date():
                    invited_users.append(entity['email'])
                    return render_template('addTask.html', users=invited_users, user_data=claims,
                                           error_message=error_message, id=id, add=2)

            task_key = datastore_client.key('Tasks', id)
            task = datastore_client.get(task_key)

            if chckbx:
                task.update({
                    'assigned_user': chckbx[0]
                })
            if request.form['deadline']:
                task.update({
                    'deadline': request.form['deadline']
                })
            if request.form['name']:
                task.update({
                    'task_name': request.form['name']

                })
            task.update({
                'email': claims['email']
            })
            datastore_client.put(task)
            print(task)
            result = datastore_client.get(entity_key)
            print(result)
            board_tasks = retrieveTasks(result)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(board_id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=board_id, add=0)


@app.route('/complete_tasks/<int:id>', methods=['POST'])
def completeTasks(id):
    id_token = request.cookies.get("token")
    claims = None
    boards = None
    board_tasks = []
    result = None
    counter_list = None
    error_message = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            chckbx = request.form.getlist('checkboxes')

            entity_key = datastore_client.key('Board', id)
            entity = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(entity)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(id)
            if len(chckbx) != 1:
                return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                                       uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=entity, id=id, add=1)

            task_key = datastore_client.key('Tasks', int(chckbx[0]))
            task_entity = datastore_client.get(task_key)

            if user_info['email'] != task_entity['assigned_user']:
                return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                                       uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=entity,
                                       id=id, add=2)

            finishdate = datetime.datetime.now()
            print(finishdate)
            print(task_entity)
            task_entity.update({
                'finish_date': finishdate,
                'statue': 1
            })
            datastore_client.put(task_entity)
            boards = datastore_client.get(entity_key)
            board_tasks = retrieveTasks(boards)
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
            counter_list = counters(id)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=entity, id=id, add=0)


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
    counter_list = counters(id)

    entity_key = datastore_client.key('Board', id)
    result = datastore_client.get(entity_key)
    board_tasks = retrieveTasks(result)
    uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
    #print(board_tasks)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=id, add=0)


@app.route('/invite_users/<int:id>', methods=['POST'])
def inviteUser(id):
    id_token = request.cookies.get("token")
    claims = None
    board_tasks = []
    error_message = None
    counter_list = None
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
            counter_list = counters(id)
            if len(chckbx) == 0:
                users = retrieve_all_users()
                return render_template('addUser.html', users=users, user_data=claims, id=id, add=1)

            for user in chckbx:
                exists = invited_users.count(user)
                if exists != 0:
                    users = retrieve_all_users()
                    return render_template('addUser.html', users=users, user_data=claims, id=id, add=2)
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
            uncompleted_tasks = retrieveUncompletedTasks(board_tasks)
        except ValueError as exc:
            error_message = str(exc)
    return render_template('board-page.html', user_data=claims, board_tasks=board_tasks,
                           uncompleted_tasks=uncompleted_tasks, counter_list=counter_list, result=result, id=id, add=0)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
