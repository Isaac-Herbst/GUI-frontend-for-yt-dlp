from flask import Flask, render_template, request, jsonify, Response
import re
import os
import subprocess
from threading import Thread
from queue import Queue
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/cookies'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

log_queue = Queue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_cookies', methods=['POST'])
def upload_cookies():
    if 'cookies_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['cookies_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    try:
        with open(path, 'r') as f:
            cookies = json.load(f)
        netscape_path = convert_to_netscape(path, cookies)
        if netscape_path is None:
            return jsonify({'error': 'Failed to convert cookies to Netscape format'}), 500
        path = netscape_path

    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Unexpected error reading cookies file: {e}")
        return jsonify({'error': 'Error processing cookies file'}), 500

    return jsonify({'message': 'File uploaded', 'path': path}), 200

def convert_to_netscape(file_path, cookies):
    try:
        netscape_file = os.path.splitext(file_path)[0] + "-netscape.txt"
        with open(netscape_file, 'w') as f:
            f.write('# Netscape HTTP Cookie File\n')
            for cookie in cookies:
                domain = cookie.get('domain', '')
                include_subdomains = not cookie.get('hostOnly', False)
                if include_subdomains:
                    if not domain.startswith('.'):
                        domain = '.' + domain
                else:
                    if domain.startswith('.'):
                        domain = domain[1:]

                f.write('\t'.join([
                    domain,
                    'TRUE' if include_subdomains else 'FALSE',
                    cookie.get('path', '/'),
                    'TRUE' if cookie.get('secure', False) else 'FALSE',
                    str(int(cookie.get('expirationDate', 0))),
                    cookie.get('name', ''),
                    cookie.get('value', '')
                ]) + '\n')

        return netscape_file
    except Exception as e:
        print(f"Failed to convert cookies: {e}")
        return None

@app.route('/start_download', methods=['POST'])
def start_download():
    if not request.is_json:
        return jsonify({'error': 'Request must be in JSON format'}), 400

    data = request.get_json()
    url = data.get('url')
    format_ = data.get('format')
    output_dir = data.get('output_dir') or '/downloads'
    cookies_path = data.get('cookies_path')

    if not url or 'output_dir' not in data:
        return jsonify({'error': 'URL and output directory required'}), 400

    if not re.match(r'^https?://', url):
        return jsonify({'error': 'Invalid URL format'}), 400

    os.makedirs(output_dir, exist_ok=True)

    command = ['yt-dlp', '--continue', '-o', f'{output_dir}/%(title)s.%(ext)s']
    if format_ in ['mp4', 'mkv', 'webm', 'flv']:
        command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mp4']
    else:
        command += ['-x', '--audio-format', 'mp3']
    if cookies_path:
        command += ['--cookies', cookies_path]
    command.append(url)

    def run_command():
        last_percent = -1
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line.strip())
            match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%.*?at\s+([^\s]+).*?ETA\s+([^\s]+)", line)
            if match:
                percent = float(match.group(1))
                speed = match.group(2)
                eta = match.group(3)
                if int(percent) != last_percent:
                    log_queue.put(f"PROGRESS::{percent}::{speed}::{eta}")
                    last_percent = int(percent)
            else:
                if "[ffmpeg]" in line or "Destination" in line:
                    log_queue.put(f"INFO::{line.strip()}")
        log_queue.put('[DONE]')

    Thread(target=run_command, daemon=True).start()
    return jsonify({'message': 'Download started'}), 200

@app.route('/stream_logs')
def stream_logs():
    def generate():
        while True:
            line = log_queue.get()
            yield f'data: {line}\n\n'
            if line == '[DONE]':
                break
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
