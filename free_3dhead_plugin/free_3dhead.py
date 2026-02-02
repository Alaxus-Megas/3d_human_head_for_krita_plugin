import sys
import os
import math
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QSlider,
                             QLabel, QHBoxLayout, QMainWindow, QFrame, QSizeGrip,
                             QDockWidget, QApplication, QProgressBar, QGridLayout, QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal, QByteArray, QSize, QTimer
from krita import *


PLUGIN_DIR = os.path.dirname(__file__)


FOLDER_FEMALE = "modelo_matrix_480"
FOLDER_MALE = "modelo_matrix_480_2"

COLS = 60
ROWS = 8




class ImageLoader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)


    def __init__(self, folder_name):
        super().__init__()
        self.folder_path = os.path.join(PLUGIN_DIR, folder_name)

    def run(self):
        matrix = [[None for _ in range(COLS)] for _ in range(ROWS)]
        total_files = ROWS * COLS
        loaded_count = 0

        if not os.path.exists(self.folder_path):

            self.finished.emit(matrix)
            return

        for r in range(ROWS):
            for c in range(COLS):
                filename = f"frame_r{r}_c{c}.png"
                path = os.path.join(self.folder_path, filename)

                if os.path.exists(path):
                    pix = QPixmap(path)
                    matrix[r][c] = pix

                loaded_count += 1
                if loaded_count % 15 == 0:
                    self.progress.emit(int((loaded_count / total_files) * 100))

        self.finished.emit(matrix)




class HeadOverlayWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Free 3D Head Overlay")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.base_size = QSize(800, 800)
        self.resize(500, 500)


        self.matrix_frames = []
        self.is_loaded = False


        self.current_model_folder = FOLDER_FEMALE
        self.is_flipped = False


        self.cur_row = ROWS // 2
        self.cur_col = 0
        self.current_image_rotation_angle = 0.0


        self.acc_x = 0.0
        self.acc_y = 0.0
        self.sens_x = 5.0
        self.sens_y = 15.0



        self.global_opacity = 1.0
        self.is_interaction_mode = False
        self.is_click_through = False
        self.oldPos = None


        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setLayout(layout)


        self.header = QFrame()
        self.header.setStyleSheet("background-color: rgba(60, 60, 60, 180); min-height: 20px; max-height: 20px;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 0, 8, 0)
        self.header.setLayout(header_layout)

        self.lbl_title = QLabel(":: Move Window ::")
        self.lbl_title.setStyleSheet("color: white; font-size: 10px; font-weight: bold;")
        header_layout.addWidget(self.lbl_title)

        btn_close = QPushButton("X")
        btn_close.setFixedSize(16, 16)
        btn_close.setStyleSheet("background-color: #ff4444; color: white; border: none; font-size: 10px; border-radius: 2px;")
        btn_close.clicked.connect(self.hide)
        header_layout.addWidget(btn_close)

        layout.addWidget(self.header)
        layout.addStretch()

        self.grip = QSizeGrip(self)
        self.grip.resize(40, 40)
        self.grip.setStyleSheet("""
            background-color: #404040;
            border: 2px solid black;
            border-top-left-radius: 10px;
        """)


        self.start_loading(self.current_model_folder)

    def start_loading(self, folder_name):
        self.is_loaded = False
        self.lbl_title.setText(f":: Cargando {folder_name}... ::")


        self.loader = ImageLoader(folder_name)
        self.loader.finished.connect(self.on_load_finished)
        self.loader.start()

    def on_load_finished(self, matrix):
        self.matrix_frames = matrix
        self.is_loaded = True
        self.update_header_text()
        self.update()

    def update_header_text(self):
        if self.is_click_through:
            self.lbl_title.setText(":: LOCKED (PAINT BEHIND) ::")
        elif self.is_interaction_mode:
            self.lbl_title.setText(":: ROTATE HEAD (Drag in the center) ::")
        else:
            self.lbl_title.setText(":: Move Window ::")



    def toggle_model_sex(self):
        """Alterna entre carpeta Female y Male"""
        if self.current_model_folder == FOLDER_FEMALE:
            self.current_model_folder = FOLDER_MALE
        else:
            self.current_model_folder = FOLDER_FEMALE

        self.start_loading(self.current_model_folder)

        return "Change to Female Head" if self.current_model_folder == FOLDER_MALE else "Change to Male Head"

    def toggle_flip(self):
        """Invierte horizontalmente la imagen"""
        self.is_flipped = not self.is_flipped
        self.update()


    def geo_rotate_step(self, direction):
        """Rota la imagen geométricamente en su centro 5 grados. Direction: 1 (der) o -1 (izq)"""
        if not self.is_loaded: return

        self.current_image_rotation_angle += (direction * 5.0)
        self.update()

    def rotate_step(self, direction):
        """flip manual a step (5 grades). Direction: 1 o -1"""
        if not self.is_loaded: return

        step = -1 * direction
        self.cur_col = (self.cur_col + step) % COLS
        self.update()



    def set_click_through(self, enabled):
        self.is_click_through = enabled
        if enabled:
            self.setWindowFlag(Qt.WindowTransparentForInput, True)
            self.header.setStyleSheet("background-color: rgba(200, 50, 50, 180); min-height: 20px; max-height: 20px;")
        else:
            self.setWindowFlag(Qt.WindowTransparentForInput, False)
            if self.is_interaction_mode:
                self.header.setStyleSheet("background-color: rgba(0, 100, 200, 180); min-height: 20px; max-height: 20px;")
            else:
                self.header.setStyleSheet("background-color: rgba(60, 60, 60, 180); min-height: 20px; max-height: 20px;")

        self.update_header_text()
        self.show()

    def set_interaction_mode(self, enabled):
        self.is_interaction_mode = enabled
        if self.is_click_through: return

        if enabled:
            self.header.setStyleSheet("background-color: rgba(0, 100, 200, 180); min-height: 20px; max-height: 20px;")
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.header.setStyleSheet("background-color: rgba(60, 60, 60, 180); min-height: 20px; max-height: 20px;")
            self.setCursor(Qt.ArrowCursor)
        self.update_header_text()

    def set_opacity(self, value):
        self.global_opacity = value / 100.0
        self.update()

    def set_scale_percent(self, val):
        scale = val / 100.0
        new_w = int(self.base_size.width() * scale)
        new_h = int(self.base_size.height() * scale)
        self.resize(new_w, new_h)

    def reset_view(self):
        self.cur_row = ROWS // 2
        self.cur_col = 0
        self.is_flipped = False
        self.current_image_rotation_angle = 0.0
        self.update()


    def resizeEvent(self, event):
        rect = self.rect()
        self.grip.move(rect.right() - 25, rect.bottom() - 25)
        super().resizeEvent(event)


    def paintEvent(self, event):
        if not self.is_loaded: return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setOpacity(self.global_opacity)


        pix = self.matrix_frames[self.cur_row][self.cur_col]

        if pix:

            if self.is_flipped:
                img = pix.toImage().mirrored(True, False)
                pix = QPixmap.fromImage(img)

            target_rect = self.rect()
            target_rect.setTop(20)

            scaled_pix = pix.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

            x = int(target_rect.x() + (target_rect.width() - scaled_pix.width()) / 2)
            y = int(target_rect.y() + (target_rect.height() - scaled_pix.height()) / 2)


            if self.current_image_rotation_angle != 0:

                 center_x = x + scaled_pix.width() / 2.0
                 center_y = y + scaled_pix.height() / 2.0


                 painter.translate(center_x, center_y)


                 painter.rotate(self.current_image_rotation_angle)


                 painter.translate(-center_x, -center_y)


            painter.drawPixmap(x, y, scaled_pix)


    def mousePressEvent(self, event):


        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
            if self.is_interaction_mode:
                self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        self.oldPos = None
        if self.is_interaction_mode:
            self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if not self.oldPos: return

        delta = event.globalPos() - self.oldPos

        if not self.is_interaction_mode:
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()
        else:
            self.process_rotation(delta.x(), delta.y())
            self.oldPos = event.globalPos()

    def process_rotation(self, dx_px, dy_px):
        self.acc_x += dx_px
        self.acc_y += dy_px
        frames_changed = False

        while abs(self.acc_x) >= self.sens_x:
            step = 1 if self.acc_x > 0 else -1
            self.cur_col = (self.cur_col - step) % COLS
            self.acc_x -= (step * self.sens_x)
            frames_changed = True

        while abs(self.acc_y) >= self.sens_y:
            step = 1 if self.acc_y > 0 else -1
            new_row = self.cur_row + step
            if 0 <= new_row < ROWS:
                self.cur_row = new_row
                frames_changed = True
            else:
                self.acc_y = 0
                break
            self.acc_y -= (step * self.sens_y)

        if frames_changed:
            self.update()

    def manual_move(self, dx_frame, dy_frame):
        self.process_rotation(-dx_frame * self.sens_x, dy_frame * self.sens_y)

    def get_current_image_for_canvas(self):
        if not self.is_loaded: return None
        pix = self.matrix_frames[self.cur_row][self.cur_col]

        if self.is_flipped:
            img = pix.toImage().mirrored(True, False)
            return img
        return pix.toImage()




class Free3DHeadDocker(QDockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Free 3D Head Tools")

        self.overlay_window = None
        self.is_interactive = False
        self.is_frozen = False

        main_widget = QWidget()
        self.setWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)


        self.btn_launch = QPushButton("1. Open Floating Window")
        self.btn_launch.setStyleSheet("padding: 8px; font-weight: bold; background-color: #333;")
        self.btn_launch.clicked.connect(self.launch_overlay)
        layout.addWidget(self.btn_launch)


        self.btn_sex = QPushButton("Change to Male Head")
        self.btn_sex.setStyleSheet("background-color: #6a1b9a; color: white; padding: 6px;")
        self.btn_sex.clicked.connect(self.action_change_sex)
        layout.addWidget(self.btn_sex)


        group_controls = QFrame()
        group_controls.setStyleSheet("border: 1px solid #444; border-radius: 5px; margin-top: 5px;")
        layout_g = QVBoxLayout(group_controls)

        lbl_op = QLabel("Opacity")
        lbl_op.setAlignment(Qt.AlignCenter)
        self.slider_op = QSlider(Qt.Horizontal)
        self.slider_op.setRange(20, 100); self.slider_op.setValue(100)
        self.slider_op.valueChanged.connect(self.change_opacity)
        layout_g.addWidget(lbl_op)
        layout_g.addWidget(self.slider_op)

        lbl_size = QLabel("Size (%)")
        lbl_size.setAlignment(Qt.AlignCenter)
        self.slider_size = QSlider(Qt.Horizontal)
        self.slider_size.setRange(20, 150); self.slider_size.setValue(60)
        self.slider_size.valueChanged.connect(self.change_size)
        layout_g.addWidget(lbl_size)
        layout.addWidget(group_controls)


        grid_actions = QGridLayout()

        self.btn_mode = QPushButton("Move/Rotate")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setStyleSheet("background-color: #444; padding: 6px;")
        self.btn_mode.clicked.connect(self.toggle_mode)

        self.btn_freeze = QPushButton("🔒 Block")
        self.btn_freeze.setCheckable(True)
        self.btn_freeze.setStyleSheet("background-color: #E67E22; color: white; padding: 6px;")
        self.btn_freeze.clicked.connect(self.toggle_freeze_mode)

        self.btn_flip = QPushButton("Flip ↔")
        self.btn_flip.setStyleSheet("background-color: #00897b; color: white; padding: 6px;")
        self.btn_flip.clicked.connect(self.action_flip)

        grid_actions.addWidget(self.btn_mode, 0, 0)
        grid_actions.addWidget(self.btn_freeze, 0, 1)
        grid_actions.addWidget(self.btn_flip, 1, 0, 1, 2)

        layout.addLayout(grid_actions)


        lbl_nav = QLabel("Rotation")
        lbl_nav.setAlignment(Qt.AlignCenter)
        lbl_nav.setStyleSheet("margin-top: 5px; color: #888;")
        layout.addWidget(lbl_nav)


        layout_rot = QHBoxLayout()

        btn_rot_left = QPushButton("↺ Turn Left (5°)")
        btn_rot_left.setStyleSheet("padding: 8px;")
        btn_rot_left.clicked.connect(lambda: self.action_step_rotate(-1))

        btn_rot_right = QPushButton("Turn Right (5°) ↻")
        btn_rot_right.setStyleSheet("padding: 8px;")
        btn_rot_right.clicked.connect(lambda: self.action_step_rotate(1))

        layout_rot.addWidget(btn_rot_left)
        layout_rot.addWidget(btn_rot_right)
        layout.addLayout(layout_rot)


        grid_btns = QGridLayout()
        grid_btns.setSpacing(2)

        self.btn_up = self.create_nav_btn("▲", 0, -1)
        self.btn_down = self.create_nav_btn("▼", 0, 1)
        self.btn_left = self.create_nav_btn("◄", -1, 0)
        self.btn_right = self.create_nav_btn("►", 1, 0)
        self.btn_reset = QPushButton("⟳")
        self.btn_reset.setToolTip("Reset View")
        self.btn_reset.clicked.connect(self.reset_pose)

        grid_btns.addWidget(self.btn_up, 0, 1)
        grid_btns.addWidget(self.btn_left, 1, 0)
        grid_btns.addWidget(self.btn_reset, 1, 1)
        grid_btns.addWidget(self.btn_right, 1, 2)
        grid_btns.addWidget(self.btn_down, 2, 1)

        layout.addLayout(grid_btns)


        self.btn_flatten = QPushButton("3. Iron on Canvas")
        self.btn_flatten.setStyleSheet("background-color: #2b8c30; color: white; padding: 12px; font-weight: bold; margin-top: 10px;")
        self.btn_flatten.clicked.connect(self.flatten_to_canvas)
        layout.addWidget(self.btn_flatten)

        layout.addStretch()

    def create_nav_btn(self, text, dx, dy):
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.setAutoRepeat(True)
        btn.clicked.connect(lambda: self.manual_move(dx, dy))
        return btn


    def launch_overlay(self):
        if self.overlay_window is None:
            win = Krita.instance().activeWindow().qwindow() if Krita.instance().activeWindow() else None
            self.overlay_window = HeadOverlayWindow(win)
            self.change_opacity(self.slider_op.value())
            self.change_size(self.slider_size.value())
        self.overlay_window.show()
        self.overlay_window.raise_()

    def change_opacity(self, val):
        if self.overlay_window: self.overlay_window.set_opacity(val)

    def change_size(self, val):
        if self.overlay_window: self.overlay_window.set_scale_percent(val)

    def toggle_mode(self):
        if not self.overlay_window: return
        self.is_interactive = self.btn_mode.isChecked()
        self.overlay_window.set_interaction_mode(self.is_interactive)
        if self.is_interactive:
            self.btn_mode.setStyleSheet("background-color: #0078D7; color: white; padding: 6px;")
        else:
            self.btn_mode.setStyleSheet("background-color: #444; color: white; padding: 6px;")

    def toggle_freeze_mode(self):
        if not self.overlay_window: return
        self.is_frozen = self.btn_freeze.isChecked()
        if self.is_frozen:
            self.btn_freeze.setText("🔒 Unlock")
            self.btn_freeze.setStyleSheet("background-color: #C0392B; color: white; padding: 6px;")
            self.overlay_window.set_click_through(True)
        else:
            self.btn_freeze.setText("🔓 Block")
            self.btn_freeze.setStyleSheet("background-color: #E67E22; color: white; padding: 6px;")
            self.overlay_window.set_click_through(False)

    def action_flip(self):
        if self.overlay_window: self.overlay_window.toggle_flip()

    def action_change_sex(self):
        if self.overlay_window:
            new_text = self.overlay_window.toggle_model_sex()
            self.btn_sex.setText(new_text)

    def action_step_rotate(self, direction):
        """Llama a la rotación geometrica en la ventana"""
        if self.overlay_window:
            self.overlay_window.geo_rotate_step(direction)

    def manual_move(self, dx, dy):
        if self.overlay_window: self.overlay_window.manual_move(dx, dy)

    def reset_pose(self):
        if self.overlay_window: self.overlay_window.reset_view()

    def flatten_to_canvas(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(self, "Error", "there is not an open document.")
            return
        if not self.overlay_window or not self.overlay_window.isVisible():
            QMessageBox.warning(self, "Error", "the floating window is not visible.")
            return

        base_image = self.overlay_window.get_current_image_for_canvas()
        if not base_image: return

        overlay_rect = self.overlay_window.geometry()
        doc_w = doc.width()
        doc_h = doc.height()

        canvas_image = QImage(doc_w, doc_h, QImage.Format_RGBA8888)
        canvas_image.fill(Qt.transparent)

        painter = QPainter(canvas_image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        view_w = overlay_rect.width()
        view_h = overlay_rect.height() - 20

        scaled_img = base_image.scaled(QSize(view_w, view_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        center_x = (doc_w - scaled_img.width()) / 2
        center_y = (doc_h - scaled_img.height()) / 2

        painter.drawImage(int(center_x), int(center_y), scaled_img)
        painter.end()

        ptr = canvas_image.bits()
        ptr.setsize(canvas_image.byteCount())
        pixel_data = QByteArray(ptr.asstring())

        node_name = f"Head Ref ({self.overlay_window.cur_row},{self.overlay_window.cur_col})"
        layer = doc.createNode(node_name, "paintLayer")
        layer.setPixelData(pixel_data, 0, 0, doc_w, doc_h)
        doc.rootNode().addChildNode(layer, None)
        doc.refreshProjection()


class Free3DHeadDockerFactory(DockWidgetFactoryBase):
    def __init__(self):
        super().__init__("free_3dhead_docker", DockWidgetFactoryBase.DockRight)

    def createDockWidget(self):
        return Free3DHeadDocker()