import sys
import os
import cv2
import numpy as np
import pandas as pd
import json
import hashlib
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QPoint
from PyQt5.QtGui import QPixmap, QImage, QIcon, QCursor, QFont

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QSplitter, QPushButton, QCheckBox, QSizePolicy, QApplication,
                             QAction, QFileDialog, QMessageBox, QComboBox, QDialog, QDialogButtonBox, QListWidget,
                             QMenu)
import pyqtgraph as pg
from platformdirs import user_data_dir, user_cache_dir


class BaseVideoPlayer(QMainWindow):
    def __init__(self, video_filePath=None, csv_filePath_right=None, csv_filePath_left=None):
        super().__init__()

        # Inizializzazione della finestra principale
        self.setWindowTitle("DVSS - Data Video Synchronization Software")
        self.setGeometry(100, 100, 1200, 900)
        self.setFocusPolicy(Qt.StrongFocus)

        # Impostazione dell'icona dell'applicazione
        self.setWindowIcon(QIcon('app_icon.png'))  # Assicurati che 'app_icon.png' esista

        # Variabile per il tema (di default 'dark')
        self.theme = 'dark'

        # Variabile per la velocità di riproduzione
        self.playback_speed = 1.0

        # Configurazioni
        self.config = {}

        # Directory dei dati dell'applicazione
        self.app_name = 'DVSS'  # Nome dell'applicazione
        self.app_data_dir = user_data_dir(self.app_name)
        self.app_cache_dir = user_cache_dir(self.app_name)

        # Assicuriamoci che le directory dei dati esistano
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.app_cache_dir, exist_ok=True)

        # Variabili per i marker dei passi
        self.step_markers = []  # Lista di timestamp dei passi

        # Widget centrale e layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Inizializzazione dei componenti dell'interfaccia utente
        self.setup_ui()

        # Applicazione del tema all'applicazione
        self.apply_theme()

        # Variabili per la sincronizzazione
        self.sync_offset = 0.0  # In secondi
        self.sync_state = None  # Può essere None, "video" o "data"

        # Caricamento dell'ultima cartella aperta
        self.load_last_folder()

        # Se vengono forniti i percorsi del video e dei CSV, caricali
        if video_filePath and csv_filePath_right and csv_filePath_left:
            self.load_video_and_data(video_filePath, [csv_filePath_right, csv_filePath_left])

    def setup_ui(self):
        # Creazione della barra dei menu
        self.menu_bar = self.menuBar()

        # Menu File
        self.file_menu = self.menu_bar.addMenu('File')

        # Azione Apri
        open_action = QAction('Apri', self)
        open_action.triggered.connect(self.open_files)
        self.file_menu.addAction(open_action)

        # Azione Scambia File CSV
        switch_csv_action = QAction('Scambia File CSV', self)
        switch_csv_action.triggered.connect(self.switch_csv_files)
        self.file_menu.addAction(switch_csv_action)

        # Menu Opzioni
        self.options_menu = self.menu_bar.addMenu('Opzioni')

        # Azione Reimposta Sincronizzazione
        reset_sync_action = QAction('Reimposta Sincronizzazione', self)
        reset_sync_action.triggered.connect(self.reset_synchronization)
        self.options_menu.addAction(reset_sync_action)

        # Azione Reimposta Impostazioni Predefinite
        reset_settings_action = QAction('Reimposta Impostazioni Predefinite', self)
        reset_settings_action.triggered.connect(self.reset_settings)
        self.options_menu.addAction(reset_settings_action)

        # Azione Tema Scuro/Chiaro
        toggle_theme_action = QAction('Tema Scuro/Chiaro', self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        self.options_menu.addAction(toggle_theme_action)

        # Layout centrale
        self.central_layout = QHBoxLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Barra verticale
        self.trackbar = QSlider(Qt.Vertical, self)
        self.trackbar.setRange(0, 100)  # Intervallo temporaneo finché il video non viene caricato
        self.trackbar.sliderReleased.connect(self.seek_video)
        self.trackbar.sliderMoved.connect(self.handle_slider_move)
        self.central_layout.addWidget(self.trackbar)

        # Layout per il video e i grafici
        self.video_graphs_layout = QVBoxLayout()
        self.central_layout.addLayout(self.video_graphs_layout)

        # Label per la visualizzazione del video
        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 1px solid #555555;")
        self.video_graphs_layout.addWidget(self.video_label)

        # Messaggio per aprire una cartella
        self.open_folder_label = QLabel("Per favore, apri una cartella per iniziare", self)
        self.open_folder_label.setAlignment(Qt.AlignCenter)
        self.open_folder_label.setStyleSheet("color: #F0F0F0; font-size: 16px; font-weight: bold;")
        self.video_graphs_layout.addWidget(self.open_folder_label)

        # Pannello di controllo
        self.control_panel = QWidget(self)
        self.control_layout = QHBoxLayout(self.control_panel)
        self.control_panel.setLayout(self.control_layout)
        self.video_graphs_layout.addWidget(self.control_panel)

        # Pulsante Play
        self.play_button = QPushButton("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.control_layout.addWidget(self.play_button)

        # Selettore della velocità
        self.speed_selector = QComboBox(self)
        self.speed_selector.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_selector.setCurrentText("1x")
        self.speed_selector.currentTextChanged.connect(self.change_playback_speed)
        self.control_layout.addWidget(self.speed_selector)

        # Pulsante di sincronizzazione con tooltip
        self.sync_button = QPushButton("Sincronizza")
        self.sync_button.setToolTip("Clicca per avviare il processo di sincronizzazione.")
        self.sync_button.clicked.connect(self.toggle_synchronization)
        self.control_layout.addWidget(self.sync_button)

        # Pulsante per impostare il punto di sincronizzazione (visibile solo durante la sincronizzazione)
        self.set_sync_point_button = QPushButton("Imposta Punto di Sync")
        self.set_sync_point_button.setToolTip("Clicca per impostare il punto di sincronizzazione al frame video corrente.")
        self.set_sync_point_button.clicked.connect(self.set_sync_point_video)
        self.set_sync_point_button.hide()  # Nascosto di default
        self.control_layout.addWidget(self.set_sync_point_button)

        # Spaziatore
        self.control_layout.addStretch()

        # Contatore dei frame
        self.frame_counter = QLabel(f"Frame: 0/0", self)
        self.frame_counter.setObjectName("FrameCounter")
        self.control_layout.addWidget(self.frame_counter)

        # Label di stato della sincronizzazione
        self.sync_status_label = QLabel("", self)
        self.sync_status_label.setAlignment(Qt.AlignCenter)
        self.sync_status_label.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold;")
        self.sync_status_label.hide()  # Nascosto di default
        self.video_graphs_layout.addWidget(self.sync_status_label)

        # Contenitore per i controlli e i grafici
        self.controls_and_graphs_container = QWidget(self)
        self.controls_and_graphs_layout = QVBoxLayout(self.controls_and_graphs_container)
        self.controls_and_graphs_container.setLayout(self.controls_and_graphs_layout)
        self.controls_and_graphs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_graphs_layout.addWidget(self.controls_and_graphs_container)

        # Layout per il piede destro
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

        # Layout per il piede sinistro
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

        # Splitter verticale per i grafici
        self.graph_splitter = QSplitter(Qt.Vertical, self)
        self.graph_splitter.setHandleWidth(8)
        self.controls_and_graphs_layout.addWidget(self.graph_splitter)

        # Contenitore per i widget di plotting
        self.plot_widgets = []
        self.interactive_flags = []  # Per tracciare quali grafici sono interattivi

        # Inizializzazione dei widget di plotting per le colonne selezionate
        self.selected_columns = []

        # Applica il tema alle label dei piedi
        self.update_foot_labels_theme()

        # Label per visualizzare il timestamp al passaggio del mouse
        self.mouse_timestamp_label = QLabel("", self)
        self.mouse_timestamp_label.setAlignment(Qt.AlignRight)
        self.mouse_timestamp_label.setStyleSheet("color: #FFD700; font-size: 12px;")
        self.mouse_timestamp_label.hide()  # Nascosta inizialmente
        self.video_graphs_layout.addWidget(self.mouse_timestamp_label)

    def apply_theme(self):
        if self.theme == 'dark':
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())
        # Aggiorna le label dei piedi in base al tema
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
            QMenu {
                background-color: #3E3E3E;
                color: #F0F0F0;
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
            QMenu {
                background-color: #FFFFFF;
                color: #000000;
            }
        """

    def open_files(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Seleziona Cartella", "")
        if folder_path:
            self.open_folder(folder_path)

    def open_folder(self, folder_path):
        try:
            self.open_folder_label.hide()
            self.folder_path = folder_path  # Memorizza il percorso della cartella
            # Trova il file video e i file CSV nella cartella
            video_file = None
            csv_files = []
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.mp4', '.avi', '.mov')):
                    video_file = os.path.join(folder_path, file)
                elif file.lower().endswith('.csv'):
                    csv_files.append(os.path.join(folder_path, file))
            if video_file and len(csv_files) >= 2:
                # Chiedi all'utente di assegnare i file CSV
                assigned_csv_files = self.assign_csv_files(csv_files)
                if assigned_csv_files:
                    # Ricarica il video e i dati
                    self.load_video_and_data(video_file, assigned_csv_files)
                    # Salva l'ultima cartella aperta
                    self.save_last_folder(folder_path)
            else:
                QMessageBox.warning(self, "Errore", "La cartella deve contenere un file video e almeno due file CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante l'apertura della cartella: {e}")

    def assign_csv_files(self, csv_files):
        try:
            # Verifica se l'assegnazione esiste già nella configurazione
            config_file = self.get_config_file_path()
            assigned_csv_files = None
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                right_csv = self.config.get('right_csv')
                left_csv = self.config.get('left_csv')
                if right_csv and left_csv:
                    right_csv_full = os.path.join(self.folder_path, right_csv)
                    left_csv_full = os.path.join(self.folder_path, left_csv)
                    if os.path.exists(right_csv_full) and os.path.exists(left_csv_full):
                        assigned_csv_files = [right_csv_full, left_csv_full]
            if not assigned_csv_files:
                # Chiedi all'utente di assegnare i file CSV
                dialog = QDialog(self)
                dialog.setWindowTitle("Assegna File CSV")

                layout = QVBoxLayout()
                instructions = QLabel("Seleziona il file CSV per ciascun piede:")
                layout.addWidget(instructions)

                right_combo = QComboBox()
                right_combo.addItems([os.path.basename(f) for f in csv_files])
                layout.addWidget(QLabel("Piede Destro:"))
                layout.addWidget(right_combo)

                left_combo = QComboBox()
                left_combo.addItems([os.path.basename(f) for f in csv_files])
                layout.addWidget(QLabel("Piede Sinistro:"))
                layout.addWidget(left_combo)

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)

                dialog.setLayout(layout)

                if dialog.exec_() == QDialog.Accepted:
                    right_csv = right_combo.currentText()
                    left_csv = left_combo.currentText()
                    if right_csv == left_csv:
                        QMessageBox.warning(self, "Errore", "I file CSV per il piede destro e sinistro devono essere diversi.")
                        return None
                    right_csv_full = os.path.join(self.folder_path, right_csv)
                    left_csv_full = os.path.join(self.folder_path, left_csv)
                    assigned_csv_files = [right_csv_full, left_csv_full]
                    # Salva l'assegnazione nella configurazione
                    self.config['right_csv'] = right_csv
                    self.config['left_csv'] = left_csv
                    self.save_config()
                else:
                    return None
            return assigned_csv_files
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante l'assegnazione dei file CSV: {e}")
            return None

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
                        # Tenta di aprire l'ultima cartella
                        self.open_folder(last_folder)
            except Exception as e:
                print(f"Errore nel caricamento dell'ultima cartella: {e}")

    def load_video_and_data(self, video_filePath, csv_filePaths):
        try:
            # csv_filePaths[0] dovrebbe essere il file del piede destro
            # csv_filePaths[1] dovrebbe essere il file del piede sinistro
            self.csv_filePaths = csv_filePaths.copy()

            # Chiudi il video corrente se presente
            if hasattr(self, 'cap') and self.cap.isOpened():
                self.cap.release()

            # Carica il video
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

            # Controllo della riproduzione video
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.next_frame)
            self.is_playing = False

            # Carica e preprocessa i dati per il plotting
            self.load_and_preprocess_data(self.csv_filePaths[0], self.csv_filePaths[1])

            # Carica la configurazione se esiste
            self.load_config()

            # Regola il layout in base alle dimensioni del video
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if width > height:
                # Video orizzontale
                self.adjust_layout(Qt.Vertical)
            else:
                # Video verticale
                self.adjust_layout(Qt.Horizontal)

            # Aggiorna i componenti dell'interfaccia utente
            self.show_first_frame()
            self.update_selected_columns()
            self.update_frame_counter()

            # Aggiorna i marker dei passi dopo il caricamento
            for plot_widget, _, _, _ in self.plot_widgets:
                self.update_step_markers(plot_widget)

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante il caricamento dei dati: {e}")

    def adjust_layout(self, orientation):
        # Rimuovi i widget esistenti se presenti
        if hasattr(self, 'main_splitter'):
            self.main_splitter.deleteLater()

        self.main_splitter = QSplitter(orientation, self.central_widget)

        # Aggiungi lo splitter principale al layout centrale
        self.video_graphs_layout.addWidget(self.main_splitter)

        # Crea il contenitore per il video e il pannello di controllo
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
            try:
                # Converti Timestamp in datetime
                data['Timestamp'] = pd.to_datetime(data['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
                data.dropna(subset=['Timestamp'], inplace=True)
                data['Timestamp'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
                data.sort_values('Timestamp', inplace=True)
                data.reset_index(drop=True, inplace=True)

                # Crea 'VideoTime' inizialmente uguale a 'Timestamp'
                data['VideoTime'] = data['Timestamp']

                # Gestisci i valori mancanti
                data.infer_objects(copy=False)  # Aggiunto per convertire le colonne a tipi appropriati
                data.interpolate(method='linear', inplace=True)
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore nel preprocessamento dei dati: {e}")

    def switch_csv_files(self):
        # Scambia i dati del piede sinistro e destro
        self.data_left, self.data_right = self.data_right, self.data_left
        # Scambia i percorsi dei file CSV
        self.csv_filePaths[0], self.csv_filePaths[1] = self.csv_filePaths[1], self.csv_filePaths[0]
        # Aggiorna i nomi dei file nella configurazione
        self.config['right_csv'] = os.path.basename(self.csv_filePaths[0])
        self.config['left_csv'] = os.path.basename(self.csv_filePaths[1])
        # Aggiorna i grafici
        self.update_plot_widgets()
        # Aggiorna i marker dei passi
        for plot_widget, _, _, _ in self.plot_widgets:
            self.update_step_markers(plot_widget)
        # Salva la configurazione aggiornata
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
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
            self.play_button.setText("Pause")
            self.play_button.setIcon(QIcon("pause.png"))
            self.play_button.setStyleSheet("background-color: #f44336; color: white;")
        self.is_playing = not self.is_playing

    def change_playback_speed(self, speed_text):
        try:
            speed_factor = float(speed_text.replace('x', ''))
            self.playback_speed = speed_factor
            if self.is_playing:
                self.timer.stop()
                self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
            # Salva la configurazione aggiornata
            self.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Velocità di riproduzione non valida: {e}")

    def seek_video(self):
        try:
            self.timer.stop()
            self.is_playing = False
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")
            self.current_frame = self.trackbar.value()
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if ret:
                self.update_frame_display(frame)
                self.update_graphs()
            self.video_finished = False
            # Salva la configurazione aggiornata
            self.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento nel video: {e}")

    def handle_slider_move(self, position):
        try:
            self.current_frame = position
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if ret:
                self.update_frame_display(frame)
                self.update_graphs()
            # Salva la configurazione aggiornata
            self.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento nel video: {e}")

    def update_frame_display(self, frame):
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qt_image))
            self.update_frame_counter()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante l'aggiornamento del frame video: {e}")

    def update_frame_counter(self):
        self.frame_counter.setText(f"Frame: {self.current_frame}/{self.total_frames}")

    def restart_video(self):
        try:
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
            self.play_button.setStyleSheet("background-color: #f44336; color: white;")
            self.timer.start(int(1000 / (self.video_fps * self.playback_speed)))
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante il riavvio del video: {e}")

    def update_graphs(self):
        try:
            # Calcola il timestamp corrente del video considerando l'offset
            current_video_time = self.video_timestamps[self.current_frame]

            # Applica l'offset di sincronizzazione
            synced_time = current_video_time - self.sync_offset

            for i, (plot_widget, moving_points, columns, data) in enumerate(self.plot_widgets):
                synced_time_clipped = max(data['VideoTime'].min(), min(data['VideoTime'].max(), synced_time))
                closest_index = np.abs(data['VideoTime'] - synced_time_clipped).idxmin()

                x = data['VideoTime'].values[closest_index]

                # Aggiorna i punti mobili per le colonne selezionate
                point_idx = 0
                for j, column in enumerate(plot_widget.all_columns):
                    if column in plot_widget.selected_columns:
                        y = data[column].values[closest_index]
                        moving_points[point_idx].setData([x], [y])
                        point_idx += 1

                # Aggiorna i marker dei passi
                self.update_step_markers(plot_widget)
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante l'aggiornamento dei grafici: {e}")

    def update_step_markers(self, plot_widget):
        # Rimuovi i marker esistenti
        for line in plot_widget.step_marker_lines:
            plot_widget.removeItem(line)
        plot_widget.step_marker_lines = []

        # Aggiungi i nuovi marker
        for timestamp in self.step_markers:
            line = pg.InfiniteLine(pos=timestamp, angle=90, pen=pg.mkPen(color='yellow', style=Qt.DashLine))
            plot_widget.addItem(line)
            plot_widget.step_marker_lines.append(line)

    def toggle_synchronization(self):
        if self.sync_state is None:
            # Inizia la sincronizzazione
            self.sync_state = "video"
            self.sync_status_label.setText("Sincronizzazione: Naviga al frame desiderato e clicca 'Imposta Punto di Sync'")
            self.sync_status_label.show()
            self.set_sync_point_button.show()
            self.sync_button.setText("Annulla Sync")
        else:
            # Annulla la sincronizzazione
            self.sync_state = None
            self.sync_status_label.hide()
            self.set_sync_point_button.hide()
            self.sync_button.setText("Sincronizza")
            self.sync_video_time = None
            self.sync_data_time = None
            QApplication.restoreOverrideCursor()
            # Ripristina l'interattività
            for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
                self.stop_interactivity(plot_widget, idx)

    def set_sync_point_video(self):
        if self.sync_state == "video":
            # Salva il timestamp corrente del video come punto di sincronizzazione
            self.sync_video_time = self.video_timestamps[self.current_frame]
            self.sync_state = "data"
            self.sync_status_label.setText("Sincronizzazione: Clicca sul grafico per impostare il punto di sincronizzazione dei dati")
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))
            # Attiva la modalità di selezione dei punti dati
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
        # Trova l'indice più vicino al punto cliccato
        closest_index = np.abs(data['VideoTime'] - mouse_point.x()).idxmin()
        self.sync_data_time = data['VideoTime'].values[closest_index]

        # Disabilita l'interattività per tutti i grafici
        for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
            self.stop_interactivity(plot_widget, idx)
        QApplication.restoreOverrideCursor()
        self.sync_status_label.hide()
        self.sync_button.setText("Sincronizza")
        self.sync_state = None
        self.check_sync_ready()

    def check_sync_ready(self):
        # Se entrambi i punti di sincronizzazione sono selezionati, calcola l'offset
        if self.sync_video_time is not None and self.sync_data_time is not None:
            self.sync_offset = self.sync_video_time - self.sync_data_time
            print(f"Offset di sincronizzazione impostato a {self.sync_offset} secondi")
            # Aggiorna i grafici per riflettere la nuova sincronizzazione
            self.update_graphs()
            # Reimposta i punti di sincronizzazione
            self.sync_video_time = None
            self.sync_data_time = None
            # Assicura che la riproduzione possa procedere
            self.is_playing = False
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")
            # Salva la configurazione aggiornata
            self.save_config()

    def reset_synchronization(self):
        # Reimposta l'offset di sincronizzazione
        self.sync_offset = 0.0
        self.update_graphs()
        self.save_config()
        QMessageBox.information(self, "Sincronizzazione Reimpostata", "L'offset di sincronizzazione è stato reimpostato.")

    def reset_settings(self):
        # Chiedi conferma all'utente
        reply = QMessageBox.question(self, 'Reimposta Impostazioni',
                                     'Sei sicuro di voler reimpostare tutte le impostazioni ai valori predefiniti?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Elimina il file di configurazione specifico della cartella
            config_file = self.get_config_file_path()
            if os.path.exists(config_file):
                os.remove(config_file)
            # Reimposta le impostazioni
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
            # Reimposta i marker dei passi
            self.step_markers = []
            self.save_config()
            QMessageBox.information(self, "Impostazioni Reimpostate", "Le impostazioni sono state reimpostate ai valori predefiniti.")

    def toggle_theme(self):
        if self.theme == 'dark':
            self.theme = 'light'
        else:
            self.theme = 'dark'
        self.apply_theme()
        # Aggiorna i grafici
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
        # Salva la configurazione aggiornata
        self.save_config()

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        try:
            widget.scene().sigMouseMoved.disconnect()
        except TypeError:
            pass  # Già disconnesso

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
                self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")
                self.video_finished = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right or event.key() == Qt.Key_Up:
            self.step_frame(1)
        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_Down:
            self.step_frame(-1)
        elif event.key() == Qt.Key_Space:
            self.toggle_playback()

    def step_frame(self, step):
        try:
            self.timer.stop()
            self.is_playing = False
            self.play_button.setText("Play")
            self.play_button.setIcon(QIcon("play.png"))
            self.play_button.setStyleSheet("background-color: #4CAF50; color: white;")

            self.current_frame = max(0, min(self.total_frames - 1, self.current_frame + step))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

            ret, frame = self.cap.read()
            if ret:
                self.trackbar.setValue(self.current_frame)
                self.update_frame_display(frame)
                self.update_graphs()
            self.update_frame_counter()
            self.video_finished = False
            # Salva la configurazione aggiornata
            self.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante lo scorrimento dei frame: {e}")

    def update_selected_columns(self):
        selected_columns = [checkbox.text() for checkbox in (self.checkboxes_right + self.checkboxes_left) if checkbox.isChecked()]
        if selected_columns != self.selected_columns:
            self.selected_columns = selected_columns
            self.update_plot_widgets()
            # Salva la configurazione aggiornata
            self.save_config()

    def update_plot_widgets(self):
        try:
            # Rimuovi i grafici esistenti
            for widget, _, _, _ in self.plot_widgets:
                widget.deleteLater()
            self.plot_widgets.clear()
            self.interactive_flags.clear()

            if not self.selected_columns:
                return

            # Aggiorna i grafici per il piede destro
            if "Accelerazioni Dx (Ax, Ay, Az)" in self.selected_columns:
                self.create_plot_widget(["Ax", "Ay", "Az"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

            if "Giroscopio Dx (Gx, Gy, Gz)" in self.selected_columns:
                self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

            if "Pressione Dx (S0, S1, S2)" in self.selected_columns:
                self.create_plot_widget(["S0", "S1", "S2"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

            # Aggiorna i grafici per il piede sinistro
            if "Accelerazioni Sx (Ax, Ay, Az)" in self.selected_columns:
                self.create_plot_widget(["Ax", "Ay", "Az"], ["#FFA500", "#800080", "#008080"], self.data_left)

            if "Giroscopio Sx (Gx, Gy, Gz)" in self.selected_columns:
                self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FFA500", "#800080", "#008080"], self.data_left)

            if "Pressione Sx (S0, S1, S2)" in self.selected_columns:
                self.create_plot_widget(["S0", "S1", "S2"], ["#FFA500", "#800080", "#008080"], self.data_left)
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante l'aggiornamento dei grafici: {e}")

    def create_plot_widget(self, columns, colors, data):
        plot_widget = pg.PlotWidget()
        if self.theme == 'dark':
            plot_widget.setBackground('#2E2E2E')
            axis_color = '#F0F0F0'
        else:
            plot_widget.setBackground('#FFFFFF')
            axis_color = '#000000'
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Creazione di label personalizzate per l'asse Y
        ylabel = ", ".join([f"<span style='color: {colors[i]};'>{column}</span>" for i, column in enumerate(columns)])

        plot_widget.setLabel('left', ylabel)
        plot_widget.setLabel('bottom', 'Tempo (s)')
        plot_widget.getAxis('left').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color=axis_color, width=1))
        plot_widget.getAxis('left').setTextPen(pg.mkPen(color=axis_color))
        plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color=axis_color))
        self.graph_splitter.addWidget(plot_widget)

        # Memorizza le colonne e i dati nel plot_widget per futuri accessi
        plot_widget.all_columns = columns
        plot_widget.data = data
        plot_widget.selected_columns = columns.copy()  # Inizialmente tutte le colonne sono selezionate
        plot_widget.colors = colors

        # Lista per i marker dei passi in questo plot
        plot_widget.step_marker_lines = []

        # Accedi alla ViewBox del grafico
        view_box = plot_widget.getViewBox()

        # Crea una nuova QAction per selezionare i datapoint
        select_datapoints_action = QAction("Seleziona Datapoint", plot_widget)
        select_datapoints_action.triggered.connect(lambda: self.select_datapoints(plot_widget))

        # Crea una QAction per aggiungere un marker al timestamp corrente
        add_marker_action = QAction("Aggiungi Marker al Timestamp Corrente", plot_widget)
        add_marker_action.triggered.connect(lambda: self.add_step_marker_at_current_time())

        # Crea una QAction per aggiungere un marker al punto cliccato
        add_marker_here_action = QAction("Aggiungi Marker Qui", plot_widget)
        add_marker_here_action.triggered.connect(lambda: self.add_step_marker_at_position(plot_widget))

        # Aggiungi le azioni al menu contestuale della ViewBox
        view_box.menu.addAction(select_datapoints_action)
        view_box.menu.addAction(add_marker_action)
        view_box.menu.addAction(add_marker_here_action)

        # Aggiungi il plot_widget al layout e aggiorna la lista plot_widgets
        self.plot_widgets.append((plot_widget, [], columns, data))
        self.interactive_flags.append(False)

        # Traccia i dati iniziali
        self.update_plot_widget(plot_widget)

        # Gestisci l'interattività
        plot_widget.scene().sigMouseClicked.connect(
            lambda event, widget=plot_widget, idx=len(self.plot_widgets) - 1: self.toggle_interactivity(event, widget, idx)
        )

        # Connetti l'evento di movimento del mouse per mostrare il timestamp
        plot_widget.scene().sigMouseMoved.connect(
            lambda pos, widget=plot_widget: self.on_mouse_hover(pos, widget)
        )

    def select_datapoints(self, plot_widget):
        # Crea una finestra di dialogo con le checkbox per ogni colonna
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleziona Datapoint")

        layout = QVBoxLayout()
        checkboxes = []
        for column in plot_widget.all_columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(column in plot_widget.selected_columns)
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)

        # Aggiungi i pulsanti OK e Annulla
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        # Mostra la finestra di dialogo e attendi l'input dell'utente
        if dialog.exec_() == QDialog.Accepted:
            # Aggiorna le colonne selezionate in base all'input dell'utente
            plot_widget.selected_columns = [cb.text() for cb in checkboxes if cb.isChecked()]
            # Aggiorna il grafico
            self.update_plot_widget(plot_widget)

    def update_plot_widget(self, plot_widget):
        # Cancella i grafici esistenti
        plot_widget.clear()

        data = plot_widget.data
        selected_columns = plot_widget.selected_columns
        colors = plot_widget.colors

        moving_points = []

        # Ripresenta le colonne selezionate
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

        # Aggiorna i punti mobili in plot_widgets
        for idx, (pw, _, cols, _) in enumerate(self.plot_widgets):
            if pw == plot_widget:
                self.plot_widgets[idx] = (plot_widget, moving_points, plot_widget.all_columns, data)
                break

        # Aggiorna i marker dei passi
        self.update_step_markers(plot_widget)

    def add_step_marker(self):
        # Aggiungi il timestamp corrente alla lista dei marker
        current_video_time = self.video_timestamps[self.current_frame]
        synced_time = current_video_time - self.sync_offset
        self.step_markers.append(synced_time)
        # Aggiorna i grafici per mostrare il nuovo marker
        for plot_widget, _, _, _ in self.plot_widgets:
            self.update_step_markers(plot_widget)
        # Salva la configurazione aggiornata
        self.save_config()

    def add_step_marker_at_current_time(self):
        self.add_step_marker()

    def add_step_marker_at_position(self, plot_widget):
        # Ottieni la posizione corrente del mouse
        mouse_point = plot_widget.plotItem.vb.mapSceneToView(plot_widget.mapFromGlobal(QCursor.pos()))
        timestamp = mouse_point.x()
        self.step_markers.append(timestamp)
        self.update_step_markers(plot_widget)
        # Salva la configurazione aggiornata
        self.save_config()

    @pyqtSlot(object)
    def on_mouse_moved(self, pos, widget, idx):
        if self.sync_state == "data":
            return  # Evita interferenze con la modalità sync

        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]  # Recupera i dati associati
        # Applica l'offset di sincronizzazione
        synced_time = mouse_point.x() + self.sync_offset
        # Trova il frame video corrispondente
        synced_time_clipped = max(0, min(self.video_timestamps[-1], synced_time))
        closest_frame = np.abs(self.video_timestamps - synced_time_clipped).argmin()
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

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        try:
            widget.scene().sigMouseMoved.disconnect()
        except TypeError:
            pass  # Già disconnesso

    def toggle_interactivity(self, event, widget, idx):
        if self.sync_state == "data":
            return  # Evita interferenze con la modalità sync

        if event.button() == Qt.RightButton:
            # Mostra il menu contestuale
            menu = QMenu(widget)
            add_marker_action = QAction("Aggiungi Marker Qui", self)
            add_marker_action.triggered.connect(lambda: self.add_step_marker_at_position(widget))
            menu.addAction(add_marker_action)
            remove_marker_action = QAction("Rimuovi Marker Qui", self)
            remove_marker_action.triggered.connect(lambda: self.remove_step_marker_at_position(widget))
            menu.addAction(remove_marker_action)
            # Converti la posizione in QPoint
            screen_pos = event.screenPos()
            qt_screen_pos = QPoint(int(screen_pos.x()), int(screen_pos.y()))
            menu.exec_(qt_screen_pos)
        else:
            if not self.interactive_flags[idx]:
                self.interactive_flags[idx] = True
                widget.setMouseTracking(True)
                widget.scene().sigMouseMoved.connect(lambda pos, widget=widget, idx=idx: self.on_mouse_moved(pos, widget, idx))
            else:
                self.stop_interactivity(widget, idx)

    def remove_step_marker_at_position(self, plot_widget):
        # Ottieni la posizione corrente del mouse
        mouse_point = plot_widget.plotItem.vb.mapSceneToView(plot_widget.mapFromGlobal(QCursor.pos()))
        timestamp = mouse_point.x()
        # Trova il marker più vicino
        if self.step_markers:
            closest_marker = min(self.step_markers, key=lambda x: abs(x - timestamp))
            if abs(closest_marker - timestamp) < 0.1:  # Tolleranza di 0.1 secondi
                self.step_markers.remove(closest_marker)
                self.update_step_markers(plot_widget)
                # Salva la configurazione aggiornata
                self.save_config()
            else:
                QMessageBox.information(self, "Nessun Marker Trovato", "Non ci sono marker vicini alla posizione selezionata.")
        else:
            QMessageBox.information(self, "Nessun Marker", "Non ci sono marker da rimuovere.")

    def get_folder_hash(self):
        return hashlib.md5(self.folder_path.encode('utf-8')).hexdigest()

    def get_config_file_path(self):
        folder_hash = self.get_folder_hash()
        config_file = os.path.join(self.app_data_dir, f'config_{folder_hash}.json')
        return config_file

    def load_config(self):
        config_file = self.get_config_file_path()
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            # Imposta le impostazioni dalla configurazione
            self.sync_offset = float(self.config.get('sync_offset', 0.0))
            self.playback_speed = float(self.config.get('playback_speed', 1.0))
            # Imposta il selettore di velocità
            speed_text = f"{self.playback_speed}x"
            if speed_text in [self.speed_selector.itemText(i) for i in range(self.speed_selector.count())]:
                self.speed_selector.setCurrentText(speed_text)
            else:
                self.speed_selector.addItem(speed_text)
                self.speed_selector.setCurrentText(speed_text)
            # Imposta il frame corrente
            self.current_frame = int(self.config.get('current_frame', 0))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            # Aggiorna la visualizzazione del video
            ret, frame = self.cap.read()
            if ret:
                self.update_frame_display(frame)
                self.update_graphs()

            # Aggiorna i percorsi dei file CSV in base alla configurazione
            right_csv = self.config.get('right_csv')
            left_csv = self.config.get('left_csv')
            if right_csv and left_csv:
                self.csv_filePaths[0] = os.path.join(self.folder_path, right_csv)
                self.csv_filePaths[1] = os.path.join(self.folder_path, left_csv)
                self.load_and_preprocess_data(self.csv_filePaths[0], self.csv_filePaths[1])

            # Imposta le colonne selezionate
            selected_columns = self.config.get('selected_columns', [])
            for checkbox in (self.checkboxes_right + self.checkboxes_left):
                if checkbox.text() in selected_columns:
                    checkbox.setChecked(True)
                else:
                    checkbox.setChecked(False)
            # Aggiorna i grafici
            self.update_selected_columns()
            # Imposta il tema
            self.theme = self.config.get('theme', 'dark')
            self.apply_theme()

            # Carica i marker dei passi
            self.step_markers = self.config.get('step_markers', [])

        else:
            self.config = {}
            self.step_markers = []

    def save_config(self):
        config_file = self.get_config_file_path()
        self.config['sync_offset'] = float(self.sync_offset)
        self.config['playback_speed'] = float(self.playback_speed)
        self.config['current_frame'] = int(self.current_frame)
        self.config['selected_columns'] = [checkbox.text() for checkbox in (self.checkboxes_right + self.checkboxes_left) if checkbox.isChecked()]
        # Memorizza quali CSV sono assegnati ai piedi
        self.config['right_csv'] = os.path.basename(self.csv_filePaths[0])
        self.config['left_csv'] = os.path.basename(self.csv_filePaths[1])
        # Salva il tema corrente
        self.config['theme'] = self.theme
        # Salva i marker dei passi
        self.config['step_markers'] = self.step_markers
        # Converte tutti i valori in tipi standard per evitare problemi con JSON
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
                    # Estrai il valore dopo 'SamplingFrequency:'
                    sensor_rate = int(line.split(":")[1].strip())
                    break

        if sensor_rate is None:
            raise ValueError("SamplingFrequency non trovato nell'header del file.")
        return sensor_rate
