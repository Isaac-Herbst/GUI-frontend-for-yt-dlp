import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import PhotoImage, ttk
from info import show_info
from download_logic import start_download
import sys
import os

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# GUI Setup
root = tk.Tk()
root.title("yt-dlp Download Manager")

# Set custom icon
try:
    #building .exe line
    #icon_path = resource_path(os.path.join("img", "logo.png"))  # Use the correct path for the bundled file
    #source
    icon_path = resource_path("src/logo.png")
    icon_image = PhotoImage(file=icon_path)
    root.iconphoto(True, icon_image)
except Exception as e:
    print(f"Failed to load custom icon: {e}")

# Playlist URL
tk.Label(root, text="Video/Playlist URL:").grid(row=0, column=0, padx=10, pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=5)

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

# Format Selection
tk.Label(root, text="Download Format:").grid(row=3, column=0, padx=10, pady=5)
format_var = tk.StringVar(value="mp4")  # Default to mp4
# List of supported formats
supported_formats = [
    "mp4", "mkv", "webm", "flv",  # Video formats
    "mp3", "aac", "flac", "wav", "m4a", "opus", "vorbis"  # Audio formats
]
format_menu = ttk.Combobox(root, textvariable=format_var, values=supported_formats, state="readonly", width=47)
format_menu.grid(row=3, column=1, padx=10, pady=5)

# Start Download Button
tk.Button(root, text="Start Download", command=lambda: start_download(
    url_entry.get(), output_entry.get(), cookies_entry.get(), format_var.get()
)).grid(row=4, column=0, columnspan=3, pady=10)

# Info Button
tk.Button(root, text="Info", command=lambda: show_info(root)).grid(row=5, column=0, columnspan=3, pady=10)

# Run the GUI
root.mainloop()