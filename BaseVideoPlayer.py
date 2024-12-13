import sys
import os
import cv2
import numpy as np
import pandas as pd
import json
import hashlib
import random
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QPointF, QRectF
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QSlider, QSplitter, QPushButton,
                             QCheckBox, QSizePolicy, QApplication, QAction,
                             QFileDialog, QMessageBox, QComboBox, QDialog,
                             QDialogButtonBox, QListWidget, QGridLayout,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QCursor
import pyqtgraph as pg
from platformdirs import user_data_dir, user_cache_dir

class BaseVideoPlayer(QMainWindow):
    def __init__(self, video_filePath=None, csv_filePath_right=None, csv_filePath_left=None):
        super().__init__()

        self.setWindowTitle("Video Player con Grafici Interattivi")
        self.setGeometry(100, 100, 1200, 900)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowIcon(QIcon('app_icon.png'))  # Assicurati che esista

        self.theme = 'dark'
        self.playback_speed = 1.0
        self.config = {}

        self.app_name = 'DVSS'
        self.app_data_dir = user_data_dir(self.app_name)
        self.app_cache_dir = user_cache_dir(self.app_name)
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.app_cache_dir, exist_ok=True)

        self.step_markers_right = []
        self.step_markers_left = []
        self.emiciclo_markers_right = []
        self.emiciclo_markers_left = []
        self.show_steps = True
        self.current_frame = 0

        # Variabile per layout del video: 'vertical' o 'horizontal' o None
        self.video_layout_orientation = None

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.setFocus()

        self.setup_ui()
        self.apply_theme()

        self.sync_offset = 0.0
        self.sync_state = None

        self.load_last_folder()

        if video_filePath and csv_filePath_right and csv_filePath_left:
            self.load_video_and_data(video_filePath, [csv_filePath_right, csv_filePath_left])

    def setup_ui(self):
        self.menu_bar = self.menuBar()

        # Menu File
        self.file_menu = self.menu_bar.addMenu('File')

        open_action = QAction('Apri', self)
        open_action.triggered.connect(self.open_files)
        self.file_menu.addAction(open_action)

        switch_csv_action = QAction('Scambia File CSV', self)
        switch_csv_action.triggered.connect(self.switch_csv_files)
        self.file_menu.addAction(switch_csv_action)

        generate_csv_action = QAction('Genera CSV per Passi', self)
        generate_csv_action.triggered.connect(self.generate_csv_for_steps)
        self.file_menu.addAction(generate_csv_action)

        # Menu Opzioni
        self.options_menu = self.menu_bar.addMenu('Opzioni')

        reset_sync_action = QAction('Reimposta Sincronizzazione', self)
        reset_sync_action.triggered.connect(self.reset_synchronization)
        self.options_menu.addAction(reset_sync_action)

        reset_settings_action = QAction('Reimposta Impostazioni Predefinite', self)
        reset_settings_action.triggered.connect(self.reset_settings)
        self.options_menu.addAction(reset_settings_action)

        toggle_theme_action = QAction('Tema Scuro/Chiaro', self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        self.options_menu.addAction(toggle_theme_action)

        # Sottomenu per layout video
        layout_menu = self.options_menu.addMenu("Layout Video")

        self.layout_vertical_action = QAction('Layout Verticale', self)
        self.layout_vertical_action.setCheckable(True)
        self.layout_vertical_action.triggered.connect(self.set_layout_vertical)

        self.layout_horizontal_action = QAction('Layout Orizzontale', self)
        self.layout_horizontal_action.setCheckable(True)
        self.layout_horizontal_action.triggered.connect(self.set_layout_horizontal)

        layout_menu.addAction(self.layout_vertical_action)
        layout_menu.addAction(self.layout_horizontal_action)

        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.trackbar = QSlider(Qt.Vertical, self)
        self.trackbar.setRange(0, 100)
        self.trackbar.sliderReleased.connect(self.seek_video)
        self.trackbar.sliderMoved.connect(self.handle_slider_move)
        self.central_layout.addWidget(self.trackbar)

        self.video_graphs_layout = QVBoxLayout()
        self.central_layout.addLayout(self.video_graphs_layout)

        self.video_widget = QWidget(self)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_graphs_layout.addWidget(self.video_widget)

        self.video_layout = QGridLayout(self.video_widget)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_layout.setSpacing(0)

        self.graphics_scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.graphics_scene, self.video_widget)
        self.graphics_view.setAlignment(Qt.AlignCenter)
        self.video_layout.addWidget(self.graphics_view, 0, 0)

        self.open_folder_label = QLabel("Per favore, apri una cartella per iniziare", self.video_widget)
        self.open_folder_label.setAlignment(Qt.AlignCenter)
        self.open_folder_label.setStyleSheet(
            "color: #F0F0F0; font-size: 16px; font-weight: bold; background-color: rgba(0, 0, 0, 128);")
        self.video_layout.addWidget(self.open_folder_label, 0, 0, Qt.AlignCenter)

        self.sync_status_label = QLabel("", self.video_widget)
        self.sync_status_label.setAlignment(Qt.AlignCenter)
        self.sync_status_label.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold; background-color: rgba(0,0,0,128);")
        self.sync_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sync_status_label.hide()
        self.video_layout.addWidget(self.sync_status_label, 0, 0, Qt.AlignTop | Qt.AlignHCenter)

        self.mouse_timestamp_label = QLabel("", self.video_widget)
        self.mouse_timestamp_label.setAlignment(Qt.AlignRight)
        self.mouse_timestamp_label.setStyleSheet("color: #FFD700; font-size: 12px; background-color: rgba(0,0,0,128);")
        self.mouse_timestamp_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.mouse_timestamp_label.hide()
        self.video_layout.addWidget(self.mouse_timestamp_label, 0, 0, Qt.AlignBottom | Qt.AlignRight)

        self.control_panel = QWidget(self)
        self.control_layout = QHBoxLayout(self.control_panel)
        self.control_panel.setLayout(self.control_layout)
        self.video_graphs_layout.addWidget(self.control_panel)

        self.play_button = QPushButton("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.play_button.setMinimumWidth(80)
        self.control_layout.addWidget(self.play_button)

        self.speed_selector = QComboBox(self)
        self.speed_selector.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_selector.setCurrentText("1x")
        self.speed_selector.currentTextChanged.connect(self.change_playback_speed)
        self.control_layout.addWidget(self.speed_selector)

        self.sync_button = QPushButton("Sincronizza")
        self.sync_button.setToolTip("Clicca per avviare il processo di sincronizzazione.")
        self.sync_button.clicked.connect(self.toggle_synchronization)
        self.control_layout.addWidget(self.sync_button)

        self.cancel_sync_button = QPushButton("Annulla Sync")
        self.cancel_sync_button.setToolTip("Clicca per annullare la sincronizzazione.")
        self.cancel_sync_button.clicked.connect(self.toggle_synchronization)
        self.cancel_sync_button.hide()

        self.set_sync_point_button = QPushButton("Imposta Punto di Sync")
        self.set_sync_point_button.setToolTip("Clicca per impostare il punto di sincronizzazione.")
        self.set_sync_point_button.clicked.connect(self.set_sync_point_video)
        self.set_sync_point_button.hide()

        self.add_step_marker_button = QPushButton("Aggiungi Marker Passo")
        self.add_step_marker_button.setToolTip("Clicca per aggiungere un marker al timestamp corrente.")
        self.add_step_marker_button.clicked.connect(lambda: self.add_step_marker())
        self.control_layout.addWidget(self.add_step_marker_button)

        self.control_layout.addStretch()

        self.frame_counter = QLabel("Frame: 0/0", self)
        self.frame_counter.setObjectName("FrameCounter")
        self.control_layout.addWidget(self.frame_counter)

        self.controls_and_graphs_container = QWidget(self)
        self.controls_and_graphs_layout = QVBoxLayout(self.controls_and_graphs_container)
        self.controls_and_graphs_container.setLayout(self.controls_and_graphs_layout)
        self.controls_and_graphs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_graphs_layout.addWidget(self.controls_and_graphs_container)

        right_foot_layout = QHBoxLayout()
        self.right_label = QLabel("Piede Destro")
        self.right_label.setStyleSheet("font-weight: bold;")
        right_foot_layout.addWidget(self.right_label)

        self.checkboxes_right = []
        checkbox_labels_right = ["Accelerazioni Dx (Ax, Ay, Az)",
                                 "Giroscopio Dx (Gx, Gy, Gz)",
                                 "Pressione Dx (S0, S1, S2)"]
        for label in checkbox_labels_right:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            right_foot_layout.addWidget(checkbox)
            self.checkboxes_right.append(checkbox)

        self.controls_and_graphs_layout.addLayout(right_foot_layout)

        left_foot_layout = QHBoxLayout()
        self.left_label = QLabel("Piede Sinistro")
        self.left_label.setStyleSheet("font-weight: bold;")
        left_foot_layout.addWidget(self.left_label)

        self.checkboxes_left = []
        checkbox_labels_left = ["Accelerazioni Sx (Ax, Ay, Az)",
                                "Giroscopio Sx (Gx, Gy, Gz)",
                                "Pressione Sx (S0, S1, S2)"]
        for label in checkbox_labels_left:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            left_foot_layout.addWidget(checkbox)
            self.checkboxes_left.append(checkbox)

        self.controls_and_graphs_layout.addLayout(left_foot_layout)

        self.graph_splitter = QSplitter(Qt.Vertical, self)
        self.graph_splitter.setHandleWidth(8)
        self.controls_and_graphs_layout.addWidget(self.graph_splitter)

        self.plot_widgets = []
        self.interactive_flags = []
        self.selected_columns = []
        self.update_foot_labels_theme()

        self.zoom_factor = 1.0
        self.graphics_view.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.graphics_view.setResizeAnchor(QGraphicsView.NoAnchor)
        self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.graphics_view.viewport().installEventFilter(self)
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def set_layout_vertical(self):
        self.video_layout_orientation = 'vertical'
        self.layout_vertical_action.setChecked(True)
        self.layout_horizontal_action.setChecked(False)
        self.adjust_layout(Qt.Horizontal)
        self.save_config()

    def set_layout_horizontal(self):
        self.video_layout_orientation = 'horizontal'
        self.layout_vertical_action.setChecked(False)
        self.layout_horizontal_action.setChecked(True)
        self.adjust_layout(Qt.Vertical)
        self.save_config()

    def adjust_layout(self, orientation):
        if hasattr(self, 'main_splitter'):
            self.main_splitter.deleteLater()

        self.main_splitter = QSplitter(orientation, self.central_widget)
        self.video_graphs_layout.addWidget(self.main_splitter)

        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.addWidget(self.video_widget)
        video_layout.addWidget(self.control_panel)

        self.main_splitter.addWidget(video_container)
        self.main_splitter.addWidget(self.controls_and_graphs_container)

    def load_video_and_data(self, video_filePath, csv_filePaths):
        self.csv_filePaths = csv_filePaths.copy()

        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False

        self.load_and_preprocess_data(self.csv_filePaths[0], self.csv_filePaths[1])
        self.load_config()

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Se l'utente non ha mai scelto un layout, decidi automaticamente
        if self.video_layout_orientation is None:
            if width > height:
                # Video orizzontale => Vertical splitter
                self.adjust_layout(Qt.Vertical)
                self.video_layout_orientation = 'horizontal'
            else:
                # Video verticale => Horizontal splitter
                self.adjust_layout(Qt.Horizontal)
                self.video_layout_orientation = 'vertical'
            self.save_config()
        else:
            # Usa il layout salvato
            if self.video_layout_orientation == 'vertical':
                self.adjust_layout(Qt.Horizontal)
                self.layout_vertical_action.setChecked(True)
                self.layout_horizontal_action.setChecked(False)
            else:
                self.adjust_layout(Qt.Vertical)
                self.layout_vertical_action.setChecked(False)
                self.layout_horizontal_action.setChecked(True)

        self.show_first_frame()
        self.update_selected_columns()
        self.update_frame_counter()

    def load_and_preprocess_data(self, csv_filePath_right, csv_filePath_left):
        try:
            self.data_right = pd.read_csv(csv_filePath_right, skiprows=18)
            self.data_left = pd.read_csv(csv_filePath_left, skiprows=18)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i file CSV: {e}")
            return

        for data in [self.data_right, self.data_left]:
            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
            data.dropna(subset=['Timestamp'], inplace=True)
            data['Timestamp'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
            data.sort_values('Timestamp', inplace=True)
            data.reset_index(drop=True, inplace=True)
            data['VideoTime'] = data['Timestamp']

        self.data_right.interpolate(method='linear', inplace=True)
        self.data_left.interpolate(method='linear', inplace=True)

    def open_files(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Seleziona Cartella", "")
        if folder_path:
            self.open_folder(folder_path)

    def open_folder(self, folder_path):
        self.open_folder_label.hide()
        self.folder_path = folder_path
        video_file = None
        csv_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.mp4', '.avi', '.mov')):
                video_file = os.path.join(folder_path, file)
            elif file.lower().endswith('.csv'):
                csv_files.append(os.path.join(folder_path, file))
        if video_file and len(csv_files) >= 2:
            assigned_csv_files = random.sample(csv_files, 2)
            self.load_video_and_data(video_file, assigned_csv_files)
            self.save_last_folder(folder_path)
        else:
            QMessageBox.warning(self, "Errore", "La cartella deve contenere un file video e almeno due file CSV.")

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
                        self.open_folder(last_folder)
            except Exception as e:
                print(f"Errore nel caricamento dell'ultima cartella: {e}")

    def save_config(self):
        config_file = self.get_config_file_path()
        self.config['sync_offset'] = float(self.sync_offset)
        self.config['playback_speed'] = float(self.playback_speed)
        self.config['current_frame'] = int(self.current_frame)
        self.config['selected_columns'] = [checkbox.text() for checkbox in
                                           (self.checkboxes_right + self.checkboxes_left)
                                           if checkbox.isChecked()]
        self.config['right_csv'] = os.path.basename(self.csv_filePaths[0])
        self.config['left_csv'] = os.path.basename(self.csv_filePaths[1])
        self.config['theme'] = self.theme
        self.config['step_markers_right'] = self.step_markers_right
        self.config['step_markers_left'] = self.step_markers_left
        self.config['emiciclo_markers_right'] = self.emiciclo_markers_right
        self.config['emiciclo_markers_left'] = self.emiciclo_markers_left
        self.config['show_steps'] = self.show_steps

        # Salva l'orientamento del layout video
        if self.video_layout_orientation is not None:
            self.config['video_layout_orientation'] = self.video_layout_orientation

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

    def load_config(self):
        config_file = self.get_config_file_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)

            right_csv = self.config.get('right_csv')
            left_csv = self.config.get('left_csv')
            if right_csv and left_csv:
                self.csv_filePaths[0] = os.path.join(self.folder_path, right_csv)
                self.csv_filePaths[1] = os.path.join(self.folder_path, left_csv)
                self.load_and_preprocess_data(self.csv_filePaths[0], self.csv_filePaths[1])

            self.step_markers_right = self.config.get('step_markers_right', [])
            self.step_markers_left = self.config.get('step_markers_left', [])
            self.emiciclo_markers_right = self.config.get('emiciclo_markers_right', [])
            self.emiciclo_markers_left = self.config.get('emiciclo_markers_left', [])

            self.sync_offset = float(self.config.get('sync_offset', 0.0))
            self.playback_speed = float(self.config.get('playback_speed', 1.0))
            speed_text = f"{self.playback_speed}x"
            items = [self.speed_selector.itemText(i) for i in range(self.speed_selector.count())]
            if speed_text in items:
                self.speed_selector.setCurrentText(speed_text)
            else:
                self.speed_selector.addItem(speed_text)
                self.speed_selector.setCurrentText(speed_text)

            self.current_frame = int(self.config.get('current_frame', 0))
            if hasattr(self, 'cap'):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.cap.read()
                if ret:
                    self.update_frame_display(frame)

            selected_columns = self.config.get('selected_columns', [])
            for checkbox in (self.checkboxes_right + self.checkboxes_left):
                checkbox.setChecked(checkbox.text() in selected_columns)

            self.theme = self.config.get('theme', 'dark')
            self.apply_theme()

            self.show_steps = self.config.get('show_steps', True)

            # Carica orientamento layout video se presente
            self.video_layout_orientation = self.config.get('video_layout_orientation', None)
        else:
            self.config = {}
            self.step_markers_right = []
            self.step_markers_left = []
            self.emiciclo_markers_right = []
            self.emiciclo_markers_left = []
            self.video_layout_orientation = None

    def get_folder_hash(self):
        return hashlib.md5(self.folder_path.encode('utf-8')).hexdigest()

    def get_config_file_path(self):
        folder_hash = self.get_folder_hash()
        config_file = os.path.join(self.app_data_dir, f'config_{folder_hash}.json')
        return config_file

    @staticmethod
    def extract_sensor_rate(csv_filePath):
        sensor_rate = None
        with open(csv_filePath, 'r') as f:
            for line in f:
                if "SamplingFrequency" in line:
                    sensor_rate = int(line.split(":")[1].strip())
                    break
        if sensor_rate is None:
            raise ValueError("SamplingFrequency non trovato nell'header del file.")
        return sensor_rate

    def apply_theme(self):
        if self.theme == 'dark':
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())
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

    def seek_video(self):
        self.timer.stop()
        self.is_playing = False
        self.play_button.setText("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.current_frame = self.trackbar.value()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
        self.video_finished = False
        self.save_config()

    def handle_slider_move(self, position):
        self.current_frame = position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
        self.save_config()

    def update_frame_display(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.graphics_scene.clear()
        self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
        self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
        self.update_frame_counter()

    def update_frame_counter(self):
        self.frame_counter.setText(f"Frame: {self.current_frame}/{self.total_frames}")

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
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
            self.play_button.setText("Pause")
            self.play_button.setIcon(QIcon("pause.png"))
            self.play_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.is_playing = not self.is_playing

    def change_playback_speed(self, speed_text):
        speed_factor = float(speed_text.replace('x', ''))
        self.playback_speed = speed_factor
        if self.is_playing:
            self.timer.stop()
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
        self.save_config()

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
        self.play_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))

    def update_graphs(self):
        current_video_time = self.video_timestamps[self.current_frame]
        synced_time = current_video_time - self.sync_offset

        for i, (plot_widget, moving_points, columns, data) in enumerate(self.plot_widgets):
            synced_time_clipped = max(data['VideoTime'].min(), min(data['VideoTime'].max(), synced_time))
            closest_index = np.abs(data['VideoTime'] - synced_time_clipped)
            closest_index = closest_index.idxmin()

            x = data['VideoTime'].values[closest_index]

            point_idx = 0
            for j, column in enumerate(plot_widget.all_columns):
                if column in plot_widget.selected_columns:
                    y = data[column].values[closest_index]
                    plot_widget.moving_points[point_idx].setData([x], [y])
                    point_idx += 1

    def update_markers(self, plot_widget):
        for line in plot_widget.step_marker_lines + plot_widget.emiciclo_marker_lines:
            plot_widget.removeItem(line)
        plot_widget.step_marker_lines = []
        plot_widget.emiciclo_marker_lines = []

        for region in plot_widget.step_regions + plot_widget.emiciclo_regions:
            plot_widget.removeItem(region)
        plot_widget.step_regions = []
        plot_widget.emiciclo_regions = []

        for label in plot_widget.step_labels + plot_widget.emiciclo_labels:
            plot_widget.removeItem(label)
        plot_widget.step_labels = []
        plot_widget.emiciclo_labels = []

        foot = plot_widget.foot
        if foot == 'right':
            step_markers = sorted(self.step_markers_right)
            emiciclo_markers = sorted(self.emiciclo_markers_right)
        else:
            step_markers = sorted(self.step_markers_left)
            emiciclo_markers = sorted(self.emiciclo_markers_left)

        for timestamp in step_markers:
            line = pg.InfiniteLine(pos=timestamp, angle=90, pen=pg.mkPen(color='yellow', style=Qt.DashLine, width=2))
            plot_widget.addItem(line)
            plot_widget.step_marker_lines.append(line)

        for timestamp in emiciclo_markers:
            line = pg.InfiniteLine(pos=timestamp, angle=90, pen=pg.mkPen(color='green', style=Qt.DashDotLine, width=2))
            plot_widget.addItem(line)
            plot_widget.emiciclo_marker_lines.append(line)

        if self.show_steps:
            if step_markers:
                if step_markers[0] > 0:
                    step_markers.insert(0, 0)

                for i in range(len(step_markers) - 1):
                    start_time = step_markers[i]
                    end_time = step_markers[i + 1]

                    color = (255, 0, 0, 50) if foot == 'right' else (0, 0, 255, 50)
                    region = pg.LinearRegionItem(values=(start_time, end_time), brush=pg.mkBrush(color=color))
                    plot_widget.addItem(region)
                    plot_widget.step_regions.append(region)

                    label_pos = (start_time + end_time) / 2
                    y_min, y_max = plot_widget.getAxis('left').range
                    label = pg.TextItem(text=f"Passo {i+1}", color='w', anchor=(0.5, 1))
                    label.setPos(label_pos, y_max)
                    plot_widget.addItem(label)
                    plot_widget.step_labels.append(label)

                last_marker = step_markers[-1]
                data_max_time = plot_widget.data['VideoTime'].max()
                if last_marker < data_max_time:
                    start_time = last_marker
                    end_time = data_max_time
                    color = (255, 0, 0, 50) if foot == 'right' else (0, 0, 255, 50)
                    region = pg.LinearRegionItem(values=(start_time, end_time), brush=pg.mkBrush(color=color))
                    plot_widget.addItem(region)
                    plot_widget.step_regions.append(region)

                    label_pos = (start_time + end_time) / 2
                    y_min, y_max = plot_widget.getAxis('left').range
                    label = pg.TextItem(text=f"Passo {len(step_markers)}", color='w', anchor=(0.5, 1))
                    label.setPos(label_pos, y_max)
                    plot_widget.addItem(label)
                    plot_widget.step_labels.append(label)

            # Nota: Nessun aggiunta di regioni verdi tra emicicli (rimosso come richiesto)

    def toggle_step_visualization(self):
        self.show_steps = not self.show_steps
        for plot_widget, _, _, _ in self.plot_widgets:
            self.update_markers(plot_widget)
            self.update_toggle_steps_action(plot_widget)
        self.save_config()

    def update_toggle_steps_action(self, plot_widget):
        if self.show_steps:
            plot_widget.toggle_steps_action.setText("Disattiva Visualizzazione Passi")
        else:
            plot_widget.toggle_steps_action.setText("Attiva Visualizzazione Passi")

    def toggle_synchronization(self):
        if self.sync_state is None:
            self.sync_state = "video"
            self.sync_status_label.setText("Sincronizzazione: Naviga al frame desiderato e clicca 'Imposta Punto di Sync'")
            self.sync_status_label.show()
            self.control_layout.removeWidget(self.sync_button)
            self.sync_button.hide()
            self.control_layout.insertWidget(2, self.cancel_sync_button)
            self.cancel_sync_button.show()
            self.control_layout.removeWidget(self.add_step_marker_button)
            self.add_step_marker_button.hide()
            self.control_layout.insertWidget(3, self.set_sync_point_button)
            self.set_sync_point_button.show()
        else:
            self.sync_state = None
            self.sync_status_label.hide()
            self.control_layout.removeWidget(self.cancel_sync_button)
            self.cancel_sync_button.hide()
            self.control_layout.insertWidget(2, self.sync_button)
            self.sync_button.show()
            self.control_layout.removeWidget(self.set_sync_point_button)
            self.set_sync_point_button.hide()
            self.control_layout.insertWidget(3, self.add_step_marker_button)
            self.add_step_marker_button.show()
            self.sync_video_time = None
            self.sync_data_time = None
            QApplication.restoreOverrideCursor()
            for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
                self.stop_interactivity(plot_widget, idx)

    def set_sync_point_video(self):
        if self.sync_state == "video":
            self.sync_video_time = self.video_timestamps[self.current_frame]
            self.sync_state = "data"
            self.sync_status_label.setText("Sincronizzazione: Clicca sul grafico per impostare il punto di sincronizzazione dei dati")
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
            for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
                self.interactive_flags[idx] = True
                plot_widget.setMouseTracking(True)
                plot_widget.scene().sigMouseClicked.connect(
                    lambda event, widget=plot_widget, idx=idx: self.on_sync_data_point_selected(event, widget, idx))

    def on_sync_data_point_selected(self, event, widget, idx):
        if self.sync_state != "data":
            return
        pos = event.scenePos()
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]
        closest_index = np.abs(data['VideoTime'] - mouse_point.x()).idxmin()
        self.sync_data_time = data['VideoTime'].values[closest_index]

        for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
            self.stop_interactivity(plot_widget, idx)
        QApplication.restoreOverrideCursor()
        self.sync_status_label.hide()
        self.control_layout.removeWidget(self.cancel_sync_button)
        self.cancel_sync_button.hide()
        self.control_layout.insertWidget(2, self.sync_button)
        self.sync_button.show()
        self.control_layout.removeWidget(self.set_sync_point_button)
        self.set_sync_point_button.hide()
        self.control_layout.insertWidget(3, self.add_step_marker_button)
        self.add_step_marker_button.show()
        self.sync_state = None
        self.check_sync_ready()

    def check_sync_ready(self):
        if self.sync_video_time is not None and self.sync_data_time is not None:
            self.sync_offset = self.sync_video_time - self.sync_data_time
            print(f"Offset di sincronizzazione impostato a {self.sync_offset} secondi")
            self.update_graphs()
            self.sync_video_time = None
            self.sync_data_time = None
            self.is_playing = False
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.save_config()

    def reset_synchronization(self):
        self.sync_offset = 0.0
        self.update_graphs()
        self.save_config()
        QMessageBox.information(self, "Sincronizzazione Reimpostata", "L'offset di sincronizzazione è stato reimpostato.")

    def reset_settings(self):
        reply = QMessageBox.question(self, 'Reimposta Impostazioni',
                                     'Sei sicuro di voler reimpostare tutte le impostazioni ai valori predefiniti?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            config_file = self.get_config_file_path()
            if os.path.exists(config_file):
                os.remove(config_file)
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
            self.step_markers_right = []
            self.step_markers_left = []
            self.emiciclo_markers_right = []
            self.emiciclo_markers_left = []
            self.show_steps = True
            self.video_layout_orientation = None
            self.save_config()
            QMessageBox.information(self, "Impostazioni Reimpostate",
                                    "Le impostazioni sono state reimpostate ai valori predefiniti.")

    def toggle_theme(self):
        if self.theme == 'dark':
            self.theme = 'light'
        else:
            self.theme = 'dark'
        self.apply_theme()
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
        self.save_config()

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        try:
            widget.scene().sigMouseMoved.disconnect(self.on_mouse_moved_slots[idx])
        except TypeError:
            pass

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
                self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
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
        self.play_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.current_frame = max(0, min(self.total_frames - 1, self.current_frame + step))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

        ret, frame = self.cap.read()
        if ret:
            self.trackbar.setValue(self.current_frame)
            self.update_frame_display(frame)
            self.update_graphs()
        self.update_frame_counter()
        self.video_finished = False
        self.save_config()

    def update_selected_columns(self):
        selected_columns = [checkbox.text() for checkbox in
                            (self.checkboxes_right + self.checkboxes_left)
                            if checkbox.isChecked()]
        if selected_columns != self.selected_columns:
            self.selected_columns = selected_columns
            self.update_plot_widgets()
            self.save_config()

    def update_plot_widgets(self):
        for widget, _, _, _ in self.plot_widgets:
            widget.deleteLater()
        self.plot_widgets.clear()
        self.interactive_flags.clear()

        if not self.selected_columns:
            return

        self.on_mouse_moved_slots = []

        if "Accelerazioni Dx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"],
                                    ["#FF0000", "#00FF00", "#0000FF"],
                                    self.data_right, 'right')

        if "Giroscopio Dx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"],
                                    ["#FF0000", "#00FF00", "#0000FF"],
                                    self.data_right, 'right')

        if "Pressione Dx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"],
                                    ["#FF0000", "#00FF00", "#0000FF"],
                                    self.data_right, 'right')

        if "Accelerazioni Sx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"],
                                    ["#FFA500", "#800080", "#008080"],
                                    self.data_left, 'left')

        if "Giroscopio Sx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"],
                                    ["#FFA500", "#800080", "#008080"],
                                    self.data_left, 'left')

        if "Pressione Sx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"],
                                    ["#FFA500", "#800080", "#008080"],
                                    self.data_left, 'left')

    def create_plot_widget(self, columns, colors, data, foot):
        plot_widget = pg.PlotWidget()
        if self.theme == 'dark':
            plot_widget.setBackground('#2E2E2E')
            axis_color = '#F0F0F0'
        else:
            plot_widget.setBackground('#FFFFFF')
            axis_color = '#000000'
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        plot_widget.foot = foot
        ylabel = ", ".join([f"<span style='color: {colors[i]};'>{column}</span>"
                            for i, column in enumerate(columns)])
        plot_widget.setLabel('left', ylabel)
        plot_widget.setLabel('bottom', 'Tempo (s)')
        plot_widget.getAxis('left').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('left').setTextPen(pg.mkPen(color=axis_color))
        plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color=axis_color))
        self.graph_splitter.addWidget(plot_widget)

        plot_widget.all_columns = columns
        plot_widget.data = data
        plot_widget.selected_columns = columns.copy()
        plot_widget.colors = colors

        plot_widget.step_marker_lines = []
        plot_widget.step_regions = []
        plot_widget.step_labels = []

        plot_widget.emiciclo_marker_lines = []
        plot_widget.emiciclo_regions = []
        plot_widget.emiciclo_labels = []

        view_box = plot_widget.getViewBox()

        select_datapoints_action = QAction("Seleziona Datapoint", plot_widget)
        select_datapoints_action.triggered.connect(lambda: self.select_datapoints(plot_widget))

        view_box.menu.addAction(select_datapoints_action)

        add_marker_here_action = QAction("Aggiungi Marker Qui", plot_widget)
        add_marker_here_action.triggered.connect(lambda: self.add_marker_here(plot_widget))

        add_marker_current_time_action = QAction("Aggiungi Marker al Timestamp Corrente", plot_widget)
        add_marker_current_time_action.triggered.connect(lambda: self.add_step_marker(plot_widget))

        add_emiciclo_here_action = QAction("Aggiungi Marker Emiciclo Qui", plot_widget)
        add_emiciclo_here_action.triggered.connect(lambda: self.add_emiciclo_marker_here(plot_widget))

        add_emiciclo_current_time_action = QAction("Aggiungi Marker Emiciclo al Timestamp Corrente", plot_widget)
        add_emiciclo_current_time_action.triggered.connect(lambda: self.add_emiciclo_marker(plot_widget))

        view_box.menu.addAction(add_marker_here_action)
        view_box.menu.addAction(add_marker_current_time_action)
        view_box.menu.addAction(add_emiciclo_here_action)
        view_box.menu.addAction(add_emiciclo_current_time_action)

        remove_marker_action = QAction("Rimuovi Marker Qui", plot_widget)
        remove_marker_action.triggered.connect(lambda: self.remove_marker_here(plot_widget))
        remove_marker_action.setVisible(False)
        view_box.menu.addAction(remove_marker_action)

        remove_emiciclo_marker_action = QAction("Rimuovi Marker Emiciclo Qui", plot_widget)
        remove_emiciclo_marker_action.triggered.connect(lambda: self.remove_emiciclo_marker_here(plot_widget))
        remove_emiciclo_marker_action.setVisible(False)
        view_box.menu.addAction(remove_emiciclo_marker_action)

        plot_widget.toggle_steps_action = QAction("Disattiva Visualizzazione Passi" if self.show_steps else "Attiva Visualizzazione Passi", plot_widget)
        plot_widget.toggle_steps_action.triggered.connect(self.toggle_step_visualization)
        view_box.menu.addSeparator()
        view_box.menu.addAction(plot_widget.toggle_steps_action)

        plot_widget.remove_marker_action = remove_marker_action
        plot_widget.remove_emiciclo_marker_action = remove_emiciclo_marker_action

        view_box.menu.aboutToShow.connect(lambda vw=view_box, pw=plot_widget: self.update_context_menu(vw, pw))

        self.plot_widgets.append((plot_widget, [], columns, data))
        self.interactive_flags.append(False)
        plot_widget.plot_curves = []
        plot_widget.moving_points = []

        self.update_plot_widget(plot_widget)

        plot_widget.scene().sigMouseClicked.connect(
            lambda event, widget=plot_widget, idx=len(self.plot_widgets) - 1: self.toggle_interactivity(event, widget, idx))

        plot_widget.scene().sigMouseMoved.connect(
            lambda pos, widget=plot_widget: self.on_mouse_hover(pos, widget))

        on_mouse_moved_slot = lambda pos, widget=plot_widget, idx=len(self.plot_widgets) - 1: self.on_mouse_moved(pos, widget, idx)
        self.on_mouse_moved_slots.append(on_mouse_moved_slot)

    def update_plot_widget(self, plot_widget):
        data = plot_widget.data
        selected_columns = plot_widget.selected_columns
        colors = plot_widget.colors

        max_points = 10000
        if len(data) > max_points:
            indices = np.linspace(0, len(data) - 1, max_points).astype(int)
            data = data.iloc[indices]
        time_values = data["VideoTime"].values

        plot_widget.clear()
        plot_widget.plot_curves = []
        plot_widget.moving_points = []

        for i, column in enumerate(plot_widget.all_columns):
            if column in selected_columns:
                color = colors[i]
                color = pg.mkColor(color)
                color.setAlpha(255)
                pen = pg.mkPen(color=color, width=2)
                curve = plot_widget.plot(time_values, data[column].values, pen=pen)
                curve.setDownsampling(auto=True, method='mean')
                plot_widget.plot_curves.append(curve)
                moving_point = plot_widget.plot(
                    [time_values[0]], [data[column].values[0]],
                    pen=None, symbol='o', symbolBrush=color)
                plot_widget.moving_points.append(moving_point)

        for idx, (pw, _, cols, _) in enumerate(self.plot_widgets):
            if pw == plot_widget:
                self.plot_widgets[idx] = (plot_widget, plot_widget.moving_points, plot_widget.all_columns, data)
                break

        self.update_markers(plot_widget)

    def select_datapoints(self, plot_widget):
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleziona Datapoint")

        layout = QVBoxLayout()
        checkboxes = []
        for column in plot_widget.all_columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(column in plot_widget.selected_columns)
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            plot_widget.selected_columns = [cb.text() for cb in checkboxes if cb.isChecked()]
            self.update_plot_widget(plot_widget)

    def update_context_menu(self, view_box, plot_widget):
        if hasattr(self, 'context_menu_event_pos'):
            pos = self.context_menu_event_pos
            vb = plot_widget.plotItem.vb
            mouse_point = vb.mapSceneToView(pos)
            timestamp = mouse_point.x()

            foot = plot_widget.foot
            if foot == 'right':
                step_markers = self.step_markers_right
                emiciclo_markers = self.emiciclo_markers_right
            else:
                step_markers = self.step_markers_left
                emiciclo_markers = self.emiciclo_markers_left

            threshold = 0.1
            distances = np.abs(np.array(step_markers) - timestamp)
            min_distance = np.min(distances) if len(distances) > 0 else np.inf

            if min_distance <= threshold:
                plot_widget.remove_marker_action.setVisible(True)
            else:
                plot_widget.remove_marker_action.setVisible(False)

            distances_emiciclo = np.abs(np.array(emiciclo_markers) - timestamp)
            min_distance_emiciclo = np.min(distances_emiciclo) if len(distances_emiciclo) > 0 else np.inf

            if min_distance_emiciclo <= threshold:
                plot_widget.remove_emiciclo_marker_action.setVisible(True)
            else:
                plot_widget.remove_emiciclo_marker_action.setVisible(False)

        self.update_toggle_steps_action(plot_widget)

    def add_step_marker(self, plot_widget=None):
        if plot_widget is None:
            foot = 'right'
        else:
            foot = plot_widget.foot

        current_video_time = self.video_timestamps[self.current_frame]
        synced_time = current_video_time - self.sync_offset

        if foot == 'right':
            self.step_markers_right.append(synced_time)
        else:
            self.step_markers_left.append(synced_time)

        if plot_widget:
            self.update_markers(plot_widget)
        else:
            for pw, _, _, _ in self.plot_widgets:
                if pw.foot == foot:
                    self.update_markers(pw)

        self.save_config()

    def add_marker_here(self, plot_widget):
        pos = self.context_menu_event_pos
        vb = plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        timestamp = mouse_point.x()

        foot = plot_widget.foot
        if foot == 'right':
            self.step_markers_right.append(timestamp)
        else:
            self.step_markers_left.append(timestamp)

        self.update_markers(plot_widget)
        self.save_config()

    def remove_marker_here(self, plot_widget):
        pos = self.context_menu_event_pos
        vb = plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        timestamp = mouse_point.x()

        foot = plot_widget.foot
        if foot == 'right':
            markers = self.step_markers_right
        else:
            markers = self.step_markers_left

        threshold = 0.1
        distances = np.abs(np.array(markers) - timestamp)
        min_distance = np.min(distances) if len(distances) > 0 else np.inf

        if min_distance <= threshold:
            idx_to_remove = np.argmin(distances)
            del markers[idx_to_remove]
            self.update_markers(plot_widget)
            self.save_config()
        else:
            QMessageBox.information(self, "Nessun Marker Vicino", "Non ci sono marker vicini alla posizione selezionata.")

    def add_emiciclo_marker(self, plot_widget=None):
        if plot_widget is None:
            foot = 'right'
        else:
            foot = plot_widget.foot

        current_video_time = self.video_timestamps[self.current_frame]
        synced_time = current_video_time - self.sync_offset

        if foot == 'right':
            self.emiciclo_markers_right.append(synced_time)
        else:
            self.emiciclo_markers_left.append(synced_time)

        if plot_widget:
            self.update_markers(plot_widget)
        else:
            for pw, _, _, _ in self.plot_widgets:
                if pw.foot == foot:
                    self.update_markers(pw)

        self.save_config()

    def add_emiciclo_marker_here(self, plot_widget):
        pos = self.context_menu_event_pos
        vb = plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        timestamp = mouse_point.x()

        foot = plot_widget.foot
        if foot == 'right':
            self.emiciclo_markers_right.append(timestamp)
        else:
            self.emiciclo_markers_left.append(timestamp)

        self.update_markers(plot_widget)
        self.save_config()

    def remove_emiciclo_marker_here(self, plot_widget):
        pos = self.context_menu_event_pos
        vb = plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        timestamp = mouse_point.x()

        foot = plot_widget.foot
        if foot == 'right':
            markers = self.emiciclo_markers_right
        else:
            markers = self.emiciclo_markers_left

        threshold = 0.1
        distances = np.abs(np.array(markers) - timestamp)
        min_distance = np.min(distances) if len(distances) > 0 else np.inf

        if min_distance <= threshold:
            idx_to_remove = np.argmin(distances)
            del markers[idx_to_remove]
            self.update_markers(plot_widget)
            self.save_config()
        else:
            QMessageBox.information(self, "Nessun Marker Emiciclo Vicino",
                                    "Non ci sono marker emiciclo vicini alla posizione selezionata.")

    @pyqtSlot(object)
    def on_mouse_moved(self, pos, widget, idx):
        if self.sync_state == "data":
            return
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]
        synced_time = mouse_point.x() + self.sync_offset
        synced_time_clipped = max(0, min(self.video_timestamps[-1], synced_time))
        closest_frame = np.abs(self.video_timestamps - synced_time_clipped)
        closest_frame = closest_frame.argmin()
        self.current_frame = closest_frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
            self.trackbar.setValue(self.current_frame)

    @pyqtSlot(object)
    def on_mouse_hover(self, pos, widget):
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        timestamp = mouse_point.x()
        self.mouse_timestamp_label.setText(f"Timestamp: {timestamp:.2f} s")
        self.mouse_timestamp_label.show()

    def toggle_interactivity(self, event, widget, idx):
        if self.sync_state == "data":
            return
        if event.button() == Qt.RightButton:
            self.context_menu_event_pos = event.scenePos()
        else:
            if not self.interactive_flags[idx]:
                self.interactive_flags[idx] = True
                widget.setMouseTracking(True)
                widget.scene().sigMouseMoved.connect(self.on_mouse_moved_slots[idx])
            else:
                self.stop_interactivity(widget, idx)

    def generate_csv_for_steps(self):
        if not self.step_markers_right and not self.step_markers_left:
            QMessageBox.warning(self, "Nessun Marker", "Non ci sono marker per generare i CSV dei passi.")
            return

        steps_folder = os.path.join(self.folder_path, 'Passi')
        os.makedirs(steps_folder, exist_ok=True)

        right_folder = os.path.join(steps_folder, 'Piede_Destro')
        left_folder = os.path.join(steps_folder, 'Piede_Sinistro')
        os.makedirs(right_folder, exist_ok=True)
        os.makedirs(left_folder, exist_ok=True)

        right_steps_folder = os.path.join(right_folder, 'Passi_Interi')
        right_half_steps_folder = os.path.join(right_folder, 'Mezzi_Passi')
        os.makedirs(right_steps_folder, exist_ok=True)
        os.makedirs(right_half_steps_folder, exist_ok=True)

        left_steps_folder = os.path.join(left_folder, 'Passi_Interi')
        left_half_steps_folder = os.path.join(left_folder, 'Mezzi_Passi')
        os.makedirs(left_steps_folder, exist_ok=True)
        os.makedirs(left_half_steps_folder, exist_ok=True)

        # Generazione CSV per piede destro
        if self.step_markers_right:
            markers_right_sorted = sorted(self.step_markers_right)
            emicicli_right_sorted = sorted(self.emiciclo_markers_right)
            if markers_right_sorted and markers_right_sorted[0] > 0:
                markers_right_sorted.insert(0, 0)
            step_count = len(markers_right_sorted)
            for i in range(step_count - 1):
                step_start = markers_right_sorted[i]
                step_end = markers_right_sorted[i + 1]
                data_segment = self.data_right[
                    (self.data_right['VideoTime'] >= step_start) &
                    (self.data_right['VideoTime'] <= step_end)]
                if not data_segment.empty:
                    filename = os.path.join(right_steps_folder, f'Passo_{i+1}.csv')
                    data_segment.to_csv(filename, index=False)

                emicicli_in_step = [e for e in emicicli_right_sorted if step_start < e < step_end]
                if emicicli_in_step:
                    data_half_step = self.data_right[
                        (self.data_right['VideoTime'] >= step_start) &
                        (self.data_right['VideoTime'] <= emicicli_in_step[0])]
                    if not data_half_step.empty:
                        filename = os.path.join(right_half_steps_folder, f'Passo{i+1}.1.csv')
                        data_half_step.to_csv(filename, index=False)

                    data_half_step = self.data_right[
                        (self.data_right['VideoTime'] >= emicicli_in_step[0]) &
                        (self.data_right['VideoTime'] <= step_end)]
                    if not data_half_step.empty:
                        filename = os.path.join(right_half_steps_folder, f'Passo{i+1}.2.csv')
                        data_half_step.to_csv(filename, index=False)
                else:
                    midpoint = (step_start + step_end) / 2
                    data_half_step = self.data_right[
                        (self.data_right['VideoTime'] >= step_start) &
                        (self.data_right['VideoTime'] <= midpoint)]
                    if not data_half_step.empty:
                        filename = os.path.join(right_half_steps_folder, f'Passo{i+1}.1.csv')
                        data_half_step.to_csv(filename, index=False)
                    data_half_step = self.data_right[
                        (self.data_right['VideoTime'] >= midpoint) &
                        (self.data_right['VideoTime'] <= step_end)]
                    if not data_half_step.empty:
                        filename = os.path.join(right_half_steps_folder, f'Passo{i+1}.2.csv')
                        data_half_step.to_csv(filename, index=False)

            if step_count > 0:
                last_marker = markers_right_sorted[-1]
                data_segment = self.data_right[self.data_right['VideoTime'] >= last_marker]
                if not data_segment.empty:
                    filename = os.path.join(right_steps_folder, f'Passo_{step_count}.csv')
                    data_segment.to_csv(filename, index=False)
                    emicicli_in_step = [e for e in emicicli_right_sorted if e > last_marker]
                    if emicicli_in_step:
                        data_half_step = self.data_right[
                            (self.data_right['VideoTime'] >= last_marker) &
                            (self.data_right['VideoTime'] <= emicicli_in_step[0])]
                        if not data_half_step.empty:
                            filename = os.path.join(right_half_steps_folder, f'Passo{step_count}.1.csv')
                            data_half_step.to_csv(filename, index=False)

                        data_half_step = self.data_right[self.data_right['VideoTime'] >= emicicli_in_step[0]]
                        if not data_half_step.empty:
                            filename = os.path.join(right_half_steps_folder, f'Passo{step_count}.2.csv')
                            data_half_step.to_csv(filename, index=False)
                    else:
                        midpoint = last_marker + (data_segment['VideoTime'].max() - last_marker) / 2
                        data_half_step = self.data_right[
                            (self.data_right['VideoTime'] >= last_marker) &
                            (self.data_right['VideoTime'] <= midpoint)]
                        if not data_half_step.empty:
                            filename = os.path.join(right_half_steps_folder, f'Passo{step_count}.1.csv')
                            data_half_step.to_csv(filename, index=False)
                        data_half_step = self.data_right[self.data_right['VideoTime'] >= midpoint]
                        if not data_half_step.empty:
                            filename = os.path.join(right_half_steps_folder, f'Passo{step_count}.2.csv')
                            data_half_step.to_csv(filename, index=False)
        else:
            QMessageBox.information(self, "Nessun Marker Piede Destro", "Non ci sono marker per il piede destro.")

        # Generazione CSV per piede sinistro
        if self.step_markers_left:
            markers_left_sorted = sorted(self.step_markers_left)
            emicicli_left_sorted = sorted(self.emiciclo_markers_left)
            if markers_left_sorted and markers_left_sorted[0] > 0:
                markers_left_sorted.insert(0, 0)
            step_count = len(markers_left_sorted)
            for i in range(step_count - 1):
                step_start = markers_left_sorted[i]
                step_end = markers_left_sorted[i + 1]
                data_segment = self.data_left[
                    (self.data_left['VideoTime'] >= step_start) &
                    (self.data_left['VideoTime'] <= step_end)]
                if not data_segment.empty:
                    filename = os.path.join(left_steps_folder, f'Passo_{i+1}.csv')
                    data_segment.to_csv(filename, index=False)

                emicicli_in_step = [e for e in emicicli_left_sorted if step_start < e < step_end]
                if emicicli_in_step:
                    data_half_step = self.data_left[
                        (self.data_left['VideoTime'] >= step_start) &
                        (self.data_left['VideoTime'] <= emicicli_in_step[0])]
                    if not data_half_step.empty:
                        filename = os.path.join(left_half_steps_folder, f'Passo{i+1}.1.csv')
                        data_half_step.to_csv(filename, index=False)

                    data_half_step = self.data_left[
                        (self.data_left['VideoTime'] >= emicicli_in_step[0]) &
                        (self.data_left['VideoTime'] <= step_end)]
                    if not data_half_step.empty:
                        filename = os.path.join(left_half_steps_folder, f'Passo{i+1}.2.csv')
                        data_half_step.to_csv(filename, index=False)
                else:
                    midpoint = (step_start + step_end) / 2
                    data_half_step = self.data_left[
                        (self.data_left['VideoTime'] >= step_start) &
                        (self.data_left['VideoTime'] <= midpoint)]
                    if not data_half_step.empty:
                        filename = os.path.join(left_half_steps_folder, f'Passo{i+1}.1.csv')
                        data_half_step.to_csv(filename, index=False)
                    data_half_step = self.data_left[
                        (self.data_left['VideoTime'] >= midpoint) &
                        (self.data_left['VideoTime'] <= step_end)]
                    if not data_half_step.empty:
                        filename = os.path.join(left_half_steps_folder, f'Passo{i+1}.2.csv')
                        data_half_step.to_csv(filename, index=False)

            if step_count > 0:
                last_marker = markers_left_sorted[-1]
                data_segment = self.data_left[self.data_left['VideoTime'] >= last_marker]
                if not data_segment.empty:
                    filename = os.path.join(left_steps_folder, f'Passo_{step_count}.csv')
                    data_segment.to_csv(filename, index=False)
                    emicicli_in_step = [e for e in emicicli_left_sorted if e > last_marker]
                    if emicicli_in_step:
                        data_half_step = self.data_left[
                            (self.data_left['VideoTime'] >= last_marker) &
                            (self.data_left['VideoTime'] <= emicicli_in_step[0])]
                        if not data_half_step.empty:
                            filename = os.path.join(left_half_steps_folder, f'Passo{step_count}.1.csv')
                            data_half_step.to_csv(filename, index=False)

                        data_half_step = self.data_left[self.data_left['VideoTime'] >= emicicli_in_step[0]]
                        if not data_half_step.empty:
                            filename = os.path.join(left_half_steps_folder, f'Passo{step_count}.2.csv')
                            data_half_step.to_csv(filename, index=False)
                    else:
                        midpoint = last_marker + (data_segment['VideoTime'].max() - last_marker) / 2
                        data_half_step = self.data_left[
                            (self.data_left['VideoTime'] >= last_marker) &
                            (self.data_left['VideoTime'] <= midpoint)]
                        if not data_half_step.empty:
                            filename = os.path.join(left_half_steps_folder, f'Passo{step_count}.1.csv')
                            data_half_step.to_csv(filename, index=False)
                        data_half_step = self.data_left[self.data_left['VideoTime'] >= midpoint]
                        if not data_half_step.empty:
                            filename = os.path.join(left_half_steps_folder, f'Passo{step_count}.2.csv')
                            data_half_step.to_csv(filename, index=False)
        else:
            QMessageBox.information(self, "Nessun Marker Piede Sinistro", "Non ci sono marker per il piede sinistro.")

        QMessageBox.information(self, "Operazione Completa", "I file CSV dei passi e dei mezzi passi sono stati generati con successo.")

    def eventFilter(self, source, event):
        if event.type() == event.Wheel and source is self.graphics_view.viewport():
            self.handle_zoom(event)
            return True
        return super().eventFilter(source, event)

    def handle_zoom(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        old_pos = self.graphics_view.mapToScene(event.pos())
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
        self.graphics_view.scale(zoom_factor, zoom_factor)
        new_pos = self.graphics_view.mapToScene(event.pos())
        delta = new_pos - old_pos
        self.graphics_view.translate(delta.x(), delta.y())

    def switch_csv_files(self):
        # Scambia i dati del piede sinistro e destro
        self.data_left, self.data_right = self.data_right, self.data_left
        # Scambia i percorsi dei file CSV
        self.csv_filePaths[0], self.csv_filePaths[1] = \
            self.csv_filePaths[1], self.csv_filePaths[0]
        # Aggiorna i nomi dei file nella configurazione
        self.config['right_csv'] = os.path.basename(self.csv_filePaths[0])
        self.config['left_csv'] = os.path.basename(self.csv_filePaths[1])
        # Scambia i marker dei passi
        self.step_markers_left, self.step_markers_right = \
            self.step_markers_right, self.step_markers_left
        # Scambia i marker degli emicicli
        self.emiciclo_markers_left, self.emiciclo_markers_right = \
            self.emiciclo_markers_right, self.emiciclo_markers_left
        # Aggiorna i grafici
        self.update_plot_widgets()
        # Salva la configurazione aggiornata
        self.save_config()
