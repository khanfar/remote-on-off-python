from flask import Flask, request
import requests
import subprocess
import threading
import time
import logging
import signal
import os
import psutil

app = Flask(__name__)

TOKEN = '1898xxx:AAH-s2qXxxY-pSjxxxx12o_c'  # Replace with your bot token
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'
script_process = None

script_path = r"C:\Users\Lenovo\Desktop\chatgpt-telegram-bot-main-12-12-2023\chatgpt-telegram-bot-main\bot\main.py"

logging.basicConfig(level=logging.INFO)

def send_message(chat_id, text):
    url = f'{TELEGRAM_API}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    requests.post(url, data=data)

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
        if script_process.poll() is None:  # If still running, send SIGTERM to process group
            parent = psutil.Process(script_process.pid)
            children = parent.children(recursive=True)
            for process in children:
                process.send_signal(signal.SIGTERM)
            script_process.send_signal(signal.SIGTERM)
        script_process = None  # Reset script_process variable
        return "Script stopped."
    except Exception as e:
        logging.error(f"Error stopping script: {e}")
        return "Failed to stop script."

@app.route('/webhook', methods=['POST'])
def webhook(update):
    chat_id = update['message']['chat']['id']
    text = update['message']['text']

    logging.info(f"Received command: {text}")

    if text == '/startscript':
        message = start_script()
    elif text == '/stopscript':
        message = stop_script()
    else:
        message = "Unknown command."

    send_message(chat_id, message)
    return 'OK'

def poll_updates():
    offset = 0
    while True:
        response = requests.get(f'{TELEGRAM_API}/getUpdates?offset={offset}')
        updates = response.json()['result']
        for update in updates:
            offset = update['update_id'] + 1
            threading.Thread(target=webhook, args=(update,)).start()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=poll_updates).start()
    app.run(port=5000)
