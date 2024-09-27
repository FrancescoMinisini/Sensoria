import sys
import cv2
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QSplitter, QPushButton, QCheckBox, QSizePolicy, QApplication)
from PyQt5.QtGui import QPixmap, QImage, QIcon
import pyqtgraph as pg


class BaseVideoPlayer(QMainWindow):
    def __init__(self, video_filePath, csv_filePath_right, csv_filePath_left):
        super().__init__()

        # Set up the main window
        self.setWindowTitle("Video Player with Interactive Graphs")
        self.setGeometry(100, 100, 1200, 900)
        self.setFocusPolicy(Qt.StrongFocus)

        # Apply a dark theme to the application
        self.setStyleSheet(self.get_stylesheet())

        # Initialize synchronization offset
        self.sync_offset = 0.0  # In seconds

        # Central widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Define the central layout and set it to central_widget
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)

        # Initialize UI components
        self.setup_ui(video_filePath, csv_filePath_right, csv_filePath_left)

    def setup_ui(self, video_filePath, csv_filePath_right, csv_filePath_left):
        # Video display label
        self.video_label = QLabel(self)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)

        # Container for control panel and graphs
        self.controls_and_graphs_container = QWidget(self)
        self.controls_and_graphs_layout = QVBoxLayout(self.controls_and_graphs_container)

        # Control panel
        self.control_panel = QWidget(self)
        self.control_layout = QHBoxLayout(self.control_panel)
        self.controls_and_graphs_layout.addWidget(self.control_panel)

        # Play button
        self.play_button = QPushButton("Play")
        self.play_button.setIcon(QIcon("play.png"))
        self.play_button.setIconSize(self.play_button.sizeHint())
        self.play_button.clicked.connect(self.toggle_playback)
        self.control_layout.addWidget(self.play_button)

        # Sync buttons
        self.sync_video_button = QPushButton("Set Sync Point (Video)")
        self.sync_video_button.clicked.connect(self.set_sync_point_video)
        self.control_layout.addWidget(self.sync_video_button)

        self.sync_data_button = QPushButton("Set Sync Point (Data)")
        self.sync_data_button.clicked.connect(self.set_sync_point_data)
        self.control_layout.addWidget(self.sync_data_button)

        # Spacer
        self.control_layout.addStretch()

        # Frame counter
        self.frame_counter = QLabel("Frame: 0/0", self)
        self.frame_counter.setObjectName("FrameCounter")
        self.control_layout.addWidget(self.frame_counter)

        # Trackbar for seeking through video
        self.trackbar = QSlider(Qt.Horizontal, self)
        self.trackbar.sliderReleased.connect(self.seek_video)
        self.trackbar.sliderMoved.connect(self.handle_slider_move)
        self.controls_and_graphs_layout.addWidget(self.trackbar)

        # Load video
        self.video_path = video_filePath
        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.trackbar.setRange(0, self.total_frames - 1)
        self.video_timestamps = np.arange(0, self.total_frames) / self.video_fps

        # Video playback control
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False
        self.current_frame = 0
        self.video_finished = False

        # Load and preprocess data for plotting
        self.load_and_preprocess_data(csv_filePath_right, csv_filePath_left)

        # Synchronization points
        self.sync_video_time = None
        self.sync_data_time = None

        # Right foot layout
        right_foot_layout = QHBoxLayout()
        right_label = QLabel("Right Foot")
        right_label.setStyleSheet("color: #F0F0F0; font-weight: bold;")
        right_foot_layout.addWidget(right_label)

        self.checkboxes_right = []
        checkbox_labels_right = ["Accelerazioni Dx (Ax, Ay, Az)", "Giroscopio Dx (Gx, Gy, Gz)", "Pressione Dx (S0, S1, S2)"]
        for label in checkbox_labels_right:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            right_foot_layout.addWidget(checkbox)
            self.checkboxes_right.append(checkbox)

        self.controls_and_graphs_layout.addLayout(right_foot_layout)

        # Left foot layout
        left_foot_layout = QHBoxLayout()
        left_label = QLabel("Left Foot")
        left_label.setStyleSheet("color: #F0F0F0; font-weight: bold;")
        left_foot_layout.addWidget(left_label)

        self.checkboxes_left = []
        checkbox_labels_left = ["Accelerazioni Sx (Ax, Ay, Az)", "Giroscopio Sx (Gx, Gy, Gz)", "Pressione Sx (S0, S1, S2)"]
        for label in checkbox_labels_left:
            checkbox = QCheckBox(label, self)
            checkbox.stateChanged.connect(self.update_selected_columns)
            left_foot_layout.addWidget(checkbox)
            self.checkboxes_left.append(checkbox)

        self.controls_and_graphs_layout.addLayout(left_foot_layout)

        # Vertical splitter for graphs
        self.graph_splitter = QSplitter(Qt.Vertical, self.controls_and_graphs_container)
        self.graph_splitter.setHandleWidth(8)
        self.controls_and_graphs_layout.addWidget(self.graph_splitter)

        # Plot widgets container
        self.plot_widgets = []
        self.interactive_flags = []  # To track which plots are interactive

        # Initialize plot widget for selected columns
        self.selected_columns = []

        # Command info overlay
        self.setup_command_overlay()

        # Add video label and controls to the main layout
        self.main_splitter = QSplitter(Qt.Horizontal, self.central_widget)
        self.main_splitter.addWidget(self.video_label)
        self.main_splitter.addWidget(self.controls_and_graphs_container)
        self.central_layout.addWidget(self.main_splitter)

        # Render the first frame of the video
        self.show_first_frame()

    def get_stylesheet(self):
        return """
            QMainWindow {
                background-color: #2E2E2E;
                color: #F0F0F0;
            }
            QLabel, QPushButton, QSlider, QCheckBox {
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

    def setup_command_overlay(self):
        # Metodo per configurare il pannello di comandi
        self.command_overlay = QWidget(self)
        self.command_overlay.setGeometry(10, 10, 150, 90)
        self.command_overlay.setStyleSheet("""
            background-color: #2E2E2E;
            border: 1px solid #F0F0F0;
            border-radius: 8px;
            padding: 3px;
        """)
        command_layout = QVBoxLayout(self.command_overlay)
        command_layout.setSpacing(2)

        command_info_label = QLabel()
        command_info_label.setPixmap(QPixmap("right_arrow.png"))
        command_info_label.setText(" Right: Next Frame")
        command_info_label.setStyleSheet("color: #F0F0F0; font-size: 12px;")
        command_layout.addWidget(command_info_label)

        command_info_label = QLabel()
        command_info_label.setPixmap(QPixmap("left_arrow.png"))
        command_info_label.setText(" Left: Prev Frame")
        command_info_label.setStyleSheet("color: #F0F0F0; font-size: 12px;")
        command_layout.addWidget(command_info_label)

        command_info_label = QLabel()
        command_info_label.setPixmap(QPixmap("spacebar.png"))
        command_info_label.setText(" Space: Play/Pause")
        command_info_label.setStyleSheet("color: #F0F0F0; font-size: 12px;")
        command_layout.addWidget(command_info_label)

    def show_first_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
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
            self.timer.start(int(1000 / self.video_fps))  # Adjust based on your video's FPS
            self.play_button.setText("Pause")
            self.play_button.setIcon(QIcon("pause.png"))
        self.is_playing = not self.is_playing

    def next_frame(self):
        if not any(self.interactive_flags):
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

    def handle_slider_move(self, position):
        self.current_frame = position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()

    def update_frame_display(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))
        self.update_frame_counter()

    def update_frame_counter(self):
        self.frame_counter.setText(f"Frame: {self.current_frame}/{self.total_frames}")

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
        self.timer.start(int(1000 / self.video_fps))

    def update_graphs(self):
        # Calcola il timestamp corrente del video tenendo conto dell'offset
        current_video_time = self.video_timestamps[self.current_frame]

        # Applica l'offset temporale
        synced_time = current_video_time - self.sync_offset

        for i, (plot_widget, moving_points, columns, data) in enumerate(self.plot_widgets):
            # Trova l'indice più vicino al timestamp sincronizzato
            closest_index = np.abs(data['VideoTime'] - synced_time).idxmin()

            x = data['VideoTime'].values[closest_index]
            for j, column in enumerate(columns):
                y = data[column].values[closest_index]
                moving_points[j].setData([x], [y])

    def update_selected_columns(self):
        selected_columns = [checkbox.text() for checkbox in (self.checkboxes_right + self.checkboxes_left) if checkbox.isChecked()]
        if selected_columns != self.selected_columns:
            self.selected_columns = selected_columns
            self.update_plot_widgets()

    def update_plot_widgets(self):
        for widget, _, _, _ in self.plot_widgets:
            widget.deleteLater()
        self.plot_widgets.clear()
        self.interactive_flags.clear()

        if not self.selected_columns:
            return

        # Update right foot plots
        if "Accelerazioni Dx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        if "Giroscopio Dx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        if "Pressione Dx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"], ["#FF0000", "#00FF00", "#0000FF"], self.data_right)

        # Update left foot plots
        if "Accelerazioni Sx (Ax, Ay, Az)" in self.selected_columns:
            self.create_plot_widget(["Ax", "Ay", "Az"], ["#FFFF00", "#FF00FF", "#00FFFF"], self.data_left)

        if "Giroscopio Sx (Gx, Gy, Gz)" in self.selected_columns:
            self.create_plot_widget(["Gx", "Gy", "Gz"], ["#FFFF00", "#FF00FF", "#00FFFF"], self.data_left)

        if "Pressione Sx (S0, S1, S2)" in self.selected_columns:
            self.create_plot_widget(["S0", "S1", "S2"], ["#FFFF00", "#FF00FF", "#00FFFF"], self.data_left)

    def create_plot_widget(self, columns, colors, data):
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#2E2E2E')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Creazione di etichette personalizzate per l'asse Y su una sola linea
        ylabel = ", ".join([f"<span style='color: {colors[i]};'>{column}</span>" for i, column in enumerate(columns)])

        plot_widget.setLabel('left', ylabel, color='#F0F0F0', size='10pt')
        plot_widget.setLabel('bottom', 'Time (s)', color='#F0F0F0', size='10pt')
        plot_widget.getAxis('left').setPen(pg.mkPen(color='#F0F0F0', width=1))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#F0F0F0', width=1))
        self.graph_splitter.addWidget(plot_widget)

        moving_points = []
        for i, column in enumerate(columns):
            plot = plot_widget.plot(pen=pg.mkPen(color=colors[i], width=2))
            plot.setData(data["VideoTime"].values, data[column].values)
            moving_point = plot_widget.plot([data["VideoTime"].values[0]], [data[column].values[0]], pen=None, symbol='o', symbolBrush=colors[i])
            moving_points.append(moving_point)

        self.plot_widgets.append((plot_widget, moving_points, columns, data))
        self.interactive_flags.append(False)

        plot_widget.scene().sigMouseClicked.connect(
            lambda event, widget=plot_widget, idx=len(self.plot_widgets) - 1: self.toggle_interactivity(event, widget, idx)
        )

    @pyqtSlot(object)
    def on_mouse_moved(self, pos, widget, idx):
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]  # Recupera i dati associati al grafico
        closest_index = np.abs(data['VideoTime'] - mouse_point.x()).idxmin()
        self.current_frame = closest_index
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            self.update_frame_display(frame)
            self.update_graphs()
            self.trackbar.setValue(self.current_frame)

    def stop_interactivity(self, widget, idx):
        self.interactive_flags[idx] = False
        widget.setMouseTracking(False)
        widget.scene().sigMouseMoved.disconnect()

    def toggle_interactivity(self, event, widget, idx):
        if not self.interactive_flags[idx]:
            self.interactive_flags[idx] = True
            widget.setMouseTracking(True)
            widget.scene().sigMouseMoved.connect(lambda pos, widget=widget, idx=idx: self.on_mouse_moved(pos, widget, idx))
        else:
            self.stop_interactivity(widget, idx)

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

    def load_and_preprocess_data(self, csv_filePath_right, csv_filePath_left):
        self.data_right = pd.read_csv(csv_filePath_right, skiprows=18)
        self.data_left = pd.read_csv(csv_filePath_left, skiprows=18)

        for data in [self.data_right, self.data_left]:
            # Converti Timestamp in datetime
            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
            data.dropna(subset=['Timestamp'], inplace=True)
            data['Timestamp'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
            data.sort_values('Timestamp', inplace=True)
            data.reset_index(drop=True, inplace=True)

            # Crea 'VideoTime' inizialmente uguale a 'Timestamp'
            data['VideoTime'] = data['Timestamp']

        # Gestione dei valori mancanti
        self.data_right.interpolate(method='linear', inplace=True)
        self.data_left.interpolate(method='linear', inplace=True)

    def set_sync_point_video(self):
        # Salva il timestamp corrente del video come punto di sincronizzazione
        self.sync_video_time = self.video_timestamps[self.current_frame]
        self.check_sync_ready()

    def set_sync_point_data(self):
        # Attiva la modalità di selezione del punto sul grafico
        for idx, (plot_widget, _, _, _) in enumerate(self.plot_widgets):
            self.interactive_flags[idx] = True
            plot_widget.setMouseTracking(True)
            plot_widget.scene().sigMouseClicked.connect(
                lambda event, widget=plot_widget, idx=idx: self.on_sync_data_point_selected(event, widget, idx)
            )

    def on_sync_data_point_selected(self, event, widget, idx):
        pos = event.scenePos()
        vb = widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        data = self.plot_widgets[idx][-1]
        # Trova l'indice più vicino al punto cliccato
        closest_index = np.abs(data['VideoTime'] - mouse_point.x()).idxmin()
        self.sync_data_time = data['VideoTime'].values[closest_index]

        # Disabilita l'interattività
        self.stop_interactivity(widget, idx)
        self.check_sync_ready()

    def check_sync_ready(self):
        # Se entrambi i punti di sincronizzazione sono stati selezionati, calcola l'offset
        if self.sync_video_time is not None and self.sync_data_time is not None:
            self.sync_offset = self.sync_video_time - self.sync_data_time
            print(f"Synchronization offset set to {self.sync_offset} seconds")
            # Aggiorna i grafici per riflettere la nuova sincronizzazione
            self.update_graphs()

    @staticmethod
    def extract_sensor_rate(csv_filePath):
        sensor_rate = None
        with open(csv_filePath, 'r') as f:
            for line in f:
                if "SamplingFrequency" in line:
                    # Extract the value after 'SamplingFrequency:'
                    sensor_rate = int(line.split(":")[1].strip())
                    break

        if sensor_rate is None:
            raise ValueError("SamplingFrequency not found in the file header.")
        return sensor_rate
