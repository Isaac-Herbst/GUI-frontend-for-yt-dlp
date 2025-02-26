import subprocess
import sys
import json
import os
from tkinter import messagebox

def is_netscape_format(file_path):
    """Check if the cookies file is in Netscape format."""
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            return first_line.startswith('# Netscape HTTP Cookie File')
    except Exception:
        return False

def convert_to_netscape(file_path):
    """Convert a JSON cookies file to Netscape format."""
    try:
        with open(file_path, 'r') as f:
            cookies = json.load(f)

        netscape_file = os.path.splitext(file_path)[0] + "-netscape.txt"
        with open(netscape_file, 'w') as f:
            f.write('# Netscape HTTP Cookie File\n')
            for cookie in cookies:
                f.write('\t'.join([
                    cookie.get('domain', ''),
                    'TRUE' if not cookie.get('hostOnly', False) else 'FALSE',  # Set TRUE for domain cookies
                    cookie.get('path', '/'),
                    'TRUE' if cookie.get('secure', False) else 'FALSE',        # TRUE if secure
                    str(int(cookie.get('expirationDate', 0))),                # Convert expirationDate to an integer
                    cookie.get('name', ''),
                    cookie.get('value', '')
                ]) + '\n')

        return netscape_file
    except Exception as e:
        messagebox.showerror("Error", f"Failed to convert cookies: {e}")
        return None

def start_download(playlist_url, output_dir, cookies_file, download_format):
    if not playlist_url or not output_dir:
        messagebox.showerror("Error", "Please fill in all required fields.")
        return

    # Handle cookies file
    converted_cookies_file = None
    if cookies_file:
        if not is_netscape_format(cookies_file):
            # Convert to Netscape format
            converted_cookies_file = convert_to_netscape(cookies_file)
            if not converted_cookies_file:
                return  # Conversion failed
            cookies_file = converted_cookies_file

    # Build the yt-dlp command based on the selected format
    command = ['yt-dlp', '--continue', '-o', f'{output_dir}/%(title)s.%(ext)s', '--age-limit', '100']

    # Video formats
    video_formats = ["mp4", "mkv", "webm", "flv"]
    if download_format in video_formats:
        # Default to mp4 if merging fails
        command.extend(['-f', 'bestvideo+bestaudio', '--merge-output-format', 'mp4'])
    # Audio formats
    else:
        # Default to mp3 if merging fails
        command.extend(['-x', '--audio-format', 'mp3'])

    if cookies_file:
        command.extend(['--cookies', cookies_file])

    command.append(playlist_url)

    try:
        # Spawn a terminal window to show the download process
        if sys.platform == "win32":
            # For Windows, use 'start' to open a new terminal window
            subprocess.Popen(['start', 'cmd', '/k'] + command, shell=True)
        elif sys.platform == "darwin":
            # For macOS, use 'osascript' to open a new Terminal window
            script = f'tell application "Terminal" to do script "{" ".join(command)}"'
            subprocess.Popen(['osascript', '-e', script])
        else:
            # For Linux, use 'gnome-terminal' or 'xterm'
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', ' '.join(command) + '; exec bash'])

        messagebox.showinfo("Info", "Download started in a new terminal window.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start download: {e}")
    finally:
        # Delete the converted cookies file if it was created
        if converted_cookies_file and os.path.exists(converted_cookies_file):
            os.remove(converted_cookies_file)