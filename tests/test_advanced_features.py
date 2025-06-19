import unittest
import os
import shutil
from app import app, DOWNLOAD_FOLDER
from unittest.mock import patch, MagicMock

class AdvancedFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.video_title = "Test Video Title"
        self.video_folder = os.path.join(DOWNLOAD_FOLDER, self.video_title)
        os.makedirs(self.video_folder, exist_ok=True)  # simulate output folder

    def tearDown(self):
        if os.path.exists(self.video_folder):
            shutil.rmtree(self.video_folder)  # clean up after test

    def test_custom_flag_creates_subfolder_for_extra_files(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=video123",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {},
            "custom_flags": ["--write-description", "--write-info-json"]
        }

        # Simulated yt-dlp output that would include extra files
        mock_lines = [
            f"[download] Destination: {self.video_title}/video.mp4",
            f"[info] Writing video description to: {self.video_title}/{self.video_title}.description",
            f"[info] Writing metadata to: {self.video_title}/{self.video_title}.info.json",
            "[DONE]"
        ]

        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(mock_lines)
            mock_popen.return_value = mock_proc

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Download started", response.get_json()["message"])

            called_args = mock_popen.call_args[0][0]
            output_path_flag_index = called_args.index('-o')
            output_template = called_args[output_path_flag_index + 1]

            if any(flag in payload['custom_flags'] for flag in ["--write-description", "--write-info-json"]):
                self.assertIn('%(title)s/%(title)s.%(ext)s', output_template,
                              msg="Output template should save to subfolder when extra files are requested")
            else:
                self.assertEqual(output_template, f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s')

    def test_partial_download_failure(self):
        payload = {
            "url": "https://www.youtube.com/playlist?list=PARTIAL_FAIL",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "download_options": {},
            "custom_flags": []
        }

        mock_lines = [
            "[download] Downloading playlist: PlaylistName",
            "[download] Playlist PlaylistName: Downloading 3 videos",
            "[download] Destination: video1.mp4",
            "ERROR: video2 unavailable",
            "[download] Destination: video3.mp4",
            "[DONE]"
        ]

        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(mock_lines)
            mock_popen.return_value = mock_proc

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Download started", response.get_json()["message"])

    def test_no_duplicate_flags(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=duplicateflag",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {
                "description": True
            },
            "custom_flags": ["--write-description"]
        }

        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)

            called_args = mock_popen.call_args[0][0]
            self.assertEqual(called_args.count("--write-description"), 1)
