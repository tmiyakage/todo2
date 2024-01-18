from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import threading
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import traceback
import io

app = Flask(__name__)

# JSONキーのファイルパス
JSON_KEY_PATH = 'todo-411603-1389bdc53e74.json'
# Google DriveのフォルダID
DRIVE_FOLDER_ID = '1asEriZsUaafyT4n5t1hCBdeOZn488Ku3'

# ローカルのJSONファイルパス
JSON_FILE_PATH = 'todos.json'

# 認証情報のロード
credentials = service_account.Credentials.from_service_account_file(
    JSON_KEY_PATH, scopes=['https://www.googleapis.com/auth/drive']
)

# Google Drive APIのビルド
drive_service = build('drive', 'v3', credentials=credentials)

# 初回ロードフラグ
initial_load_complete = False

def load_todos():
    global initial_load_complete
    try:
        if not initial_load_complete:
            # 初回のロードはGoogle Driveから
            global todos_data
            file_id = '1h0JpoYAHgiALQfDpeibw1KHyBtLXLv21'
            request = drive_service.files().get_media(fileId=file_id)
            file_content = request.execute()
            todos_data = json.loads(file_content.decode('utf-8'))
            initial_load_complete = True
        else:
            # 2回目以降はローカルから
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
                todos_data = json.load(file)
    except Exception as e:
        print(f"Error loading todos: {e}")
        todos_data = []
    return todos_data

def save_todos():
    try:
        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(todos_data, file, indent=2)
    except Exception as e:
        print(f"Error saving todos locally: {e}")

    # JSONデータをバイナリに変換して、同期関数に渡す
    json_data = json.dumps(todos_data, indent=2).encode('utf-8')
    sync_thread = threading.Thread(target=sync_with_drive, args=(json_data,))
    sync_thread.start()

# Googleドライブにデータを同期する関数
def sync_with_drive(json_data):
    try:
        # Googleドライブ上のファイルID
        file_id = '1h0JpoYAHgiALQfDpeibw1KHyBtLXLv21'

        # JSONデータをバイナリに変換して、バイナリデータを指定
        media_body = MediaIoBaseUpload(io.BytesIO(json_data), mimetype='application/json')

        # Googleドライブのファイルを更新
        drive_service.files().update(
            fileId=file_id,
            media_body=media_body,
            body={'mimeType': 'application/json'}
        ).execute()

        print("Googleドライブと同期が完了しました")

    except Exception as e:
        print(f"Googleドライブとの同期中にエラーが発生しました: {e}")

@app.route('/')
def index():
    todos_data = load_todos()
    return render_template('index.html', todos=todos_data)

@app.route('/add', methods=['POST'])
def add():
    new_todo = request.form.get('new_todo')
    todos_data = load_todos()
    todos_data.append({'task': new_todo, 'status': '未完了'})
    save_todos()

    return redirect(url_for('index'))

@app.route('/delete/<int:todo_id>')
def delete(todo_id):
    todos_data = load_todos()
    if 0 <= todo_id < len(todos_data):
        del todos_data[todo_id]
        save_todos()
    return redirect(url_for('index'))

@app.route('/update_status/<int:todo_id>/<status>')
def update_status(todo_id, status):
    todos_data = load_todos()
    if 0 <= todo_id < len(todos_data):
        todos_data[int(todo_id)]['status'] = status
        save_todos()
    return redirect(url_for('index'))

@app.route('/update_order', methods=['POST'])
def update_order():
    new_order = request.json.get('new_order')
    todos_data = load_todos()

    # リクエストで受け取った新しい順序にToDoアイテムを更新
    todos_data = [todos_data[int(index)] for index in new_order]

    # 保存
    save_todos()

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
