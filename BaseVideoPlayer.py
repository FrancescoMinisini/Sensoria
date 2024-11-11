import sys
import os
import cv2
import numpy as np
import pandas as pd
import json
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QSplitter, QPushButton, QCheckBox, QSizePolicy, QApplication,
                             QAction, QFileDialog, QMessageBox, QComboBox, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QCursor
import pyqtgraph as pg
from platformdirs import user_data_dir, user_cache_dir

class BaseVideoPlayer(QMainWindow):
    def __init__(self, video_filePath=None, csv_filePath_right=None, csv_filePath_left=None):
        super().__init__()

        # Initialize main window
        self.setWindowTitle("Video Player with Interactive Graphs")
        self.setGeometry(100, 100, 1200, 900)
        self.setFocusPolicy(Qt.StrongFocus)

        # Set application icon
        self.setWindowIcon(QIcon('app_icon.png'))  # Ensure 'app_icon.png' exists

        # Theme variable (dark by default)
        self.theme = 'dark'

        # Playback speed variable
        self.playback_speed = 1.0

        # Configurations
        self.config = {}

        # Application data directory
        self.app_name = 'YourAppName'  # Replace with your app name
        self.app_data_dir = user_data_dir(self.app_name)
        self.app_cache_dir = user_cache_dir(self.app_name)

        # Ensure the data directories exist
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.app_cache_dir, exist_ok=True)

        # Central widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Initialize UI components
        self.setup_ui()

        # Apply theme to the application
        self.apply_theme()

        # Variables for synchronization
        self.sync_offset = 0.0  # In seconds
        self.sync_state = None  # Can be None, "video", or "data"

        # Load the last opened folder
        self.load_last_folder()

        # If video and CSV paths are provided, load them
        if video_filePath and csv_filePath_right and csv_filePath_left:
            self.load_video_and_data(video_filePath, [csv_filePath_right, csv_filePath_left])

    def setup_ui(self):
        # Create menu bar
        self.menu_bar = self.menuBar()

        # File menu
        self.file_menu = self.menu_bar.addMenu('File')

        # Open action
        open_action = QAction('Apri', self)
        open_action.triggered.connect(self.open_files)
        self.file_menu.addAction(open_action)

        # Switch CSV files action
        switch_csv_action = QAction('Scambia File CSV', self)
        switch_csv_action.triggered.connect(self.switch_csv_files)
        self.file_menu.addAction(switch_csv_action)

        # Options menu
        self.options_menu = self.menu_bar.addMenu('Opzioni')

        # Reset synchronization action
        reset_sync_action = QAction('Reimposta Sincronizzazione', self)
        reset_sync_action.triggered.connect(self.reset_synchronization)
        self.options_menu.addAction(reset_sync_action)

        # Reset settings action
        reset_settings_action = QAction('Reimposta Impostazioni Predefinite', self)
        reset_settings_action.triggered.connect(self.reset_settings)
        self.options_menu.addAction(reset_settings_action)

        # Toggle theme action
        toggle_theme_action = QAction('Tema Scuro/Chiaro', self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        self.options_menu.addAction(toggle_theme_action)

        # Central layout
        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Vertical trackbar
        self.trackbar = QSlider(Qt.Vertical, self)
        self.trackbar.setRange(0, 100)  # Temporary range until video is loaded
        self.trackbar.sliderReleased.connect(self.seek_video)
        self.trackbar.sliderMoved.connect(self.handle_slider_move)
        self.central_layout.addWidget(self.trackbar)

        # Layout for video and graphs
        self.video_graphs_layout = QVBoxLayout()
        self.central_layout.addLayout(self.video_graphs_layout)

        # Label for video display
        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_graphs_layout.addWidget(self.video_label)

        # Message to open a folder
        self.open_folder_label = QLabel("Per favore, apri una cartella per iniziare", self)
        self.open_folder_label.setAlignment(Qt.AlignCenter)
        self.open_folder_label.setStyleSheet("color: #F0F0F0; font-size: 16px; font-weight: bold;")
        self.video_graphs_layout.addWidget(self.open_folder_label)

        # Control panel
        self.control_panel = QWidget(self)
        self.control_layout = QHBoxLayout(self.control_panel)
        self.control_panel.setLayout(self.control_layout)
        self.video_graphs_layout.addWidget(self.control_panel)

        # Play button
        self.play_button = QPushButton("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.play_button.clicked.connect(self.toggle_playback)
        self.control_layout.addWidget(self.play_button)

        # Speed selector
        self.speed_selector = QComboBox(self)
        self.speed_selector.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_selector.setCurrentText("1x")
        self.speed_selector.currentTextChanged.connect(self.change_playback_speed)
        self.control_layout.addWidget(self.speed_selector)

        # Synchronization button with tooltip
        self.sync_button = QPushButton("Sincronizza")
        self.sync_button.setToolTip("Clicca per avviare il processo di sincronizzazione.")
        self.sync_button.clicked.connect(self.toggle_synchronization)
        self.control_layout.addWidget(self.sync_button)

        # Set sync point button (visible only during synchronization)
        self.set_sync_point_button = QPushButton("Imposta Punto di Sync")
        self.set_sync_point_button.setToolTip("Clicca per impostare il punto di sincronizzazione al frame video corrente.")
        self.set_sync_point_button.clicked.connect(self.set_sync_point_video)
        self.set_sync_point_button.hide()  # Hidden by default
        self.control_layout.addWidget(self.set_sync_point_button)

        # Spacer
        self.control_layout.addStretch()

        # Frame counter
        self.frame_counter = QLabel(f"Frame: 0/0", self)
        self.frame_counter.setObjectName("FrameCounter")
        self.control_layout.addWidget(self.frame_counter)

        # Synchronization status label
        self.sync_status_label = QLabel("", self)
        self.sync_status_label.setAlignment(Qt.AlignCenter)
        self.sync_status_label.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold;")
        self.sync_status_label.hide()  # Hidden by default
        self.video_graphs_layout.addWidget(self.sync_status_label)

        # Container for controls and graphs
        self.controls_and_graphs_container = QWidget(self)
        self.controls_and_graphs_layout = QVBoxLayout(self.controls_and_graphs_container)
        self.controls_and_graphs_container.setLayout(self.controls_and_graphs_layout)
        self.controls_and_graphs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_graphs_layout.addWidget(self.controls_and_graphs_container)

        # Layout for the right foot
        right_foot_layout = QHBoxLayout()
        self.right_label = QLabel("Piede Destro")
        self.right_label.setStyleSheet("font-weight: bold;")
        right_foot_layout.addWidget(self.right_label)

        self.checkboxes_right = []
        checkbox_labels_right = ["Accelerazioni Dx (Ax, Ay, Az)", "Giroscopio Dx (Gx, Gy, Gz)", "Pressione Dx (S0, S1, S2)"]
        for label in checkbox_labels_right:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            right_foot_layout.addWidget(checkbox)
            self.checkboxes_right.append(checkbox)

        self.controls_and_graphs_layout.addLayout(right_foot_layout)

        # Layout for the left foot
        left_foot_layout = QHBoxLayout()
        self.left_label = QLabel("Piede Sinistro")
        self.left_label.setStyleSheet("font-weight: bold;")
        left_foot_layout.addWidget(self.left_label)

        self.checkboxes_left = []
        checkbox_labels_left = ["Accelerazioni Sx (Ax, Ay, Az)", "Giroscopio Sx (Gx, Gy, Gz)", "Pressione Sx (S0, S1, S2)"]
        for label in checkbox_labels_left:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            left_foot_layout.addWidget(checkbox)
            self.checkboxes_left.append(checkbox)

        self.controls_and_graphs_layout.addLayout(left_foot_layout)

        # Vertical splitter for graphs
        self.graph_splitter = QSplitter(Qt.Vertical, self)
        self.graph_splitter.setHandleWidth(8)
        self.controls_and_graphs_layout.addWidget(self.graph_splitter)

        # Container for plotting widgets
        self.plot_widgets = []
        self.interactive_flags = []  # To track which graphs are interactive

        # Initialize plotting widgets for selected columns
        self.selected_columns = []

        # Apply theme to foot labels
        self.update_foot_labels_theme()

    def apply_theme(self):
        if self.theme == 'dark':
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())
        # Update foot labels based on the theme
        self.update_foot_labels_theme()

    def update_foot_labels_theme(self):
        if self.theme == 'dark':
            label_color = 'color: #F0F0F0;'
        else:
            label_color = 'color: #000000;'
        self.right_label.setStyleSheet(f"{label_color} font-weight: bold;")
        self.left_label.setStyleSheet(f"{label_color} font-weight: bold;")

    def get_dark_stylesheet(self):
        return """
            QMainWindow {
                background-color: #2E2E2E;
                color: #F0F0F0;
            }
            QLabel, QPushButton, QSlider, QCheckBox, QComboBox {
                background-color: #3E3E3E;
                color: #F0F0F0;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                font-size: 14px;
            }
            QLabel#FrameCounter {
                font-size: 12px;
                padding: 2px;
                width: 80px;
                font-weight: bold;
            }
            QSplitter::handle {
                background-color: #555555;
            }
        """

    def get_light_stylesheet(self):
        return """
            QMainWindow {
                background-color: #F0F0F0;
                color: #000000;
            }
            QLabel, QPushButton, QSlider, QCheckBox, QComboBox {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                font-size: 14px;
            }
            QLabel#FrameCounter {
                font-size: 12px;
                padding: 2px;
                width: 80px;
                font-weight: bold;
            }
            QSplitter::handle {
                background-color: #AAAAAA;
            }
        """

    def open_files(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Seleziona Cartella", "")
        if folder_path:
            self.open_folder(folder_path)

    def open_folder(self, folder_path):
        self.open_folder_label.hide()
        self.folder_path = folder_path  # Store folder path
        # Find video file and two CSV files in the folder
        video_file = None
        csv_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.mp4', '.avi', '.mov')):
                video_file = os.path.join(folder_path, file)
            elif file.lower().endswith('.csv'):
                csv_files.append(os.path.join(folder_path, file))
        if video_file and len(csv_files) == 2:
            # Reload video and data
            self.load_video_and_data(video_file, csv_files)
            # Save last opened folder
            self.save_last_folder(folder_path)
        else:
            QMessageBox.warning(self, "Errore", "La cartella deve contenere un file video e due file CSV.")

    def save_last_folder(self, folder_path):
        app_config_file = os.path.join(self.app_data_dir, 'app_config.json')
        try:
            app_config = {}
            if os.path.exists(app_config_file):
                with open(app_config_file, 'r') as f:
                    app_config = json.load(f)
            app_config['last_folder'] = folder_path
            with open(app_config_file, 'w') as f:
                json.dump(app_config, f)
        except Exception as e:
            print(f"Errore nel salvataggio dell'ultima cartella: {e}")

    def load_last_folder(self):
        app_config_file = os.path.join(self.app_data_dir, 'app_config.json')
        if os.path.exists(app_config_file):
            try:
                with open(app_config_file, 'r') as f:
                    app_config = json.load(f)
                    last_folder = app_config.get('last_folder')
                    if last_folder and os.path.exists(last_folder):
                        # Attempt to open the last folder
                        self.open_folder(last_folder)
            except Exception as e:
                print(f"Errore nel caricamento dell'ultima cartella: {e}")

    def load_video_and_data(self, video_filePath, csv_filePaths):
        # Store CSV file paths
        self.csv_filePaths = csv_filePaths.copy()

        # Close current video capture if present
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

        # Load video
        self.video_path = video_filePath
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file video: {self.video_path}")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_timestamps = np.arange(0, self.total_frames) / self.video_fps
        self.current_frame = 0
        self.trackbar.setRange(0, self.total_frames - 1)
        self.video_finished = False

        # Video playback control
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False

        # Load and preprocess data for plotting
        self.load_and_preprocess_data(csv_filePaths[0], csv_filePaths[1])

        # Load configuration if exists
        self.load_config()

        # Adjust layout based on video dimensions
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if width > height:
            # Horizontal video
            self.adjust_layout(Qt.Vertical)
        else:
            # Vertical video
            self.adjust_layout(Qt.Horizontal)

        # Update UI components
        self.show_first_frame()
        self.update_selected_columns()
        self.update_frame_counter()

    def adjust_layout(self, orientation):
        # Remove existing widgets if present
        if hasattr(self, 'main_splitter'):
            self.main_splitter.deleteLater()

        self.main_splitter = QSplitter(orientation, self.central_widget)

        # Add main splitter to central layout
        self.video_graphs_layout.addWidget(self.main_splitter)

        # Create container for video and control panel
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.addWidget(self.video_label)
        video_layout.addWidget(self.control_panel)

        self.main_splitter.addWidget(video_container)
        self.main_splitter.addWidget(self.controls_and_graphs_container)

    def load_and_preprocess_data(self, csv_filePath_right, csv_filePath_left):
        try:
            self.data_right = pd.read_csv(csv_filePath_right, skiprows=18)
            self.data_left = pd.read_csv(csv_filePath_left, skiprows=18)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i file CSV: {e}")
            return

        for data in [self.data_right, self.data_left]:
            # Convert Timestamp to datetime
            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
            data.dropna(subset=['Timestamp'], inplace=True)
            data['Timestamp'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
            data.sort_values('Timestamp', inplace=True)
            data.reset_index(drop=True, inplace=True)

            # Create 'VideoTime' initially equal to 'Timestamp'
            data['VideoTime'] = data['Timestamp']

        # Handle missing values
        self.data_right.interpolate(method='linear', inplace=True)
        self.data_left.interpolate(method='linear', inplace=True)

    def switch_csv_files(self):
        # Swap left and right data
        self.data_left, self.data_right = self.data_right, self.data_left
        # Swap CSV file paths
        self.csv_filePaths[0], self.csv_filePaths[1] = self.csv_filePaths[1], self.csv_filePaths[0]
        # Update graphs
        self.update_plot_widgets()
        # Save updated configuration
        self.save_config()

    def show_first_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_frame_counter()
            self.update_graphs()

    def toggle_playback(self):
        if self.video_finished:
            self.restart_video()
        if self.is_playing:
            self.timer.stop()
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
        else:
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
            self.play_button.setText("Pause")
            self.play_button.setIcon(QIcon("pause.png"))
        self.is_playing = not self.is_playing

    def change_playback_speed(self, speed_text):
        speed_factor = float(speed_text.replace('x', ''))
        self.playback_speed = speed_factor
        if self.is_playing:
            self.timer.stop()
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
        # Save updated configuration
        self.save_config()

    def seek_video(self):
        self.timer.stop()
        self.is_playing = False
        self.play_button.setText("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.current_frame = self.trackbar.value()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
        self.video_finished = False
        # Save updated configuration
        self.save_config()

    def handle_slider_move(self, position):
        self.current_frame = position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
        # Save updated configuration
        self.save_config()

    def update_frame_display(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))
        self.update_frame_counter()

    def update_frame_counter(self):
        self.frame_counter.setText(f"Frame: {self.current_frame}/{self.total_frames}")

    def restart_video(self):
        self.current_frame = 0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.trackbar.setValue(self.current_frame)
            self.update_frame_display(frame)
            self.update_graphs()
        self.video_finished = False
        self.play_button.setText("Pause")
        self.play_button.setIcon(QIcon("pause.png"))
        self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))

    def update_graphs(self):
        # Calculate current video timestamp considering offset
        current_video_time = self.video_timestamps[self.current_frame]

        # Apply time offset
        synced_time = current_video_time - self.sync_offset

        for i, (plot_widget, moving_points, columns, data) in enumerate(self.plot_widgets):
            synced_time_clipped = max(data['VideoTime'].min(), min(data['VideoTime'].max(), synced_time))
            closest_index = np.abs(data['VideoTime'] - synced_time_clipped).idxmin()

            x = data['VideoTime'].values[closest_index]

            # Update moving points for selected columns
            point_idx = 0
            for j, column in enumerate(plot_widget.all_columns):
                if column in plot_widget.selected_columns:
                    y = data[column].values[closest_index]
                    moving_points[point_idx].setData([x], [y])
                    point_idx += 1

    def toggle_synchronization(self):
        if self.sync_state is None:
            # Start synchronization
            self.sync_state = "video"
            self.sync_status_label.setText("Sincronizzazione: Naviga al frame desiderato e clicca 'Imposta Punto di Sync'")
            self.sync_status_label.show()
            self.set_sync_point_button.show()
            self.sync_button.setText("Annulla Sync")
        else:
            # Cancel synchronization
            self.sync_state = None
            self.sync_status_label.hide()
            self.set_sync_point_button.hide()
            self.sync_button.setText("Sincronizza")
            self.sync_video_time = None
            self.sync_data_time = None
            QApplication.restoreOverrideCursor()
            # Restore interactivity
            for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
                self.stop_interactivity(plot_widget, idx)

    def set_sync_point_video(self):
        if self.sync_state == "video":
            # Save current video timestamp as sync point
            self.sync_video_time = self.video_timestamps[self.current_frame]
            self.sync_state = "data"
            self.sync_status_label.setText("Sincronizzazione: Clicca sul grafico per impostare il punto di sincronizzazione dei dati")
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
            # Activate data point selection mode
            for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
                self.interactive_flags[idx] = True
                plot_widget.setMouseTracking(True)
                plot_widget.scene().sigMouseClicked.connect(
                    lambda event, widget=plot_widget, idx=idx: self.on_sync_data_point_selected(event, widget, idx)
                )
            self.set_sync_point_button.hide()

    def on_sync_data_point_selected(self, event, widget, idx):
        if self.sync_state != "data":
            return

        pos = event.scenePos()
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]
        # Find index closest to clicked point
        closest_index = np.abs(data['VideoTime'] - mouse_point.x()).idxmin()
        self.sync_data_time = data['VideoTime'].values[closest_index]

        # Disable interactivity for all graphs
        for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
            self.stop_interactivity(plot_widget, idx)
        QApplication.restoreOverrideCursor()
        self.sync_status_label.hide()
        self.sync_button.setText("Sincronizza")
        self.sync_state = None
        self.check_sync_ready()

    def check_sync_ready(self):
        # If both sync points are selected, calculate offset
        if self.sync_video_time is not None and self.sync_data_time is not None:
            self.sync_offset = self.sync_video_time - self.sync_data_time
            print(f"Offset di sincronizzazione impostato a {self.sync_offset} secondi")
            # Update graphs to reflect new synchronization
            self.update_graphs()
            # Reset sync points
            self.sync_video_time = None
            self.sync_data_time = None
            # Ensure playback can proceed
            self.is_playing = False
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
            # Save updated configuration
            self.save_config()

    def reset_synchronization(self):
        # Reset synchronization offset
        self.sync_offset = 0.0
        self.update_graphs()
        self.save_config()
        QMessageBox.information(self, "Sincronizzazione Reimpostata", "L'offset di sincronizzazione è stato reimpostato.")

    def reset_settings(self):
        # Ask for user confirmation
        reply = QMessageBox.question(self, 'Reimposta Impostazioni',
                                     'Sei sicuro di voler reimpostare tutte le impostazioni ai valori predefiniti?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Delete configuration file
            config_file = os.path.join(self.app_data_dir, 'config.json')
            if os.path.exists(config_file):
                os.remove(config_file)
            # Reset settings
            self.sync_offset = 0.0
            self.playback_speed = 1.0
            self.speed_selector.setCurrentText("1x")
            self.current_frame = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if ret:
                self.update_frame_display(frame)
                self.update_graphs()
            for checkbox in (self.checkboxes_right + self.checkboxes_left):
                checkbox.setChecked(False)
            self.update_selected_columns()
            self.save_config()
            QMessageBox.information(self, "Impostazioni Reimpostate", "Le impostazioni sono state reimpostate ai valori predefiniti.")

    def toggle_theme(self):
        if self.theme == 'dark':
            self.theme = 'light'
        else:
            self.theme = 'dark'
        self.apply_theme()
        # Update graphs
        for plot_widget, _, _, _ in self.plot_widgets:
            if self.theme == 'dark':
                plot_widget.setBackground('#2E2E2E')
                axis_color = '#F0F0F0'
            else:
                plot_widget.setBackground('#FFFFFF')
                axis_color = '#000000'
            plot_widget.getAxis('left').setPen(pg.mkPen(color=axis_color, width=1))
            plot_widget.getAxis('bottom').setPen(pg.mkPen(color=axis_color, width=1))
            plot_widget.getAxis('left').setTextPen(pg.mkPen(color=axis_color))
            plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color=axis_color))
        # Save updated configuration
        self.save_config()

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        try:
            widget.scene().sigMouseMoved.disconnect()
        except TypeError:
            pass  # Already disconnected

    def closeEvent(self, event):
        if hasattr(self, 'folder_path'):
            self.save_config()
        if hasattr(self, 'cap'):
            self.cap.release()
        event.accept()

    def next_frame(self):
        if not any(self.interactive_flags) and self.sync_state != "data":
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                self.trackbar.setValue(self.current_frame)
                self.update_frame_display(frame)
                self.update_graphs()
            else:
                self.timer.stop()
                self.is_playing = False
                self.play_button.setText("Play")
                self.play_button.setIcon(QIcon("play.png"))
                self.video_finished = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_Up:
            self.step_frame(1)
        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_Down:
            self.step_frame(-1)
        elif event.key() == Qt.Key_Space:
            self.toggle_playback()

    def step_frame(self, step):
        self.timer.stop()
        self.is_playing = False
        self.play_button.setText("Play")
        self.play_button.setIcon(QIcon("play.png"))

        self.current_frame = max(0, min(self.total_frames - 1, self.current_frame + step))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

        ret, frame = self.cap.read()
        if ret:
            self.trackbar.setValue(self.current_frame)
            self.update_frame_display(frame)
            self.update_graphs()
        self.update_frame_counter()
        self.video_finished = False
        # Save updated configuration
        self.save_config()

    def update_selected_columns(self):
        selected_columns = [checkbox.text() for checkbox in (self.checkboxes_right + self.checkboxes_left) if checkbox.isChecked()]
        if selected_columns != self.selected_columns:
            self.selected_columns = selected_columns
            self.update_plot_widgets()
            # Save updated configuration
            self.save_config()

    def update_plot_widgets(self):
        # Remove existing graphs
        for widget, _, _, _ in self.plot_widgets:
            widget.deleteLater()
        self.plot_widgets.clear()
        self.interactive_flags.clear()

        if not self.selected_columns:
            return

        # Update graphs for right foot
        if "Accelerazioni Dx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        if "Giroscopio Dx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        if "Pressione Dx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        # Update graphs for left foot
        if "Accelerazioni Sx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"], ["#FFA500", "#800080", "#008080"], self.data_left)

        if "Giroscopio Sx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FFA500", "#800080", "#008080"], self.data_left)

        if "Pressione Sx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"], ["#FFA500", "#800080", "#008080"], self.data_left)

    def create_plot_widget(self, columns, colors, data):
        plot_widget = pg.PlotWidget()
        if self.theme == 'dark':
            plot_widget.setBackground('#2E2E2E')
            axis_color = '#F0F0F0'
        else:
            plot_widget.setBackground('#FFFFFF')
            axis_color = '#000000'
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Create custom Y-axis labels in one line
        ylabel = ", ".join([f"<span style='color: {colors[i]};'>{column}</span>" for i, column in enumerate(columns)])

        plot_widget.setLabel('left', ylabel)
        plot_widget.setLabel('bottom', 'Tempo (s)')
        plot_widget.getAxis('left').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('left').setTextPen(pg.mkPen(color=axis_color))
        plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color=axis_color))
        self.graph_splitter.addWidget(plot_widget)

        # Store columns and data in plot_widget for future access
        plot_widget.all_columns = columns
        plot_widget.data = data
        plot_widget.selected_columns = columns.copy()  # Initially all columns are selected
        plot_widget.colors = colors

        # Access the ViewBox of the graph
        view_box = plot_widget.getViewBox()

        # Create a new QAction to select datapoints
        select_datapoints_action = QAction("Seleziona Datapoint", plot_widget)
        select_datapoints_action.triggered.connect(lambda: self.select_datapoints(plot_widget))

        # Add action to ViewBox context menu
        view_box.menu.addAction(select_datapoints_action)

        # Add plot_widget to layout and update plot_widgets list
        self.plot_widgets.append((plot_widget, [], columns, data))
        self.interactive_flags.append(False)

        # Plot initial data
        self.update_plot_widget(plot_widget)

        # Handle interactivity
        plot_widget.scene().sigMouseClicked.connect(
            lambda event, widget=plot_widget, idx=len(self.plot_widgets) - 1: self.toggle_interactivity(event, widget, idx)
        )

    def select_datapoints(self, plot_widget):
        # Create a dialog with checkboxes for each column
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleziona Datapoint")

        layout = QVBoxLayout()
        checkboxes = []
        for column in plot_widget.all_columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(column in plot_widget.selected_columns)
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        # Show dialog and wait for user input
        if dialog.exec_() == QDialog.Accepted:
            # Update selected columns based on user input
            plot_widget.selected_columns = [cb.text() for cb in checkboxes if cb.isChecked()]
            # Update graph
            self.update_plot_widget(plot_widget)

    def update_plot_widget(self, plot_widget):
        # Clear existing graphs
        plot_widget.clear()

        data = plot_widget.data
        selected_columns = plot_widget.selected_columns
        colors = plot_widget.colors

        moving_points = []

        # Re-plot selected columns
        for i, column in enumerate(plot_widget.all_columns):
            if column in selected_columns:
                color = colors[i]
                color = pg.mkColor(color)
                color.setAlpha(255)
                pen = pg.mkPen(color=color, width=2)
                plot = plot_widget.plot(data["VideoTime"].values, data[column].values, pen=pen)
                moving_point = plot_widget.plot([data["VideoTime"].values[0]], [data[column].values[0]],
                                                pen=None, symbol='o', symbolBrush=color)
                moving_points.append(moving_point)

        # Update moving points in plot_widgets
        for idx, (pw, _, cols, _) in enumerate(self.plot_widgets):
            if pw == plot_widget:
                self.plot_widgets[idx] = (plot_widget, moving_points, plot_widget.all_columns, data)
                break

    @pyqtSlot(object)
    def on_mouse_moved(self, pos, widget, idx):
        if self.sync_state == "data":
            return  # Avoid interference with sync mode

        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]  # Retrieve associated data
        # Apply synchronization offset
        synced_time = mouse_point.x() + self.sync_offset
        # Find corresponding video frame
        synced_time_clipped = max(0, min(self.video_timestamps[-1], synced_time))
        closest_frame = np.abs(self.video_timestamps - synced_time_clipped).argmin()
        self.current_frame = closest_frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
            self.trackbar.setValue(self.current_frame)

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        try:
            widget.scene().sigMouseMoved.disconnect()
        except TypeError:
            pass  # Already disconnected

    def toggle_interactivity(self, event, widget, idx):
        if self.sync_state == "data":
            return  # Avoid interference with sync mode

        if not self.interactive_flags[idx]:
            self.interactive_flags[idx] = True
            widget.setMouseTracking(True)
            widget.scene().sigMouseMoved.connect(lambda pos, widget=widget, idx=idx: self.on_mouse_moved(pos, widget, idx))
        else:
            self.stop_interactivity(widget, idx)

    def load_config(self):
        config_file = os.path.join(self.app_data_dir, 'config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            # Set settings from configuration
            self.sync_offset = float(self.config.get('sync_offset', 0.0))
            self.playback_speed = float(self.config.get('playback_speed', 1.0))
            # Set speed selector
            speed_text = f"{self.playback_speed}x"
            if speed_text in [self.speed_selector.itemText(i) for i in range(self.speed_selector.count())]:
                self.speed_selector.setCurrentText(speed_text)
            else:
                self.speed_selector.addItem(speed_text)
                self.speed_selector.setCurrentText(speed_text)
            # Set current frame
            self.current_frame = int(self.config.get('current_frame', 0))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            # Update video display
            ret, frame = self.cap.read()
            if ret:
                self.update_frame_display(frame)
                self.update_graphs()

            # Update CSV file paths based on configuration
            right_csv = self.config.get('right_csv')
            left_csv = self.config.get('left_csv')
            if right_csv and left_csv:
                self.csv_filePaths[0] = os.path.join(self.folder_path, right_csv)
                self.csv_filePaths[1] = os.path.join(self.folder_path, left_csv)
                self.load_and_preprocess_data(self.csv_filePaths[0], self.csv_filePaths[1])

            # Set selected columns
            selected_columns = self.config.get('selected_columns', [])
            for checkbox in (self.checkboxes_right + self.checkboxes_left):
                if checkbox.text() in selected_columns:
                    checkbox.setChecked(True)
                else:
                    checkbox.setChecked(False)
            # Update graphs
            self.update_selected_columns()
            # Set theme
            self.theme = self.config.get('theme', 'dark')
            self.apply_theme()
        else:
            self.config = {}

    def save_config(self):
        config_file = os.path.join(self.app_data_dir, 'config.json')
        self.config['sync_offset'] = float(self.sync_offset)
        self.config['playback_speed'] = float(self.playback_speed)
        self.config['current_frame'] = int(self.current_frame)
        self.config['selected_columns'] = [checkbox.text() for checkbox in (self.checkboxes_right + self.checkboxes_left) if checkbox.isChecked()]
        # Store which CSVs are assigned to feet
        self.config['right_csv'] = os.path.basename(self.csv_filePaths[0])
        self.config['left_csv'] = os.path.basename(self.csv_filePaths[1])
        # Save current theme
        self.config['theme'] = self.theme
        # Convert all values to standard types to avoid issues with JSON
        def convert_types(obj):
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            else:
                return obj

        config_to_save = convert_types(self.config)

        with open(config_file, 'w') as f:
            json.dump(config_to_save, f, indent=4)

    @staticmethod
    def extract_sensor_rate(csv_filePath):
        sensor_rate = None
        with open(csv_filePath, 'r') as f:
            for line in f:
                if "SamplingFrequency" in line:
                    # Extract value after 'SamplingFrequency:'
                    sensor_rate = int(line.split(":")[1].strip())
                    break

        if sensor_rate is None:
            raise ValueError("SamplingFrequency non trovato nell'header del file.")
        return sensor_rate
