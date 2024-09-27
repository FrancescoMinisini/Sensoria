import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QSlider
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QImage
from Models.OrizontalVideoPlayer import OrizontalVideoPlayer
from Models.VerticalVideoPlayer import VerticalVideoPlayer

def select_video_player(video_filePath, csv_filePath_right, csv_filePath_left):
    cap = cv2.VideoCapture(video_filePath)
    
    if not cap.isOpened():
        raise ValueError(f"Error opening video file: {video_filePath}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if width > height:
        return OrizontalVideoPlayer(video_filePath, csv_filePath_right, csv_filePath_left)
    else:
        return VerticalVideoPlayer(video_filePath, csv_filePath_right, csv_filePath_left)



if __name__ == "__main__":
    # File paths
    video_filePath = 'data\\vertical.mp4'
    csv_filePath_right = 'data\\sinistro.csv'
    csv_filePath_left = 'data\\destro.csv'
    
    app = QApplication(sys.argv)
    
    try:
        player = select_video_player(video_filePath, csv_filePath_right, csv_filePath_left)
        player.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

