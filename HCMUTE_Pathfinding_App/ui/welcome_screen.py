"""
welcome_screen.py - Modern splash / loading screen for the HCMUTE pathfinding app.
"""

import os
import sys

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import QBitmap, QColor, QFont, QPainter, QPainterPath, QPixmap, QRegion
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.main_window import MainWindow


class WelcomeScreen(QWidget):
    """Frameless welcome screen with smooth loading and transition to MainWindow."""

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(860, 640)
        self.setWindowOpacity(0.0)
        self._apply_rounded_window_mask()

        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if getattr(sys, "frozen", False):
            self._base_dir = os.path.dirname(sys.executable)

        self.banner_path = os.path.join(self._base_dir, "assets", "banner.png")
        self.logo_path = os.path.join(self._base_dir, "assets", "logo.png")
        self.target_path = os.path.join(self._base_dir, "assets", "icon_target.png")
        self.bg_path = os.path.join(self._base_dir, "assets", "welcome_bg.png")
        self.frames_dir = os.path.join(self._base_dir, "assets", "walk_frames")

        self.loading_value = 0
        self._is_transitioning = False
        self._status_messages = [
            "NẠP DỮ LIỆU BẢN ĐỒ HCMUTE",
            "KHỞI TẠO ĐỒ THỊ VÀ CÁC NODE",
            "CHUẨN BỊ THUẬT TOÁN TÌM ĐƯỜNG",
            "ĐỒNG BỘ GIAO DIỆN ĐIỀU HƯỚNG",
        ]

        self._setup_ui()
        self._load_walk_frames()
        self._center_window()
        self._play_intro_animation()

    def _setup_ui(self):
        self.lbl_bg = QLabel(self)
        self.lbl_bg.setGeometry(0, 0, self.width(), self.height())
        self.lbl_bg.setScaledContents(True)
        if os.path.exists(self.bg_path):
            self.lbl_bg.setPixmap(QPixmap(self.bg_path))
            blur = QGraphicsBlurEffect(self)
            blur.setBlurRadius(8)
            blur.setBlurHints(QGraphicsBlurEffect.BlurHint.PerformanceHint)
            self.lbl_bg.setGraphicsEffect(blur)
        else:
            self.lbl_bg.setStyleSheet("background-color: #F5F8FC;")

        self.overlay = QFrame(self)
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.setStyleSheet(
            "background-color: rgba(7, 24, 54, 72); border-radius: 30px;"
        )

        self.card = QFrame(self)
        self.card.setObjectName("welcomeCard")
        self.card.setGeometry(54, 38, 752, 564)
        self.card.setStyleSheet(
            """
            QFrame#welcomeCard {
                background-color: rgba(255, 255, 255, 82);
                border: 1px solid rgba(255, 255, 255, 150);
                border-radius: 28px;
            }
            QLabel {
                font-family: 'Segoe UI';
                background: transparent;
            }
            QLabel#title {
                color: #FFFFFF;
                font-size: 30px;
                font-weight: 900;
            }
            QLabel#statusLabel {
                color: #E9FFFB;
                font-size: 12px;
                font-weight: 800;
            }
            QLabel#percentLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 900;
            }
            QPushButton#btnStart {
                background-color: #0B74FF;
                color: white;
                border: none;
                border-radius: 19px;
                min-width: 176px;
                min-height: 42px;
                font-size: 15px;
                font-weight: 900;
                padding: 0 18px;
            }
            QPushButton#btnStart:hover {
                background-color: #006DFF;
            }
            QPushButton#btnStart:pressed {
                background-color: #075BCC;
            }
            QProgressBar#loadingTrack {
                border: 1px solid rgba(255, 255, 255, 170);
                background-color: rgba(255, 255, 255, 82);
                border-radius: 8px;
                height: 16px;
            }
            QProgressBar#loadingTrack::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0B74FF,
                    stop:0.45 #00D1B2,
                    stop:1 #22C55E
                );
                border-radius: 7px;
            }
            """
        )

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(2, 8, 23, 112))
        self.card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(40, 30, 40, 32)
        layout.setSpacing(14)

        self.lbl_banner = QLabel()
        self.lbl_banner.setFixedSize(672, 224)
        self.lbl_banner.setScaledContents(False)
        self.lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_banner.setStyleSheet("background-color: transparent;")
        self._banner_source = QPixmap(self.banner_path) if os.path.exists(self.banner_path) else QPixmap()
        self._set_banner_pixmap()
        layout.addWidget(self.lbl_banner)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(20)

        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(98, 98)
        self.lbl_logo.setScaledContents(True)
        if os.path.exists(self.logo_path):
            self.lbl_logo.setPixmap(QPixmap(self.logo_path))
        logo_row.addWidget(self.lbl_logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self.lbl_title = QLabel("HỆ THỐNG TÌM ĐƯỜNG HCMUTE")
        self.lbl_title.setObjectName("title")
        title_col.addWidget(self.lbl_title)
        logo_row.addLayout(title_col, 1)
        layout.addLayout(logo_row)

        self.btn_start = QPushButton("BẮT ĐẦU")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_loading)
        layout.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.loading_area = QWidget()
        loading_layout = QVBoxLayout(self.loading_area)
        loading_layout.setContentsMargins(28, 4, 28, 0)
        loading_layout.setSpacing(9)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("SẴN SÀNG KHỞI ĐỘNG")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setObjectName("percentLabel")
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        status_row.addWidget(self.lbl_percent)
        loading_layout.addLayout(status_row)

        self.track_area = QWidget()
        self.track_area.setFixedHeight(104)
        self.track = QProgressBar(self.track_area)
        self.track.setObjectName("loadingTrack")
        self.track.setGeometry(54, 50, 496, 16)
        self.track.setRange(0, 100)
        self.track.setValue(0)
        self.track.setTextVisible(False)

        self.lbl_shimmer = QLabel(self.track_area)
        self.lbl_shimmer.setGeometry(54, 50, 88, 16)
        self.lbl_shimmer.setStyleSheet(
            """
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255,255,255,0),
                stop:0.5 rgba(255,255,255,215),
                stop:1 rgba(255,255,255,0)
            );
            border-radius: 8px;
            """
        )
        self.lbl_shimmer.hide()
        self.lbl_shimmer.raise_()

        self.lbl_target = QLabel(self.track_area)
        self.lbl_target.setGeometry(566, 27, 56, 56)
        self.lbl_target.setScaledContents(True)
        if os.path.exists(self.target_path):
            self.lbl_target.setPixmap(QPixmap(self.target_path))

        self.lbl_pedestrian = QLabel(self.track_area)
        self.lbl_pedestrian.setGeometry(14, 22, 62, 62)
        self.lbl_pedestrian.setScaledContents(False)
        self.lbl_pedestrian.setStyleSheet("background: transparent;")
        loading_layout.addWidget(self.track_area)

        self.loading_area.hide()
        layout.addWidget(self.loading_area)
        layout.addStretch()

    def _load_walk_frames(self):
        self.walk_frames = []
        for i in range(12):
            frame_path = os.path.join(self.frames_dir, f"walk_{i}.png")
            if os.path.exists(frame_path):
                frame = QPixmap(frame_path).scaled(
                    62,
                    62,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.walk_frames.append(frame)

        if self.walk_frames:
            self.lbl_pedestrian.setPixmap(self.walk_frames[0])
        else:
            self.lbl_pedestrian.setText(">")
            self.lbl_pedestrian.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_pedestrian.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
            self.lbl_pedestrian.setStyleSheet("color: #0B74FF; background: transparent;")

    def _set_banner_pixmap(self):
        """Scale banner không méo và hiển thị đầy đủ ảnh."""
        if self._banner_source.isNull():
            return

        target_size = self.lbl_banner.size()
        scaled = self._banner_source.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        rounded = QPixmap(target_size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, target_size.width(), target_size.height(), 18, 18)
        painter.setClipPath(path)
        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self.lbl_banner.setPixmap(rounded)

    def _apply_rounded_window_mask(self):
        """Clip toàn bộ splash thành bo góc thật, kể cả pixmap nền."""
        mask = QBitmap(self.size())
        mask.fill(Qt.GlobalColor.color0)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.color1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 30, 30)
        painter.end()
        self.setMask(QRegion(mask))

    def _play_intro_animation(self):
        self.fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setDuration(520)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in.start()

    def _center_window(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            x = (screen_rect.width() - self.width()) // 2
            y = (screen_rect.height() - self.height()) // 2
            self.move(x, y)

    def _start_loading(self):
        self.btn_start.setEnabled(False)
        self.btn_start.hide()
        self.loading_area.show()
        self.loading_value = 0
        self.track.setValue(0)
        self.lbl_percent.setText("0%")
        self.lbl_status.setText(self._status_messages[0])
        self.lbl_shimmer.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(24)

    def _update_progress(self):
        self.loading_value = min(100, self.loading_value + 1)
        self.track.setValue(self.loading_value)
        self.lbl_percent.setText(f"{self.loading_value}%")

        status_index = min(len(self._status_messages) - 1, self.loading_value // 26)
        self.lbl_status.setText(self._status_messages[status_index])

        start_x = 24
        run_length = 484
        current_x = start_x + int(run_length * (self.loading_value / 100))
        self.lbl_pedestrian.move(current_x, 19)

        track_x = self.track.x()
        track_w = self.track.width()
        shimmer_w = self.lbl_shimmer.width()
        # Shimmer chỉ chạy trong phần thanh đã load, không tràn ra khỏi track.
        loaded_w = max(shimmer_w, int(track_w * (self.loading_value / 100)))
        shimmer_span = max(1, loaded_w - shimmer_w)
        shimmer_x = track_x + int((self.loading_value * 8) % shimmer_span)
        self.lbl_shimmer.move(shimmer_x, 50)
        self.lbl_shimmer.raise_()

        if self.walk_frames:
            frame_index = (self.loading_value // 2) % len(self.walk_frames)
            self.lbl_pedestrian.setPixmap(self.walk_frames[frame_index])

        if self.loading_value >= 100:
            self.timer.stop()
            self.lbl_status.setText("ĐANG MỞ GIAO DIỆN CHÍNH")
            QTimer.singleShot(180, self._open_main_window)

    def _open_main_window(self):
        if self._is_transitioning:
            return
        self._is_transitioning = True

        self.main_app = MainWindow()
        self.main_app.setWindowOpacity(0.0)
        self.main_app.show()

        self.fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setDuration(520)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.main_fade_in = QPropertyAnimation(self.main_app, b"windowOpacity", self)
        self.main_fade_in.setStartValue(0.0)
        self.main_fade_in.setEndValue(1.0)
        self.main_fade_in.setDuration(650)
        self.main_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.fade_out.finished.connect(self.close)
        self.fade_out.start()
        self.main_fade_in.start()
