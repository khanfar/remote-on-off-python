from flask import Flask, request
import requests
import subprocess
import threading
import time
import logging
import signal
import os
import psutil
import json

app = Flask(__name__)

TOKEN = '1898xxx56:AAH-s2qX7yxxxxxo_c'  # Replace with your bot token
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'
script_process = None

script_path = r"C:\Users\Lenovo\Desktop\chatgpt-telegram-bot-main-12-12-2023\chatgpt-telegram-bot-main\bot\main.py"

logging.basicConfig(level=logging.INFO)

keyboard = {"inline_keyboard": [[
    {"text": "Start", "callback_data": "startscript"},
    {"text": "Stop", "callback_data": "stopscript"},
]]}

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
            script_process = subprocess.Popen(['python', script_path], start_new_session=True)
            return "Script started!"
        else:
            return "Script is already running."
    except Exception as e:
        logging.error(f"Error starting script: {e}")
        return "Failed to start script."

def stop_script():
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
            return "Script stopped."
        else:
            return "Script is not running."
    except Exception as e:
        logging.error(f"Error stopping script: {e}")
        return "Failed to stop script."


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
            message = stop_script()
        else:
            message = "Unknown command."
 
        send_message(chat_id, message)

def poll_updates():
    offset = 0
    while True:
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

if __name__ == '__main__':
    threading.Thread(target=poll_updates).start()
    app.run(port=8000, debug=True)
