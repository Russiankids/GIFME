import sys
import os
import subprocess

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit,
    QFileDialog, QLabel, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Define a worker thread for video conversion to keep the GUI responsive
class VideoConverterWorker(QThread):
    # Signals to communicate with the main thread
    progress_update = pyqtSignal(str)
    conversion_finished = pyqtSignal(str)
    conversion_error = pyqtSignal(str)

    def __init__(self, directory_path):
        super().__init__()
        self.directory_path = directory_path
        self.video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv')

    def run(self):
        # Check if ffmpeg is available
        if not self._is_ffmpeg_installed():
            self.conversion_error.emit("FFmpeg is not installed or not in your system's PATH.\n"
                                       "Please install FFmpeg to use this converter.")
            return

        converted_count = 0
        total_videos = 0
        video_files = []

        # First pass to count total videos and collect their paths
        for filename in os.listdir(self.directory_path):
            if filename.lower().endswith(self.video_extensions):
                video_files.append(filename)
                total_videos += 1

        if total_videos == 0:
            self.progress_update.emit("No video files found in the selected directory.")
            self.conversion_finished.emit("Conversion process completed (no videos to convert).")
            return

        self.progress_update.emit(f"Found {total_videos} video(s). Starting conversion...")

        # Second pass to convert each video
        for i, filename in enumerate(video_files):
            input_path = os.path.join(self.directory_path, filename)
            # Create a GIF filename by changing the extension
            output_filename = os.path.splitext(filename)[0] + '.gif'
            output_path = os.path.join(self.directory_path, output_filename)

            self.progress_update.emit(f"Converting '{filename}' ({i + 1}/{total_videos})...")

            try:
                # FFmpeg command for video to GIF conversion
                # -i: input file
                # -vf: video filter graph
                #   fps=10: sets output framerate to 10 frames per second (adjust for size/quality)
                #   scale=320:-1: resizes to 320px width, maintaining aspect ratio (-1 means auto)
                #   flags=lanczos: high-quality scaling algorithm
                # -y: overwrite output file if it already exists
                command = [
                    'ffmpeg',
                    '-i', input_path,
                    '-vf', 'fps=10,scale=320:-1:flags=lanczos',
                    '-y',  # Overwrite output file if it exists
                    output_path
                ]
                # Execute the command, capture output for debugging if needed
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                converted_count += 1
                self.progress_update.emit(f"Successfully converted '{filename}' to '{output_filename}'.")
            except subprocess.CalledProcessError as e:
                self.progress_update.emit(f"Error converting '{filename}': {e.stderr}")
                self.conversion_error.emit(f"Failed to convert '{filename}'. Error: {e.stderr}")
            except FileNotFoundError:
                self.conversion_error.emit("FFmpeg command not found. Please ensure FFmpeg is installed and in your PATH.")
                return # Stop further processing if ffmpeg is not found

        self.conversion_finished.emit(f"Conversion process completed. Converted {converted_count} of {total_videos} videos.")

    def _is_ffmpeg_installed(self):
        """Checks if ffmpeg is installed and accessible."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

class VideoConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video to GIF Converter")
        self.setGeometry(100, 100, 600, 400) # x, y, width, height

        self.directory_path = ""
        self.worker_thread = None

        self._init_ui()

    def _init_ui(self):
        # Main vertical layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Set window icon (add this after setting the layout)
        self.setWindowIcon(QIcon('LOL.ico'))

        # Instructions label
        self.instructions_label = QLabel("Select a directory containing videos to convert to GIF:")
        self.instructions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instructions_label)

        # Line edit to display selected directory path
        self.path_display = QLineEdit()
        self.path_display.setPlaceholderText("No directory selected")
        self.path_display.setReadOnly(True) # Make it read-only
        layout.addWidget(self.path_display)

        # Button to browse for directory
        self.browse_button = QPushButton("Browse Directory")
        self.browse_button.clicked.connect(self._browse_directory)
        layout.addWidget(self.browse_button)

        # Button to start conversion (initially disabled)
        self.convert_button = QPushButton("Start Conversion")
        self.convert_button.clicked.connect(self._start_conversion)
        self.convert_button.setEnabled(False) # Disable until a directory is selected
        layout.addWidget(self.convert_button)

        # Text area for logging messages
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Conversion logs will appear here...")
        layout.addWidget(self.log_output)

        # Status label at the bottom
        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.status_label)

    def _browse_directory(self):
        # Open a directory selection dialog
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.directory_path = directory
            self.path_display.setText(self.directory_path)
            self.convert_button.setEnabled(True) # Enable convert button
            self.log_output.clear()
            self.log_output.append(f"Directory selected: {self.directory_path}")
            self.status_label.setText("Directory selected. Click 'Start Conversion'.")
        else:
            self.directory_path = ""
            self.path_display.clear()
            self.convert_button.setEnabled(False)
            self.log_output.append("No directory selected.")
            self.status_label.setText("Ready.")

    def _start_conversion(self):
        if not self.directory_path:
            QMessageBox.warning(self, "No Directory", "Please select a directory first.")
            return

        # Disable buttons during conversion
        self.browse_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.log_output.clear()
        self.log_output.append("Starting video conversion process...")
        self.status_label.setText("Conversion in progress...")

        # Create and start the worker thread
        self.worker_thread = VideoConverterWorker(self.directory_path)
        self.worker_thread.progress_update.connect(self._update_log)
        self.worker_thread.conversion_finished.connect(self._conversion_finished)
        self.worker_thread.conversion_error.connect(self._conversion_error)
        self.worker_thread.start()

    def _update_log(self, message):
        self.log_output.append(message)
        # Scroll to the bottom to show latest messages
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def _conversion_finished(self, message):
        self._update_log(message)
        self.browse_button.setEnabled(True)
        # Re-enable convert button only if a directory is still selected
        if self.directory_path:
            self.convert_button.setEnabled(True)
        self.status_label.setText("Conversion complete.")
        QMessageBox.information(self, "Conversion Complete", message)

    def _conversion_error(self, message):
        self._update_log(f"ERROR: {message}")
        self.browse_button.setEnabled(True)
        if self.directory_path:
            self.convert_button.setEnabled(True)
        self.status_label.setText("Conversion failed.")
        QMessageBox.critical(self, "Conversion Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoConverterApp()
    window.show()
    sys.exit(app.exec())
