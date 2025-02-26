import tkinter as tk
from tkinter import ttk

def show_info(root):
    # Disable the main window
    root.attributes('-disabled', True)

    # Create a new window
    info_window = tk.Toplevel(root)
    info_window.title("Program Information")
    info_window.geometry("800x400")  # Set a fixed size for the info window

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
    yt-dlp GUI Frontend
    Version 1.1
    Authored by Isaac Herbst, last updated 02/26/2025

    Dependencies:
    - Python 3.x
    - yt-dlp (must be installed and accessible in the system PATH)

    Requirements:
    - A valid YouTube playlist/video URL.
    - An output directory to save downloaded files.
    - Optional: A cookies file for accessing age-restricted content.

    Instructions:
    1. Enter the playlist/video URL.
    2. Select the output directory.
    3. Optionally, provide a cookies file (in .json or .txt format).
        3.1. This is an export of your cookie data from a signed-in YouTube profile.
        3.2. Save that export as a .json or .txt file.
        3.3. This program automatically converts that file into a yt-dlp readable format into a new file, then deletes it when the download ends.
    4. Click "Start Download" to begin the download process.

    Notes:
    - Upon multiple downloads, all paths will not clear. Be careful where you download!
    - The download process will open in a new terminal window.

    Relevant bugs/program quirks:
    - Pausing the output with Ctrl+C on the output terminal will pause the download, but that command is not stored in the terminal.
    - Closing this (info) window will not bring focus back to the main window.
    - For formats not mp4/mp3, currently format merging does not work. It defaults to mp4/mp3.
    - If the machine this runs on has insufficient storage for everything, there isn't any error handling for that.
    """

    info_label = tk.Label(frame, text=info_text, justify=tk.LEFT, padx=10, pady=10)
    info_label.pack()

    # Add a Close button
    close_button = tk.Button(frame, text="Close", command=lambda: close_info_window(info_window, root))
    close_button.pack(pady=10)

    # Update the canvas to enable scrolling
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    # Bind mouse scroll event to the canvas
    def on_mouse_wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    # Handle the red X button
    info_window.protocol("WM_DELETE_WINDOW", lambda: close_info_window(info_window, root))

# Function to close the info window and re-enable the main window
def close_info_window(info_window, root):
    info_window.destroy()
    root.attributes('-disabled', False)
    root.focus_set()  # Bring the main window back into focus