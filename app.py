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
DOWNLOAD_FOLDER = '/downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

log_queue = Queue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browse_directories', methods=['GET'])
def browse_directories():
    """Browse server directories for output selection"""
    path = request.args.get('path', app.config['DOWNLOAD_FOLDER'])
    try:
        if not os.path.exists(path):
            return jsonify({'error': 'Path does not exist'}), 400
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                items.append({
                    'name': item,
                    'path': item_path,
                    'type': 'directory'
                })
        
        parent_path = os.path.dirname(path) if path != '/' else None
        return jsonify({
            'current_path': path,
            'parent_path': parent_path,
            'items': sorted(items, key=lambda x: x['name'].lower())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/validate_url', methods=['POST'])
def validate_url():
    """Validate if URL is a supported video platform"""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({'valid': False, 'error': 'No URL provided'})
    
    # Basic URL validation
    if not re.match(r'^https?://', url):
        return jsonify({'valid': False, 'error': 'Invalid URL format'})
    
    # Check if it's a supported platform (basic check)
    supported_domains = [
        'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
        'twitch.tv', 'facebook.com', 'instagram.com', 'tiktok.com'
    ]
    
    is_supported = any(domain in url.lower() for domain in supported_domains)
    
    # Check if URL appears to be a playlist
    is_playlist = ('playlist' in url.lower() or 
                   'list=' in url.lower() or
                   '/sets/' in url.lower() or  # SoundCloud sets
                   '/albums/' in url.lower())  # Various platforms
    
    return jsonify({
        'valid': is_supported,
        'is_youtube': 'youtube.com' in url.lower() or 'youtu.be' in url.lower(),
        'is_playlist': is_playlist
    })

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
    output_dir = data.get('output_dir')
    cookies_path = data.get('cookies_path')
    
    # New download options
    download_options = data.get('download_options', {})
    is_playlist = data.get('is_playlist', False)

    if not url or not output_dir:
        return jsonify({'error': 'URL and output directory required'}), 400
    
    if not is_playlist:
        lower_url = url.lower()
        if ('playlist' in lower_url or
            'list=' in lower_url or
            '/sets/' in lower_url or
            '/albums/' in lower_url):
            is_playlist = True
    
    output_dir = output_dir or app.config['DOWNLOAD_FOLDER']

    if not re.match(r'^https?://', url):
        return jsonify({'error': 'Invalid URL format'}), 400

    os.makedirs(output_dir, exist_ok=True)

    # Modify output template for playlists
    if is_playlist:
        output_template = f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s'
    else:
        output_template = f'{output_dir}/%(title)s.%(ext)s'

    command = ['yt-dlp', '--continue', '-o', output_template]
    
    # Handle different formats
    if format_ in ['mp4', 'mkv', 'webm', 'flv', 'avi']:
        if format_ == 'mp4':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mp4']
        elif format_ == 'mkv':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mkv']
        elif format_ == 'webm':
            command += ['-f', 'bestvideo+bestaudio/best[ext=webm]']
        elif format_ == 'flv':
            command += ['-f', 'best[ext=flv]']
        elif format_ == 'avi':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'avi']
    else:  # Audio formats
        command += ['-x']
        if format_ == 'mp3':
            command += ['--audio-format', 'mp3']
        elif format_ == 'ogg':
            command += ['--audio-format', 'vorbis']
        elif format_ == 'aac':
            command += ['--audio-format', 'aac']
        elif format_ == 'flac':
            command += ['--audio-format', 'flac']
        elif format_ == 'm4a':
            command += ['--audio-format', 'm4a']

    # Add download options with automatic embedding
    if download_options.get('description'):
        command += ['--write-description', '--embed-metadata']
    
    if download_options.get('comments'):
        command += ['--write-comments']
    
    if download_options.get('info_json'):
        command += ['--write-info-json', '--embed-info-json']
    
    if download_options.get('subtitles'):
        command += ['--write-subs', '--write-auto-subs', '--embed-subs']
    
    if download_options.get('thumbnail'):
        command += ['--write-thumbnail', '--embed-thumbnail']
    
    if download_options.get('sponsorblock') or download_options.get('sponsorblock_remove'):
        command += ['--sponsorblock-remove', 'all']

    if cookies_path:
        command += ['--cookies', cookies_path]

    custom_flags = data.get('custom_flags', [])
    if isinstance(custom_flags, list):
        command += custom_flags
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
                if "[ffmpeg]" in line or "Destination" in line or "[info]" in line:
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
