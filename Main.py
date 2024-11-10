import sys
from PyQt5.QtWidgets import QApplication
from Models.BaseVideoPlayer import BaseVideoPlayer

if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        player = BaseVideoPlayer()
        player.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
