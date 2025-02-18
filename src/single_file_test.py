import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import json
import os
import sys

# Function to convert JSON cookies to Netscape format
def convert_cookies():
    cookies_file = filedialog.askopenfilename(
        title="Select Cookies File",
        filetypes=[("JSON Files", "*.json"), ("Text Files", "*.txt")]
    )
    if not cookies_file:
        return

    try:
        if cookies_file.endswith('.json'):
            # Convert JSON to Netscape format
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)

            netscape_file = os.path.join(os.path.dirname(cookies_file), 'youtube_cookies_netscape.txt')
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

            messagebox.showinfo("Success", f"Cookies converted and saved to:\n{netscape_file}")
        else:
            # If it's already a .txt file, just inform the user
            messagebox.showinfo("Info", "The selected file is already in the correct format.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to convert cookies: {e}")

# Function to execute the yt-dlp command in a terminal window
def start_download():
    playlist_url = url_entry.get()
    output_dir = output_entry.get()
    cookies_file = cookies_entry.get()

    if not playlist_url or not output_dir:
        messagebox.showerror("Error", "Please fill in all required fields.")
        return

    command = [
        'yt-dlp',
        '--continue',
        '-f', 'bestvideo+bestaudio',
        '--merge-output-format', 'mp4',
        '-o', f'{output_dir}/%(title)s.%(ext)s',
        '--age-limit', '100'
    ]

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

# Function to create and display the info window
def show_info():
    # Disable the main window
    root.attributes('-disabled', True)

    # Create a new window
    info_window = tk.Toplevel(root)
    info_window.title("Program Information")
    info_window.geometry("500x400")  # Set a fixed size for the info window

    # Add a scrollbar
    scrollbar = ttk.Scrollbar(info_window)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Add a canvas to hold the text and link it to the scrollbar
    canvas = tk.Canvas(info_window, yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar.config(command=canvas.yview)

    # Add a frame inside the canvas to hold the content
    frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=frame, anchor=tk.NW)

    # Add program information
    info_text = """
    Program: yt-dlp Download Manager
    Version: 1.0

    Dependencies:
    - Python 3.x
    - yt-dlp (must be installed and accessible in the system PATH)

    Requirements:
    - A valid YouTube playlist URL.
    - An output directory to save downloaded files.
    - Optional: A cookies file for accessing age-restricted content.

    Instructions:
    1. Enter the playlist URL.
    2. Select the output directory.
    3. Optionally, provide a cookies file (in JSON or Netscape format).
    4. Click "Start Download" to begin the download process.

    Notes:
    - The cookies file can be converted from JSON to Netscape format using the "Convert JSON Cookies" button.
    - The download process will open in a new terminal window.
    """

    info_label = tk.Label(frame, text=info_text, justify=tk.LEFT, padx=10, pady=10)
    info_label.pack()

    # Add a Close button
    close_button = tk.Button(frame, text="Close", command=lambda: close_info_window(info_window))
    close_button.pack(pady=10)

    # Update the canvas to enable scrolling
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    # Handle the red X button
    info_window.protocol("WM_DELETE_WINDOW", lambda: close_info_window(info_window))

# Function to close the info window and re-enable the main window
def close_info_window(info_window):
    info_window.destroy()
    root.attributes('-disabled', False)
    root.focus_set()  # Bring the main window back into focus

# GUI Setup
root = tk.Tk()
root.title("yt-dlp Download Manager")

# Playlist URL
tk.Label(root, text="Playlist URL:").grid(row=0, column=0, padx=10, pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=5)

# Output Directory
tk.Label(root, text="Output Directory:").grid(row=1, column=0, padx=10, pady=5)
output_entry = tk.Entry(root, width=50)
output_entry.grid(row=1, column=1, padx=10, pady=5)
tk.Button(root, text="Browse", command=lambda: output_entry.insert(0, filedialog.askdirectory())).grid(row=1, column=2, padx=10, pady=5)

# Cookies File
tk.Label(root, text="Cookies File (Optional):").grid(row=2, column=0, padx=10, pady=5)
cookies_entry = tk.Entry(root, width=50)
cookies_entry.grid(row=2, column=1, padx=10, pady=5)
tk.Button(root, text="Browse", command=lambda: cookies_entry.insert(0, filedialog.askopenfilename(
    title="Select Cookies File",
    filetypes=[("JSON Files", "*.json"), ("Text Files", "*.txt")]
))).grid(row=2, column=2, padx=10, pady=5)

# Convert Cookies Button
tk.Button(root, text="Convert JSON Cookies to Netscape Format", command=convert_cookies).grid(row=3, column=0, columnspan=3, pady=10)

# Start Download Button
tk.Button(root, text="Start Download", command=start_download).grid(row=4, column=0, columnspan=3, pady=10)

# Info Button
tk.Button(root, text="Info", command=show_info).grid(row=5, column=0, columnspan=3, pady=10)

# Run the GUI
root.mainloop()