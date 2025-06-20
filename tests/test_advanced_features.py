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

    def test_single_video_has_separate_metadata_folder(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=video123",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {},
            "custom_flags": ["--write-description", "--write-info-json"]
        }

        # Simulated yt-dlp output
        mock_lines = [
            f"[download] Destination: {DOWNLOAD_FOLDER}/Video1.mp4",
            f"[info] Writing video description to: {DOWNLOAD_FOLDER}/Video1/Video1.description",
            f"[info] Writing metadata to: {DOWNLOAD_FOLDER}/Video1/Video1.info.json",
            "[DONE]"
        ]

        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(mock_lines)
            mock_popen.return_value = mock_proc

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Download started", response.get_json()["message"])

            # Validate correct output structure in command
            called_args = mock_popen.call_args[0][0]
            output_flag_index = called_args.index('-o')
            output_template = called_args[output_flag_index + 1]

            self.assertEqual(output_template, f'{DOWNLOAD_FOLDER}/%(title)s/%(title)s.%(ext)s')
            self.assertIn('--paths', called_args)
            self.assertIn(f'description:{DOWNLOAD_FOLDER}/%(title)s', called_args)
            self.assertIn(f'infojson:{DOWNLOAD_FOLDER}/%(title)s', called_args)

    def test_playlist_video_has_separate_metadata_folders(self):
        payload = {
            "url": "https://www.youtube.com/playlist?list=xyz123",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {},
            "custom_flags": ["--write-description", "--write-info-json"]
        }

        # Simulated yt-dlp output
        mock_lines = [
            f"[download] Destination: {DOWNLOAD_FOLDER}/Playlist1/Video2.mp4",
            f"[info] Writing video description to: {DOWNLOAD_FOLDER}/Playlist1/Video2/Video2.description",
            f"[info] Writing metadata to: {DOWNLOAD_FOLDER}/Playlist1/Video2/Video2.info.json",
            f"[download] Destination: {DOWNLOAD_FOLDER}/Playlist1/Video3.mp4",
            f"[info] Writing video description to: {DOWNLOAD_FOLDER}/Playlist1/Video3/Video3.description",
            f"[info] Writing metadata to: {DOWNLOAD_FOLDER}/Playlist1/Video3/Video3.info.json",
            f"[info] Writing playlist metadata to: {DOWNLOAD_FOLDER}/Playlist1/Playlist1.description",
            "[DONE]"
        ]

        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(mock_lines)
            mock_popen.return_value = mock_proc

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Download started", response.get_json()["message"])

            # Validate correct output structure in command
            called_args = mock_popen.call_args[0][0]
            output_flag_index = called_args.index('-o')
            output_template = called_args[output_flag_index + 1]

            self.assertEqual(output_template, f'{DOWNLOAD_FOLDER}/%(playlist_title)s/%(title)s.%(ext)s')
            self.assertIn('--paths', called_args)
            self.assertIn(f'description:{DOWNLOAD_FOLDER}/%(playlist_title)s/%(title)s', called_args)
            self.assertIn(f'infojson:{DOWNLOAD_FOLDER}/%(playlist_title)s/%(title)s', called_args)
