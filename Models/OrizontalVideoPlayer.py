import sys
import cv2
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, 
                             QSlider, QHBoxLayout, QCheckBox, QSplitter, QSizePolicy, QGroupBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QRect
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
import pyqtgraph as pg
from Models.BaseVideoPlayer import BaseVideoPlayer

class OrizontalVideoPlayer(BaseVideoPlayer):
    def __init__(self, video_filePath, csv_filePath_right, csv_filePath_left):
        super().__init__(video_filePath, csv_filePath_right, csv_filePath_left)

        # Set up specific layout for OrizontalVideoPlayer
        self.main_splitter = QSplitter(Qt.Vertical, self.central_widget)
        
        # Add the main splitter to the central layout
        self.central_layout.addWidget(self.main_splitter)

        # Add the video label and control panel to the layout
        self.main_splitter.addWidget(self.video_label)
        self.main_splitter.addWidget(self.controls_and_graphs_container)