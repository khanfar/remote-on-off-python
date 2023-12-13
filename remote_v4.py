from flask import Flask, request
import requests
import subprocess
import threading
import time
import logging
import os
import psutil
import json
import msvcrt
import errno

app = Flask(__name__)

TOKEN = '1898741656:AAH-s2qX7yUY-pSjRHt8ZVrPuUGRsf12o_c'  # Replace with your bot token
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'
script_process = None

# Get the directory of the current script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the lock file path in the same directory as the script
LOCK_FILE_PATH = os.path.join(script_directory, "bot_lock.lock")

script_paths = [
    os.path.join(script_directory, "main.py"),
    os.path.join(script_directory, "telegram_bot.py"),
    os.path.join(script_directory, "usage_tracker.py"),
    os.path.join(script_directory, "utils.py")
]

logging.basicConfig(level=logging.INFO)

keyboard = {"inline_keyboard": [[
    {"text": "Start", "callback_data": "startscript"},
    {"text": "Stop", "callback_data": "stopscript"},
]]}

def acquire_lock():
    with open(LOCK_FILE_PATH, 'w') as lock_file:
        # Windows doesn't support fcntl, use a workaround
        while True:
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                break
            except IOError as e:
                if hasattr(errno, 'EAGAIN') and e.errno != errno.EAGAIN:
                    raise
                elif not hasattr(errno, 'EAGAIN') and e.winerror != 36:  # ERROR_SHARING_VIOLATION
                    raise
                else:
                    time.sleep(0.1)

def release_lock():
    try:
        with open(LOCK_FILE_PATH, 'w') as lock_file:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    except PermissionError:
        # Ignore PermissionError in case the file is not locked
        pass

def send_message(chat_id, text, reply_markup=None):
    url = f'{TELEGRAM_API}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(url, json=data)

def start_script():
    global script_process
    try:
        if script_process is None:
            script_process = subprocess.Popen(['python', script_paths[0]], start_new_session=True)
            return "Script started!"
        else:
            return "Script is already running."
    except Exception as e:
        logging.error(f"Error starting script: {e}")
        return "Failed to start script."

def stop_all_scripts():
    global script_process
    try:
        if script_process is not None:
            parent = psutil.Process(script_process.pid)
            children = parent.children(recursive=True)
            for process in children:
                process.terminate()

            try:
                parent.terminate()
                parent.wait(timeout=5)  # Wait for the parent process to terminate
            except psutil.TimeoutExpired:
                parent.kill()  # If termination takes too long, forcefully kill the parent process

            script_process = None  # Reset script_process variable
            return "All scripts stopped."
        else:
            return "No scripts are running."
    except Exception as e:
        logging.error(f"Error stopping scripts: {e}")
        return "Failed to stop scripts."

def handle_update(update):
    if 'message' in update:
        message = update['message']
        text = message.get('text')
        chat_id = message['chat']['id']

        if text == '/start':
            send_message(chat_id, "Welcome!", reply_markup=keyboard)
    elif 'callback_query' in update:
        callback_query = update['callback_query']
        data = callback_query.get('data')
        chat_id = callback_query['message']['chat']['id']

        if data == 'startscript':
            message = start_script()
        elif data == 'stopscript':
            message = stop_all_scripts()
        else:
            message = "Unknown command."

        send_message(chat_id, message)

def poll_updates():
    offset = 0
    while True:
        acquire_lock()  # Acquire the lock before making the getUpdates request
        try:
            response = requests.get(f'{TELEGRAM_API}/getUpdates?offset={offset}')
            response_data = response.json()

            if 'result' in response_data:
                updates = response_data['result']
                if updates:
                    offset = updates[-1]['update_id'] + 1
                    for update in updates:
                        handle_update(update)
            else:
                print("No updates found in the response.")
        finally:
            release_lock()  # Release the lock after processing updates

        time.sleep(1)  # Introduce a delay to stay within the rate limit

if __name__ == '__main__':
    threading.Thread(target=poll_updates).start()
    app.run(port=8000, debug=True)
