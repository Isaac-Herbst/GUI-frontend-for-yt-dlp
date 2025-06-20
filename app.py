from flask import Flask, render_template, request, jsonify, Response
import re
import os
import subprocess
from threading import Thread
from queue import Queue
from werkzeug.utils import secure_filename
import json
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/cookies'
DOWNLOAD_FOLDER = '/downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# Used for a couple helper functions, mainly for parsing metadata files
MEDIA_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.flv', '.avi', '.mp3', '.m4a', '.ogg', '.aac', '.flac'}

log_queue = Queue()

# Helper Functions
def is_likely_playlist(url):
    """Helper to determine if a URL likely points to a playlist based on common patterns."""
    lower_url = url.lower()
    return ('playlist' in lower_url or 
            'list=' in lower_url or
            '/sets/' in lower_url or
            '/albums/' in lower_url)

def build_format_command(format_type):
    """
    Helper to build yt-dlp format-specific command flags.
    Returns a list of flags based on whether video or audio is requested.
    """
    command = []
    if format_type in ['mp4', 'mkv', 'webm', 'flv', 'avi']:
        if format_type == 'mp4':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mp4']
        elif format_type == 'mkv':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mkv']
        elif format_type == 'webm':
            command += ['-f', 'bestvideo+bestaudio/best[ext=webm]']
        elif format_type == 'flv':
            command += ['-f', 'best[ext=flv]']
        elif format_type == 'avi':
            command += ['-f', 'bestvideo+bestaudio', '--merge-output-format', 'avi']
    else:
        command += ['-x']
        if format_type == 'mp3':
            command += ['--audio-format', 'mp3']
        elif format_type == 'ogg':
            command += ['--audio-format', 'vorbis']
        elif format_type == 'aac':
            command += ['--audio-format', 'aac']
        elif format_type == 'flac':
            command += ['--audio-format', 'flac']
        elif format_type == 'm4a':
            command += ['--audio-format', 'm4a']
    return command

def add_download_option_commands(command, download_options, metadata_dir, is_playlist):
    """
    Add yt-dlp commands for download options (e.g., metadata).
    For playlists, metadata_dir is the subfolder inside the playlist folder.
    """
    # For playlists, metadata_dir is like output_dir/%(playlist_title)s/%(title)s
    # For singles, metadata_dir is like output_dir/%(title)s or output_dir (if no metadata folder)

    # Attach --paths only for metadata files, so they go into metadata_dir subfolder

    if download_options.get('description'):
        command += ['--write-description', '--embed-metadata']
        command += ['--paths', f'description:{metadata_dir}']

    if download_options.get('comments'):
        command += ['--write-comments']

    if download_options.get('info_json'):
        command += ['--write-info-json', '--embed-info-json']
        command += ['--paths', f'infojson:{metadata_dir}']

    if download_options.get('subtitles'):
        command += ['--write-subs', '--write-auto-subs', '--embed-subs']
        command += ['--paths', f'subtitle:{metadata_dir}']

    if download_options.get('thumbnail'):
        command += ['--write-thumbnail', '--embed-thumbnail']
        command += ['--paths', f'thumbnail:{metadata_dir}']

    if download_options.get('sponsorblock') or download_options.get('sponsorblock_remove'):
        command += ['--sponsorblock-remove', 'all']

def deduplicate_command(command):
    """Helper to remove duplicate flags from the command list while preserving order and arguments."""
    unique_command = []
    seen_flags = set()
    for item in command:
        if item.startswith('-'):
            if item not in seen_flags:
                seen_flags.add(item)
                unique_command.append(item)
        else:
            unique_command.append(item)
    return unique_command

def build_metadata_dir(output_dir, is_playlist):
    """
    Returns metadata directory template path based on playlist/single video.
    Metadata will be stored in a subfolder named after the video title.
    """
    if is_playlist:
        return f'{output_dir}/%(playlist_title)s/%(title)s/%(title)s'
    else:
        return f'{output_dir}/%(title)s/%(title)s'

def is_media_file(filename):
    """
    Helper function for determining while filetype the current file is.
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() in MEDIA_EXTENSIONS

def move_media_files_up_and_metadata_down(base_dir):
    """
    Organize files so that:
    - Media files are moved up from video-named subfolders to base_dir.
    - Metadata files (including comment files with suffixes) are moved into their respective video-named subfolders.
    """

    # Move media files up from video-named subfolders to base_dir
    for entry in os.listdir(base_dir):
        entry_path = os.path.join(base_dir, entry)
        if os.path.isdir(entry_path):
            for media_ext in MEDIA_EXTENSIONS:
                candidate = os.path.join(entry_path, f"{entry}{media_ext}")
                if os.path.exists(candidate):
                    target_path = os.path.join(base_dir, f"{entry}{media_ext}")
                    if not os.path.exists(target_path):
                        try:
                            shutil.move(candidate, target_path)
                            print(f"Moved media file {candidate} -> {target_path}")
                        except Exception as e:
                            print(f"Error moving media file {candidate}: {e}")
                    else:
                        print(f"Target media file already exists: {target_path}")

    # Move all non-media files into their video-named subfolders
    media_base_names = {
        os.path.splitext(f)[0]
        for f in os.listdir(base_dir)
        if is_media_file(f)
    }

    for file in os.listdir(base_dir):
        file_path = os.path.join(base_dir, file)

        if os.path.isdir(file_path) or is_media_file(file):
            continue  # skip folders and media files

        # Try to find the matching media base name
        moved = False
        for base_name in media_base_names:
            if file.startswith(base_name):
                target_folder = os.path.join(base_dir, base_name)
                os.makedirs(target_folder, exist_ok=True)
                try:
                    shutil.move(file_path, os.path.join(target_folder, file))
                    print(f"Moved metadata file {file} -> {target_folder}")
                    moved = True
                except Exception as e:
                    print(f"Error moving metadata file {file}: {e}")
                break

        if not moved:
            print(f"Did not move metadata file (no matching media found): {file}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browse_directories', methods=['GET'])
def browse_directories():
    """Browse server directories for output selection."""
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
    """Validate if URL is a supported video platform."""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({'valid': False, 'error': 'No URL provided'})
    
    if not re.match(r'^https?://', url):
        return jsonify({'valid': False, 'error': 'Invalid URL format'})
    
    supported_domains = [
        'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
        'twitch.tv', 'facebook.com', 'instagram.com', 'tiktok.com'
    ]
    
    is_supported = any(domain in url.lower() for domain in supported_domains)
    is_playlist = is_likely_playlist(url)
    
    return jsonify({
        'valid': is_supported,
        'is_youtube': 'youtube.com' in url.lower() or 'youtu.be' in url.lower(),
        'is_playlist': is_playlist
    })

@app.route('/upload_cookies', methods=['POST'])
def upload_cookies():
    """Handle uploading and processing of cookies files."""
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
    """
    Convert JSON cookies to Netscape format for yt-dlp.
    Writes a new file and returns its path if successful.
    """
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
    format_type = data.get('format')
    output_dir = data.get('output_dir')
    cookies_path = data.get('cookies_path')
    download_options = data.get('download_options', {})
    is_playlist = data.get('is_playlist', False) or is_likely_playlist(url)

    if not url or not output_dir:
        return jsonify({'error': 'URL and output directory required'}), 400

    if not re.match(r'^https?://', url):
        return jsonify({'error': 'Invalid URL format'}), 400

    os.makedirs(output_dir, exist_ok=True)

    extra_files_requested = any(download_options.get(opt) for opt in [
        'description', 'comments', 'info_json', 'subtitles', 'thumbnail', 'sponsorblock', 'sponsorblock_remove'
    ]) or any(flag in (data.get('custom_flags') or []) for flag in [
        '--write-description', '--write-info-json', '--write-comments', '--write-subs', '--write-auto-subs',
        '--write-thumbnail', '--sponsorblock-remove'
    ])

    if is_playlist:
        output_template = f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s'
        metadata_dir = f'{output_dir}/%(playlist_title)s/%(title)s'
    elif extra_files_requested:
        output_template = f'{output_dir}/%(title)s/%(title)s.%(ext)s'
        metadata_dir = f'{output_dir}/%(title)s'
    else:
        output_template = f'{output_dir}/%(title)s.%(ext)s'
        metadata_dir = output_dir

    command = ['yt-dlp', '--continue', '-o', output_template]
    command += build_format_command(format_type)

    custom_flags = data.get('custom_flags', [])

    # Infer download_options from custom_flags if not explicitly set
    if '--write-description' in custom_flags:
        download_options['description'] = True
    if '--write-info-json' in custom_flags:
        download_options['info_json'] = True
    if '--write-comments' in custom_flags:
        download_options['comments'] = True
    if '--write-subs' in custom_flags or '--write-auto-subs' in custom_flags:
        download_options['subtitles'] = True
    if '--write-thumbnail' in custom_flags:
        download_options['thumbnail'] = True
    if '--sponsorblock-remove' in custom_flags:
        download_options['sponsorblock'] = True

    add_download_option_commands(command, download_options, metadata_dir, is_playlist)

    if cookies_path:
        command += ['--cookies', cookies_path]

    if isinstance(custom_flags, list):
        command += custom_flags
    command.append(url)

    command = deduplicate_command(command)

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
        try:
            if is_playlist:
                # Look for playlist folder (usually one folder in output_dir)
                playlist_subfolders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
                for folder in playlist_subfolders:
                    folder_path = os.path.join(output_dir, folder)
                    move_media_files_up_and_metadata_down(folder_path)
            else:
                move_media_files_up_and_metadata_down(output_dir)
        except Exception as e:
            print(f"Error organizing metadata files: {e}")

    Thread(target=run_command, daemon=True).start()
    return jsonify({'message': 'Download started'}), 200

@app.route('/stream_logs')
def stream_logs():
    """Stream download logs via Server-Sent Events (SSE)."""
    def generate():
        while True:
            line = log_queue.get()
            yield f'data: {line}\n\n'
            if line == '[DONE]':
                break
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)