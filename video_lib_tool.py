"""
Video Library Tool  —  社内ライブラリブラウザ
対応: VIDEO / 連番画像(SEQ) / 単体静止画(STILL)  ×  EXR / PNG / TGA / TIFF / JPG / GIF
"""

# ── SECTION 1: CONFIG & CONSTANTS ───────────────────────────────────────────

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import (
    QDir, QEvent, QMimeData, QObject, QPoint, QRunnable,
    QSize, Qt, QThreadPool, QTimer, Signal, QUrl,
)
from PySide6.QtGui import (
    QAction, QColor, QCursor, QDrag, QFont, QIcon, QImage,
    QPainter, QPen, QPixmap, QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFileSystemModel, QHBoxLayout, QLabel, QLineEdit, QListView,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPushButton, QProgressDialog, QSlider, QSplitter, QStatusBar,
    QTreeView, QVBoxLayout, QWidget, QFrame, QScrollArea,
)

try:
    import OpenImageIO as oiio
except Exception:
    oiio = None

try:
    import numpy as np
except Exception:
    np = None


# ── Format groups ────────────────────────────────────────────────────────────
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".avi", ".mkv", ".wmv", ".mpg", ".mpeg", ".m4v"}
IMAGE_EXTENSIONS = {".exr", ".png", ".tga", ".tiff", ".tif", ".jpg", ".jpeg", ".gif"}
FRAME_PATTERN = re.compile(r"^(?P<base>.*?)(?P<frame>\d+)$")

# ── Thumbnail dimensions ─────────────────────────────────────────────────────
THUMB_W_DEFAULT = 240
THUMB_H_DEFAULT = 135
GRID_PAD_W = 20
GRID_PAD_H = 70

# ── Default tool paths ───────────────────────────────────────────────────────
DEFAULT_RV_PATH = r"T:\tools\DF\thirdparty\win_x64\bin\rv.bat"
DEFAULT_EXR_VIEWER_PATH = r"T:\tools\DF\inhouse\win_x64\standalone\exrTools\_launcher\exrViewer.exe"
DEFAULT_LIBRARY_PATH = r"P:\Library"

# ── Proxy detection ──────────────────────────────────────────────────────────
DEFAULT_PROXY_SUBFOLDERS = ["proxy", "proxies", "_proxy", "preview", "_preview", "low"]
DEFAULT_PROXY_STEM_SUFFIXES = ["_proxy", "_lo", "_preview", "_low", "_p"]

# ── Format badge colours (R, G, B) ───────────────────────────────────────────
FORMAT_BADGE_COLORS: dict[str, tuple[int, int, int]] = {
    ".exr":  (130,  80, 200),
    ".png":  ( 50, 130, 210),
    ".tga":  ( 60, 170, 100),
    ".tiff": ( 60, 170, 100),
    ".tif":  ( 60, 170, 100),
    ".jpg":  (210, 130,  40),
    ".jpeg": (210, 130,  40),
    ".gif":  (200,  80, 130),
    ".mp4":  (200,  60,  60),
    ".mov":  (200,  60,  60),
    ".mxf":  (180,  70,  70),
    ".avi":  (180,  70,  70),
}

# ── Dark QSS ─────────────────────────────────────────────────────────────────
DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
    font-size: 10pt;
}
QMenuBar {
    background-color: #141414;
    color: #d0d0d0;
    border-bottom: 1px solid #333;
}
QMenuBar::item:selected { background-color: #2a2a2a; }
QMenu {
    background-color: #202020;
    color: #d0d0d0;
    border: 1px solid #404040;
}
QMenu::item:selected { background-color: #3d7ebf; color: #fff; }
QTreeView, QListWidget {
    background-color: #1e1e1e;
    border: 1px solid #303030;
    color: #d8d8d8;
    alternate-background-color: #222222;
    outline: none;
}
QTreeView::item:selected, QListWidget::item:selected {
    background-color: #2d5f96;
    color: #ffffff;
}
QTreeView::item:hover, QListWidget::item:hover {
    background-color: #2a3a4a;
}
QLineEdit, QComboBox {
    background-color: #252525;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 3px 6px;
    color: #e0e0e0;
    selection-background-color: #3d7ebf;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #3d7ebf;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #252525;
    border: 1px solid #404040;
    selection-background-color: #3d7ebf;
    color: #e0e0e0;
}
QPushButton {
    background-color: #2e2e2e;
    border: 1px solid #484848;
    border-radius: 4px;
    padding: 4px 12px;
    color: #d8d8d8;
}
QPushButton:hover { background-color: #3a3a3a; border-color: #3d7ebf; }
QPushButton:pressed { background-color: #2a5080; }
QPushButton:disabled { color: #555; border-color: #333; }
QCheckBox { spacing: 6px; color: #d0d0d0; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #555; border-radius: 3px;
    background-color: #252525;
}
QCheckBox::indicator:checked { background-color: #3d7ebf; border-color: #3d7ebf; }
QSlider::groove:horizontal {
    height: 4px; background: #333; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3d7ebf; border-radius: 6px;
    width: 12px; height: 12px; margin: -4px 0;
}
QSlider::sub-page:horizontal { background: #3d7ebf; border-radius: 2px; }
QSplitter::handle { background-color: #2a2a2a; width: 4px; }
QScrollBar:vertical {
    background: #1e1e1e; width: 10px; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #444; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #3d7ebf; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal {
    background: #1e1e1e; height: 10px; border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #444; border-radius: 5px; min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #3d7ebf; }
QStatusBar { background-color: #141414; color: #999; border-top: 1px solid #2a2a2a; }
QLabel { color: #d0d0d0; }
QToolTip {
    background-color: #252525; color: #e0e0e0;
    border: 1px solid #404040; padding: 4px;
}
"""


# ── SECTION 2: SMART CACHE UTILITIES ────────────────────────────────────────

def _local_cache_base() -> Path:
    """ローカルユーザーキャッシュのベースディレクトリ。"""
    app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    base = Path(app_data) / "vlt_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_cache_for_root(root_path: Path) -> Path:
    """
    ルートフォルダ直下の .vlt_cache/ に書き込めればサーバー共有キャッシュとして使用。
    失敗した場合はローカル APPDATA に fallback する。
    """
    server_cache = root_path / ".vlt_cache"
    try:
        server_cache.mkdir(parents=True, exist_ok=True)
        test_file = server_cache / f".write_test_{uuid.uuid4().hex}"
        test_file.touch()
        test_file.unlink()
        return server_cache
    except (PermissionError, OSError):
        pass
    h = hashlib.md5(str(root_path).encode("utf-8")).hexdigest()[:12]
    local = _local_cache_base() / h
    local.mkdir(parents=True, exist_ok=True)
    return local


def local_settings_dir() -> Path:
    """favorites.json / settings.json を置くローカル専用ディレクトリ。"""
    d = _local_cache_base() / "user"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── SECTION 3: PROXY DETECTION ──────────────────────────────────────────────

def find_proxy_for_video(path: Path, proxy_subfolders: list[str], proxy_suffixes: list[str]) -> str | None:
    """動画ファイルに対応するプロキシパスを返す。見つからなければ None。"""
    for sub in proxy_subfolders:
        candidate = path.parent / sub / path.name
        if candidate.exists():
            return str(candidate)
    for suf in proxy_suffixes:
        for ext in [path.suffix, ".mp4", ".mov"]:
            candidate = path.parent / f"{path.stem}{suf}{ext}"
            if candidate.exists():
                return str(candidate)
    return None


def find_proxy_for_sequence(
    folder: Path,
    base_name: str,
    padding: int,
    ext: str,
    proxy_subfolders: list[str],
    proxy_suffixes: list[str],
) -> tuple[str | None, str | None, str | None]:
    """
    連番 EXR/画像に対応するプロキシシーケンスを探す。
    (proxy_sequence_pattern, proxy_first_frame_path, proxy_path) を返す。
    """
    pattern = f"{base_name}%0{padding}d{ext}"

    # Check subfolder proxy sequences
    for sub in proxy_subfolders:
        proxy_folder = folder / sub
        if not proxy_folder.is_dir():
            continue
        test_pattern = re.compile(rf"^{re.escape(base_name)}(\d{{{padding}}}){re.escape(ext)}$")
        frames = sorted(
            [(int(m.group(1)), str(p)) for p in proxy_folder.iterdir()
             if p.is_file() and (m := test_pattern.match(p.name))],
            key=lambda x: x[0],
        )
        if frames:
            first_path = frames[0][1]
            seq_pat = str(proxy_folder / pattern)
            return seq_pat, first_path, first_path

    # Check stem suffix variants in same folder
    for suf in proxy_suffixes:
        proxy_base = f"{base_name}{suf}"
        test_pattern = re.compile(rf"^{re.escape(proxy_base)}(\d{{{padding}}}){re.escape(ext)}$")
        frames = sorted(
            [(int(m.group(1)), str(p)) for p in folder.iterdir()
             if p.is_file() and (m := test_pattern.match(p.name))],
            key=lambda x: x[0],
        )
        if frames:
            first_path = frames[0][1]
            seq_pat = str(folder / f"{proxy_base}%0{padding}d{ext}")
            return seq_pat, first_path, first_path

    return None, None, None


# ── SECTION 4: DATA MODELS ───────────────────────────────────────────────────

@dataclass
class AssetRecord:
    item_type: str           # "VIDEO" | "SEQ" | "STILL"
    format_ext: str          # ".exr" / ".png" / ".mov" 等（バッジ表示用）
    display_name: str
    path_text: str
    open_path: str
    folder_path: str
    range_text: str = "-"
    frame_start: int | None = None
    frame_end: int | None = None
    frame_count: int | None = None
    sequence_pattern: str | None = None
    first_frame_path: str | None = None
    last_frame_path: str | None = None
    proxy_path: str | None = None
    proxy_sequence_pattern: str | None = None
    proxy_first_frame_path: str | None = None
    mtime: float = 0.0

    def asset_key(self) -> str:
        return "|".join([
            self.item_type,
            self.format_ext,
            self.display_name,
            self.open_path or "",
            self.sequence_pattern or "",
            self.range_text or "",
        ])


# ── SECTION 5: IMAGE UTILITIES ───────────────────────────────────────────────

def atomic_promote_file(temp_path: Path, final_path: Path) -> bool:
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
            return True
        os.replace(temp_path, final_path)
        return True
    except Exception:
        temp_path.unlink(missing_ok=True)
    return final_path.exists()


def oiio_pixels_to_qimage(arr) -> QImage | None:
    if np is None:
        return None
    if arr.ndim == 2:
        arr = arr[..., np.newaxis]
    if arr.ndim != 3:
        return None
    channels = arr.shape[2]
    if channels >= 3:
        rgb = arr[..., :3]
    elif channels == 1:
        rgb = np.repeat(arr[..., :1], 3, axis=2)
    else:
        rgb = np.concatenate([arr[..., :1]] * 3, axis=2)

    rgb = np.nan_to_num(rgb, nan=0.0, posinf=0.0, neginf=0.0)
    rgb = np.maximum(rgb, 0.0)

    max_dim = max(rgb.shape[0], rgb.shape[1])
    if max_dim > 512:
        step = max(1, math.ceil(max_dim / 512))
        rgb = rgb[::step, ::step, :]

    sy = max(1, rgb.shape[0] // 128)
    sx = max(1, rgb.shape[1] // 128)
    sample = rgb[::sy, ::sx, :]
    peak = float(np.percentile(sample, 99.5))
    if peak <= 1e-8:
        peak = 1.0

    rgb = np.clip(rgb / peak, 0.0, 1.0)
    rgb = np.power(rgb, 1.0 / 2.2)
    rgb8 = (rgb * 255.0).astype(np.uint8)
    h, w = rgb8.shape[:2]
    image = QImage(rgb8.data, w, h, rgb8.strides[0], QImage.Format.Format_RGB888)
    return image.copy()


def fit_qimage_to_canvas(image: QImage, thumb_w: int, thumb_h: int) -> QImage:
    canvas = QImage(thumb_w, thumb_h, QImage.Format.Format_ARGB32)
    canvas.fill(QColor(24, 24, 24))
    scaled = image.scaled(thumb_w, thumb_h, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    painter = QPainter(canvas)
    painter.drawImage((thumb_w - scaled.width()) // 2, (thumb_h - scaled.height()) // 2, scaled)
    painter.end()
    return canvas


def generate_video_thumbnail(input_path: str, output_path: Path,
                              ffmpeg_path: str | None, thumb_w: int, thumb_h: int) -> bool:
    if not ffmpeg_path or not input_path or not os.path.exists(input_path):
        return False
    temp = output_path.with_name(f"{output_path.stem}.{uuid.uuid4().hex}.tmp.png")
    try:
        cmd = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
               "-i", input_path,
               "-vf", f"thumbnail,scale={thumb_w * 2}:-1:flags=lanczos",
               "-frames:v", "1", str(temp)]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if r.returncode != 0 or not temp.exists():
            temp.unlink(missing_ok=True)
            return False
        return atomic_promote_file(temp, output_path)
    except Exception:
        temp.unlink(missing_ok=True)
    return False


def generate_exr_thumbnail(source_path: str, output_path: Path,
                            thumb_w: int, thumb_h: int) -> bool:
    if oiio is None or np is None or not source_path or not os.path.exists(source_path):
        return False
    temp = output_path.with_name(f"{output_path.stem}.{uuid.uuid4().hex}.tmp.png")
    try:
        buf = oiio.ImageBuf(source_path)
        pixels = buf.get_pixels(oiio.FLOAT)
        if pixels is None:
            return False
        arr = np.asarray(pixels)
        if arr.size == 0:
            return False
        image = oiio_pixels_to_qimage(arr)
        if image is None or image.isNull():
            return False
        thumb = fit_qimage_to_canvas(image, thumb_w, thumb_h)
        if not thumb.save(str(temp)):
            temp.unlink(missing_ok=True)
            return False
        return atomic_promote_file(temp, output_path)
    except Exception:
        temp.unlink(missing_ok=True)
    return False


def generate_qt_thumbnail(source_path: str, output_path: Path,
                           thumb_w: int, thumb_h: int) -> bool:
    """PNG / TGA / TIFF / JPG / GIF など Qt 標準対応フォーマット用。"""
    if not source_path or not os.path.exists(source_path):
        return False
    temp = output_path.with_name(f"{output_path.stem}.{uuid.uuid4().hex}.tmp.png")
    try:
        img = QImage(source_path)
        if img.isNull():
            return False
        thumb = fit_qimage_to_canvas(img, thumb_w, thumb_h)
        if not thumb.save(str(temp)):
            temp.unlink(missing_ok=True)
            return False
        return atomic_promote_file(temp, output_path)
    except Exception:
        temp.unlink(missing_ok=True)
    return False


def dispatch_thumbnail(record: AssetRecord, output_path: Path,
                        ffmpeg_path: str | None, thumb_w: int, thumb_h: int) -> bool:
    """レコード種別・プロキシ有無に応じてサムネイル生成を振り分ける。"""
    if record.item_type == "VIDEO":
        source = record.proxy_path or record.open_path
        return generate_video_thumbnail(source, output_path, ffmpeg_path, thumb_w, thumb_h)

    # SEQ / STILL
    source = (record.proxy_first_frame_path or record.proxy_path
              or record.first_frame_path or record.open_path)
    if not source:
        return False
    ext = Path(source).suffix.lower()
    if ext == ".exr" and oiio is not None and np is not None:
        return generate_exr_thumbnail(source, output_path, thumb_w, thumb_h)
    return generate_qt_thumbnail(source, output_path, thumb_w, thumb_h)


# ── SECTION 6: BACKGROUND WORKERS ───────────────────────────────────────────

class ThumbnailWorkerSignals(QObject):
    finished = Signal(str, int, str)   # asset_key, generation, thumb_path
    failed   = Signal(str, int)        # asset_key, generation


class ThumbnailWorker(QRunnable):
    def __init__(self, asset_key: str, record: AssetRecord, generation: int,
                 output_path: Path, ffmpeg_path: str | None,
                 thumb_w: int, thumb_h: int):
        super().__init__()
        self.asset_key = asset_key
        self.record = record
        self.generation = generation
        self.output_path = output_path
        self.ffmpeg_path = ffmpeg_path
        self.thumb_w = thumb_w
        self.thumb_h = thumb_h
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            if self.output_path.exists():
                self.signals.finished.emit(self.asset_key, self.generation,
                                           str(self.output_path))
                return
            ok = dispatch_thumbnail(self.record, self.output_path,
                                    self.ffmpeg_path, self.thumb_w, self.thumb_h)
            if ok and self.output_path.exists():
                self.signals.finished.emit(self.asset_key, self.generation,
                                           str(self.output_path))
            else:
                self.signals.failed.emit(self.asset_key, self.generation)
        except Exception:
            self.signals.failed.emit(self.asset_key, self.generation)


# ── SECTION 7: CUSTOM WIDGETS ────────────────────────────────────────────────

class DraggableFloatingWidget(QWidget):
    """マウスでドラッグして移動できるフローティングウィジェット。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset: QPoint | None = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class FolderTreeModel(QFileSystemModel):
    def hasChildren(self, parent=None):
        if parent is None or not parent.isValid():
            return super().hasChildren(parent) if parent else False
        path_text = self.filePath(parent)
        if not path_text:
            return False
        try:
            with os.scandir(path_text) as it:
                for entry in it:
                    if entry.name not in {".", ".."} and entry.is_dir(follow_symlinks=False):
                        return True
        except Exception:
            pass
        return False


class SearchFilterBar(QWidget):
    """検索テキスト / タイプ / フォーマット / ソート / サブフォルダ / サムネイルサイズ。"""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Search…")
        self.search_edit.setMinimumWidth(180)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.changed)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Types", "VIDEO", "SEQUENCE", "STILL"])
        self.type_combo.setFixedWidth(110)
        self.type_combo.currentIndexChanged.connect(self.changed)

        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["All Formats", "EXR", "PNG", "TGA", "TIFF", "JPG", "GIF",
                                  "MP4", "MOV", "MXF"])
        self.fmt_combo.setFixedWidth(110)
        self.fmt_combo.currentIndexChanged.connect(self.changed)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name A→Z", "Name Z→A", "Date (New)", "Date (Old)", "Type"])
        self.sort_combo.setFixedWidth(110)
        self.sort_combo.currentIndexChanged.connect(self.changed)

        self.subfolder_check = QCheckBox("Subfolders")
        self.subfolder_check.stateChanged.connect(self.changed)

        size_label = QLabel("Size:")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(120, 400)
        self.size_slider.setValue(THUMB_W_DEFAULT)
        self.size_slider.setFixedWidth(90)
        self.size_slider.setTickInterval(40)
        self.size_slider.valueChanged.connect(self.changed)

        layout.addWidget(self.search_edit, stretch=1)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.fmt_combo)
        layout.addWidget(self.sort_combo)
        layout.addWidget(self.subfolder_check)
        layout.addWidget(size_label)
        layout.addWidget(self.size_slider)

    # ── accessor helpers ─────────────────────────────────────────────────────
    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    @property
    def type_filter(self) -> str:
        return self.type_combo.currentText()

    @property
    def fmt_filter(self) -> str:
        return self.fmt_combo.currentText()

    @property
    def sort_key(self) -> str:
        return self.sort_combo.currentText()

    @property
    def include_subfolders(self) -> bool:
        return self.subfolder_check.isChecked()

    @property
    def thumb_size(self) -> int:
        return self.size_slider.value()


class BreadcrumbBar(QWidget):
    """クリッカブルなパスブレッドクラム。"""
    segment_clicked = Signal(str)   # クリックされたパス文字列

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch()

    def set_path(self, path: Path | None, root: Path | None = None):
        # 既存ウィジェットをクリア
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if path is None:
            return

        try:
            parts = path.relative_to(root).parts if root else path.parts
            accumulated = root or Path(path.anchor)
        except ValueError:
            parts = path.parts
            accumulated = Path(path.anchor)

        idx = 0
        for part in parts:
            accumulated = accumulated / part
            acc_copy = str(accumulated)

            if idx > 0:
                sep = QLabel("▸")
                sep.setStyleSheet("color: #555; padding: 0 2px;")
                self._layout.insertWidget(self._layout.count() - 1, sep)

            btn = QPushButton(part)
            btn.setFlat(True)
            btn.setStyleSheet(
                "QPushButton { color: #7ab0e0; text-decoration: none; padding: 2px 4px; "
                "border: none; background: transparent; font-size: 9pt; }"
                "QPushButton:hover { color: #aad4ff; text-decoration: underline; }"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=acc_copy: self.segment_clicked.emit(p))
            self._layout.insertWidget(self._layout.count() - 1, btn)
            idx += 1


class AssetGridWidget(QListWidget):
    """アセットグリッド。Ctrl+ドラッグ時にコピーダイアログを呼び出す。"""

    def __init__(self, payload_builder, copy_drag_handler, parent=None):
        super().__init__(parent)
        self.payload_builder = payload_builder
        self.copy_drag_handler = copy_drag_handler
        self._drag_start_pos: QPoint | None = None
        self._pressed_item: QListWidgetItem | None = None

        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._pressed_item = item
        if item:
            self.setCurrentItem(item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton
                and self._drag_start_pos is not None
                and self._pressed_item is not None):
            dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self.setCurrentItem(self._pressed_item)
                self.startDrag(Qt.DropAction.CopyAction)
                self._drag_start_pos = None
                self._pressed_item = None
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._pressed_item = None
        super().mouseReleaseEvent(event)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None and self.selectedItems():
            item = self.selectedItems()[0]
        if item is None:
            return
        record: AssetRecord | None = item.data(Qt.ItemDataRole.UserRole)
        if record is None:
            return

        ctrl_held = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)

        if ctrl_held:
            # コピーダイアログ経由でドラッグ
            result = self.copy_drag_handler(record)
            if result is None:
                return
            text_payloads, url_payloads = result
        else:
            text_payloads, url_payloads = self.payload_builder(record, prefer_nuke_drop=False)

        if not text_payloads and not url_payloads:
            return

        mime = QMimeData()
        if text_payloads:
            mime.setText("\n".join(text_payloads))
        if url_payloads:
            mime.setUrls(url_payloads)

        drag = QDrag(self)
        drag.setMimeData(mime)
        preview = item.icon().pixmap(self.iconSize())
        if not preview.isNull():
            drag.setPixmap(preview)
            drag.setHotSpot(preview.rect().center())
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                  Qt.DropAction.CopyAction)


# ── SECTION 8: DIALOGS ───────────────────────────────────────────────────────

class FavoriteManagerDialog(QDialog):
    def __init__(self, favorites: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Favorites")
        self.resize(580, 380)
        self.result_favorites = list(favorites)

        self.list_widget = QListWidget()
        for p in favorites:
            item = QListWidgetItem(p)
            if not Path(p).exists():
                item.setForeground(QColor("#c05050"))
                item.setToolTip("Path does not exist")
            self.list_widget.addItem(item)

        up_btn    = QPushButton("↑ Up")
        down_btn  = QPushButton("↓ Down")
        remove_btn = QPushButton("Remove")
        ok_btn    = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")

        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        remove_btn.clicked.connect(self._remove)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Red entries indicate paths that no longer exist."))
        layout.addWidget(self.list_widget, stretch=1)
        layout.addLayout(btn_row)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row <= 0:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, item)
        self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= self.list_widget.count() - 1:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, item)
        self.list_widget.setCurrentRow(row + 1)

    def _remove(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def accept(self):
        self.result_favorites = [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
        ]
        super().accept()


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 400)
        self._settings = dict(settings)

        def _row(label_text, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(180)
            row.addWidget(lbl)
            row.addWidget(widget, stretch=1)
            return row

        # Default root
        self.root_edit = QLineEdit(settings.get("default_root", ""))
        root_browse = QPushButton("…")
        root_browse.setFixedWidth(28)
        root_browse.clicked.connect(self._browse_root)
        root_row = QHBoxLayout()
        root_lbl = QLabel("Default Root Folder:")
        root_lbl.setFixedWidth(180)
        root_row.addWidget(root_lbl)
        root_row.addWidget(self.root_edit, stretch=1)
        root_row.addWidget(root_browse)

        # RV path
        self.rv_edit = QLineEdit(settings.get("rv_path", DEFAULT_RV_PATH))
        rv_browse = QPushButton("…")
        rv_browse.setFixedWidth(28)
        rv_browse.clicked.connect(lambda: self._browse_exe(self.rv_edit, "RV Player"))
        rv_row = QHBoxLayout()
        rv_lbl = QLabel("RV Player Path:")
        rv_lbl.setFixedWidth(180)
        rv_row.addWidget(rv_lbl)
        rv_row.addWidget(self.rv_edit, stretch=1)
        rv_row.addWidget(rv_browse)

        # exrViewer path
        self.exr_viewer_edit = QLineEdit(settings.get("exr_viewer_path", DEFAULT_EXR_VIEWER_PATH))
        ev_browse = QPushButton("…")
        ev_browse.setFixedWidth(28)
        ev_browse.clicked.connect(lambda: self._browse_exe(self.exr_viewer_edit, "EXR Viewer"))
        ev_row = QHBoxLayout()
        ev_lbl = QLabel("EXR Viewer Path:")
        ev_lbl.setFixedWidth(180)
        ev_row.addWidget(ev_lbl)
        ev_row.addWidget(self.exr_viewer_edit, stretch=1)
        ev_row.addWidget(ev_browse)

        # Proxy subfolders
        self.proxy_sub_edit = QLineEdit(", ".join(settings.get("proxy_subfolders", DEFAULT_PROXY_SUBFOLDERS)))
        # Proxy suffixes
        self.proxy_sfx_edit = QLineEdit(", ".join(settings.get("proxy_suffixes", DEFAULT_PROXY_STEM_SUFFIXES)))

        ok_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(root_row)
        layout.addLayout(rv_row)
        layout.addLayout(ev_row)
        layout.addLayout(_row("Proxy Subfolders (comma-sep):", self.proxy_sub_edit))
        layout.addLayout(_row("Proxy Stem Suffixes (comma-sep):", self.proxy_sfx_edit))
        layout.addStretch()
        layout.addLayout(btn_row)

    def _browse_root(self):
        d = QFileDialog.getExistingDirectory(self, "Select Default Root", self.root_edit.text())
        if d:
            self.root_edit.setText(d)

    def _browse_exe(self, edit: QLineEdit, caption: str):
        f, _ = QFileDialog.getOpenFileName(self, f"Select {caption}", edit.text())
        if f:
            edit.setText(f)

    def accept(self):
        self._settings["default_root"]    = self.root_edit.text().strip()
        self._settings["rv_path"]         = self.rv_edit.text().strip()
        self._settings["exr_viewer_path"] = self.exr_viewer_edit.text().strip()
        self._settings["proxy_subfolders"] = [
            s.strip() for s in self.proxy_sub_edit.text().split(",") if s.strip()
        ]
        self._settings["proxy_suffixes"] = [
            s.strip() for s in self.proxy_sfx_edit.text().split(",") if s.strip()
        ]
        super().accept()

    @property
    def result_settings(self) -> dict:
        return self._settings


class CopyDestinationDialog(QDialog):
    """Ctrl+ドラッグ時に表示するコピー先選択ダイアログ。"""

    def __init__(self, record: AssetRecord, recent_dirs: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Copy Asset")
        self.resize(500, 200)
        self.record = record
        self.chosen_dir: str | None = None
        self.do_copy = False

        label = QLabel(
            f"Asset: <b>{record.display_name}</b><br>"
            f"Type: {record.item_type}"
            + (f"  Frames: {record.frame_count}" if record.frame_count else "")
        )
        label.setTextFormat(Qt.TextFormat.RichText)

        self.dest_combo = QComboBox()
        self.dest_combo.setEditable(True)
        self.dest_combo.addItems(recent_dirs)
        self.dest_combo.setPlaceholderText("Select or type destination folder…")

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        combo_row = QHBoxLayout()
        combo_row.addWidget(self.dest_combo, stretch=1)
        combo_row.addWidget(browse_btn)

        copy_btn    = QPushButton("Copy & Drag")
        original_btn = QPushButton("Drag Original")
        cancel_btn  = QPushButton("Cancel")
        copy_btn.setDefault(True)
        copy_btn.clicked.connect(self._accept_copy)
        original_btn.clicked.connect(self._accept_original)
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(original_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addLayout(combo_row)
        layout.addStretch()
        layout.addLayout(btn_row)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Destination",
                                             self.dest_combo.currentText())
        if d:
            self.dest_combo.setCurrentText(d)

    def _accept_copy(self):
        dest = self.dest_combo.currentText().strip()
        if not dest:
            QMessageBox.warning(self, "Copy Asset", "Please select a destination folder.")
            return
        self.chosen_dir = dest
        self.do_copy = True
        self.accept()

    def _accept_original(self):
        self.do_copy = False
        self.accept()


# ── SECTION 9: MAIN WINDOW ───────────────────────────────────────────────────

class MainWindow(QMainWindow):

    # ── init ─────────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self._init_state()
        self.load_settings()
        self.ffmpeg_path = self.find_ffmpeg()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(min(4, max(2, os.cpu_count() or 4)))
        self.setWindowTitle("Video Library Tool")
        self.resize(1540, 920)
        self._build_ui()
        self._build_menu()
        self._apply_shortcuts()
        QApplication.instance().installEventFilter(self)
        self.load_favorites()
        self.statusBar().showMessage("Ready")
        self.try_open_default_root()

    def _init_state(self):
        self._settings: dict = {}
        self.root_folder: Path | None = None
        self.current_folder: Path | None = None
        self.cache_root: Path = _local_cache_base()
        self.thumb_cache_dir: Path = self.cache_root / "thumbs"
        self.hover_cache_dir: Path = self.cache_root / "hover"
        self.nuke_drop_dir: Path = self.cache_root / "nuke_drop"
        self.thumb_w: int = THUMB_W_DEFAULT
        self.thumb_h: int = THUMB_H_DEFAULT
        self._all_records: list[AssetRecord] = []
        self.scan_generation: int = 0
        self.asset_items: dict[str, QListWidgetItem] = {}
        self.pending_thumbnail_keys: set[str] = set()
        self.placeholder_icons: dict = {}
        self.favorite_paths: list[str] = []
        self.sequence_file_cache: dict[str, list[str]] = {}
        self.video_preview_cache: dict[str, list[str]] = {}
        self.hovered_item: QListWidgetItem | None = None
        self.hover_original_icon: QIcon | None = None
        self.hover_preview_paths: list[str] = []
        self.hover_preview_index: int = 0
        self.overlay_preview_paths: list[str] = []
        self.overlay_preview_index: int = 0
        self._copy_recent_dirs: list[str] = []

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── toolbar row ──────────────────────────────────────────────────────
        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setFixedWidth(84)
        self.home_btn.setToolTip("Open default library root")
        self.home_btn.clicked.connect(
            lambda: self.open_root_path(self._settings.get("default_root", DEFAULT_LIBRARY_PATH))
        )

        self.breadcrumb = BreadcrumbBar()
        self.breadcrumb.segment_clicked.connect(self.open_root_path)

        self.add_fav_btn = QPushButton("★")
        self.add_fav_btn.setFixedWidth(30)
        self.add_fav_btn.setToolTip("Add current folder to favorites")
        self.add_fav_btn.clicked.connect(self.add_current_to_favorites)

        self.fav_btn = QPushButton("Favorites ▾")
        self.fav_btn.setFixedWidth(110)
        self.fav_btn.clicked.connect(self.show_favorites_menu)

        self.overlay_toggle = QCheckBox("⧉ Overlay")
        self.overlay_toggle.setToolTip("Show hover preview in floating overlay window")
        self.overlay_toggle.toggled.connect(self.on_preview_mode_changed)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedWidth(30)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(6)
        toolbar_layout.addWidget(self.home_btn)
        toolbar_layout.addWidget(self.breadcrumb, stretch=1)
        toolbar_layout.addWidget(self.add_fav_btn)
        toolbar_layout.addWidget(self.fav_btn)
        toolbar_layout.addWidget(self.overlay_toggle)
        toolbar_layout.addWidget(self.settings_btn)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)
        toolbar_widget.setObjectName("toolbar")
        toolbar_widget.setStyleSheet("#toolbar { border-bottom: 1px solid #2a2a2a; }")

        # ── search/filter bar ────────────────────────────────────────────────
        self.filter_bar = SearchFilterBar()
        self.filter_bar.changed.connect(self.apply_filter)

        # ── folder tree (left panel) ─────────────────────────────────────────
        self.folder_model = FolderTreeModel()
        self.folder_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        self.folder_model.setRootPath("")

        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.folder_model)
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setAnimated(True)
        self.folder_tree.hideColumn(1)
        self.folder_tree.hideColumn(2)
        self.folder_tree.hideColumn(3)
        self.folder_tree.clicked.connect(self.on_folder_clicked)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self.show_folder_context_menu)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.folder_tree)

        # ── asset grid (right panel) ─────────────────────────────────────────
        self.asset_grid = AssetGridWidget(
            payload_builder=self.build_drag_payload,
            copy_drag_handler=self.handle_copy_drag,
            parent=self,
        )
        self.asset_grid.setViewMode(QListView.ViewMode.IconMode)
        self.asset_grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.asset_grid.setMovement(QListView.Movement.Static)
        self.asset_grid.setSpacing(12)
        self.asset_grid.setWrapping(True)
        self.asset_grid.setWordWrap(True)
        self.asset_grid.setUniformItemSizes(False)
        self.asset_grid.setIconSize(QSize(self.thumb_w, self.thumb_h))
        self.asset_grid.setGridSize(QSize(self.thumb_w + GRID_PAD_W,
                                          self.thumb_h + GRID_PAD_H))
        self.asset_grid.setMouseTracking(True)
        self.asset_grid.viewport().installEventFilter(self)
        self.asset_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.asset_grid.customContextMenuRequested.connect(self.show_asset_context_menu)
        self.asset_grid.itemDoubleClicked.connect(self.open_selected_asset)
        self.asset_grid.currentItemChanged.connect(self.update_selection_info)
        self.asset_grid.itemEntered.connect(self.on_item_hovered)

        # ── info panel ───────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a2a;")

        self.info_label = QLabel("Select a root folder to start browsing.")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.info_label.setStyleSheet(
            "padding: 6px 8px; color: #999; font-size: 9pt; min-height: 80px; max-height: 120px;"
        )

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.asset_grid, stretch=1)
        right_layout.addWidget(sep)
        right_layout.addWidget(self.info_label)

        # ── splitter ─────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 1180])

        # ── central layout ───────────────────────────────────────────────────
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_widget)
        main_layout.addWidget(self.filter_bar)
        main_layout.addWidget(splitter, stretch=1)
        self.setCentralWidget(central)

        # ── overlay preview (floating) ────────────────────────────────────────
        self.overlay_preview_widget = DraggableFloatingWidget(None)
        self.overlay_preview_widget.setWindowFlags(Qt.WindowType.Tool)
        self.overlay_preview_widget.setStyleSheet(
            "background-color: rgba(22,22,22,235); border: 1px solid #505050; border-radius: 6px;"
        )
        self.overlay_preview_widget.resize(720, 472)
        ov_layout = QVBoxLayout(self.overlay_preview_widget)
        ov_layout.setContentsMargins(8, 8, 8, 8)
        ov_layout.setSpacing(4)
        self.overlay_title_label = QLabel("Preview")
        self.overlay_title_label.setStyleSheet("color: #ddd; font-weight: bold;")
        self.overlay_image_label = QLabel()
        self.overlay_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_image_label.setMinimumSize(688, 388)
        self.overlay_image_label.setStyleSheet("background-color: #0c0c0c; color: #555;")
        ov_layout.addWidget(self.overlay_title_label)
        ov_layout.addWidget(self.overlay_image_label, stretch=1)
        self.overlay_preview_widget.move(self.x() + 80, self.y() + 80)
        self.overlay_preview_widget.hide()

        # ── hover/preview timer ───────────────────────────────────────────────
        self.hover_preview_timer = QTimer(self)
        self.hover_preview_timer.setInterval(120)
        self.hover_preview_timer.timeout.connect(self.advance_inline_preview)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self._action("Select Root Folder…", self.select_root_folder))
        file_menu.addAction(self._action("Refresh", self.scan_current_folder,
                                          shortcut="F5"))
        view_menu = self.menuBar().addMenu("View")
        self.overlay_menu_action = QAction("Overlay Preview", self)
        self.overlay_menu_action.setCheckable(True)
        self.overlay_menu_action.toggled.connect(self.overlay_toggle.setChecked)
        self.overlay_toggle.toggled.connect(self.overlay_menu_action.setChecked)
        view_menu.addAction(self.overlay_menu_action)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self._action("Show Info", self.show_info_dialog))

    @staticmethod
    def _action(text: str, slot, shortcut: str | None = None) -> QAction:
        act = QAction(text)
        act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        return act

    def _apply_shortcuts(self):
        from PySide6.QtGui import QShortcut
        QShortcut(QKeySequence("F5"), self, activated=self.scan_current_folder)
        QShortcut(QKeySequence("Ctrl+F"), self,
                  activated=lambda: self.filter_bar.search_edit.setFocus())


    # ── settings / favorites ──────────────────────────────────────────────────

    def load_settings(self):
        defaults = {
            "default_root": DEFAULT_LIBRARY_PATH,
            "rv_path": DEFAULT_RV_PATH,
            "exr_viewer_path": DEFAULT_EXR_VIEWER_PATH,
            "proxy_subfolders": DEFAULT_PROXY_SUBFOLDERS,
            "proxy_suffixes": DEFAULT_PROXY_STEM_SUFFIXES,
            "copy_recent_dirs": [],
        }
        path = local_settings_dir() / "settings.json"
        try:
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    defaults.update(loaded)
        except Exception:
            pass
        self._settings = defaults
        self._copy_recent_dirs = list(self._settings.get("copy_recent_dirs", []))

    def save_settings(self):
        self._settings["copy_recent_dirs"] = self._copy_recent_dirs
        try:
            path = local_settings_dir() / "settings.json"
            path.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        except Exception:
            pass

    def open_settings_dialog(self):
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._settings = dlg.result_settings
            self.save_settings()

    def load_favorites(self):
        try:
            path = local_settings_dir() / "favorites.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.favorite_paths = [p for p in data if isinstance(p, str) and p]
        except Exception:
            self.favorite_paths = []

    def save_favorites(self):
        try:
            path = local_settings_dir() / "favorites.json"
            path.write_text(json.dumps(self.favorite_paths, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        except Exception:
            pass

    def add_current_to_favorites(self):
        if not self.current_folder:
            return
        p = str(self.current_folder)
        if p not in self.favorite_paths:
            self.favorite_paths.append(p)
            self.save_favorites()
            self.statusBar().showMessage(f"Added to favorites: {p}", 3000)

    def remove_favorite_path(self, path_text: str):
        self.favorite_paths = [p for p in self.favorite_paths if p != path_text]
        self.save_favorites()

    def show_favorites_menu(self):
        menu = QMenu(self)
        if self.favorite_paths:
            for p in self.favorite_paths:
                action = menu.addAction(p)
                action.triggered.connect(lambda _=False, fp=p: self.open_root_path(fp))
            menu.addSeparator()
        manage_act = menu.addAction("Manage Favorites…")
        manage_act.triggered.connect(self.open_favorite_manager)
        menu.exec(self.fav_btn.mapToGlobal(self.fav_btn.rect().bottomLeft()))

    def open_favorite_manager(self):
        dlg = FavoriteManagerDialog(self.favorite_paths, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.favorite_paths = dlg.result_favorites
            self.save_favorites()

    # ── folder navigation ─────────────────────────────────────────────────────

    def try_open_default_root(self):
        p = Path(self._settings.get("default_root", DEFAULT_LIBRARY_PATH))
        if p.exists():
            self.open_root_path(str(p))

    def select_root_folder(self):
        start = str(self.root_folder or
                    Path(self._settings.get("default_root", DEFAULT_LIBRARY_PATH)))
        folder = QFileDialog.getExistingDirectory(self, "Select Root Folder", start)
        if folder:
            self.open_root_path(folder)

    def open_root_path(self, folder_text: str):
        folder_path = Path(folder_text)
        if not folder_path.exists():
            return
        self.root_folder = folder_path
        self.current_folder = folder_path

        # ── キャッシュディレクトリ切り替え ──────────────────────────────────
        self.cache_root = resolve_cache_for_root(folder_path)
        self.thumb_cache_dir = self.cache_root / "thumbs"
        self.hover_cache_dir = self.cache_root / "hover"
        self.nuke_drop_dir   = self.cache_root / "nuke_drop"
        for d in (self.thumb_cache_dir, self.hover_cache_dir, self.nuke_drop_dir):
            d.mkdir(parents=True, exist_ok=True)

        # ── フォルダツリーのルートを更新 ────────────────────────────────────
        root_index = self.folder_model.setRootPath(str(folder_path))
        self.folder_tree.setRootIndex(root_index)
        self.folder_tree.expand(root_index)
        self.folder_tree.setCurrentIndex(root_index)

        self.breadcrumb.set_path(folder_path, folder_path)
        self.scan_current_folder()

        # キャッシュ場所をステータスバーに表示
        server = (self.cache_root == folder_path / ".vlt_cache")
        loc = "server" if server else "local"
        self.statusBar().showMessage(f"Root: {folder_path}  |  Cache: {self.cache_root} ({loc})")

    def on_folder_clicked(self, index):
        folder_path = Path(self.folder_model.filePath(index))
        self.current_folder = folder_path
        self.breadcrumb.set_path(folder_path, self.root_folder)
        self.scan_current_folder()

    # ── scan & filter ─────────────────────────────────────────────────────────

    def scan_current_folder(self):
        self.scan_generation += 1
        current_gen = self.scan_generation

        self.stop_inline_preview()
        self.asset_grid.clear()
        self.asset_items.clear()
        self.pending_thumbnail_keys.clear()
        self.sequence_file_cache.clear()
        self.video_preview_cache.clear()

        if not self.current_folder or not self.current_folder.exists():
            self.info_label.setText("No folder selected or folder does not exist.")
            self.statusBar().showMessage("No folder")
            return

        if self.filter_bar.include_subfolders:
            file_paths = [p for p in self.current_folder.rglob("*") if p.is_file()]
        else:
            file_paths = [p for p in self.current_folder.iterdir() if p.is_file()]

        self._all_records = self.build_asset_records(file_paths, self.current_folder)
        self.apply_filter(scan_gen=current_gen)

    def build_asset_records(self, file_paths: list[Path], base_folder: Path) -> list[AssetRecord]:
        proxy_subs = self._settings.get("proxy_subfolders", DEFAULT_PROXY_SUBFOLDERS)
        proxy_sfx  = self._settings.get("proxy_suffixes",   DEFAULT_PROXY_STEM_SUFFIXES)

        video_paths: list[Path] = []
        image_groups: dict = defaultdict(list)
        single_images: list[Path] = []

        for path in file_paths:
            ext = path.suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                video_paths.append(path)
            elif ext in IMAGE_EXTENSIONS:
                m = FRAME_PATTERN.match(path.stem)
                if m:
                    key = (path.parent, m.group("base"), len(m.group("frame")), ext)
                    image_groups[key].append((int(m.group("frame")), path))
                else:
                    single_images.append(path)

        records: list[AssetRecord] = []

        # ── VIDEO ─────────────────────────────────────────────────────────────
        for path in sorted(video_paths, key=lambda p: p.name.lower()):
            proxy = find_proxy_for_video(path, proxy_subs, proxy_sfx)
            records.append(AssetRecord(
                item_type="VIDEO",
                format_ext=path.suffix.lower(),
                display_name=path.name,
                path_text=self.safe_relative_text(path, base_folder),
                open_path=str(path),
                folder_path=str(path.parent),
                proxy_path=proxy,
                mtime=self._get_mtime(path),
            ))

        # ── SEQ (連番画像) ────────────────────────────────────────────────────
        for key in sorted(image_groups.keys(),
                          key=lambda k: (str(k[0]).lower(), k[1].lower())):
            parent_folder, base_name, padding, ext = key
            frames = sorted(image_groups[key], key=lambda x: x[0])
            frame_numbers = [f for f, _ in frames]
            first_path = frames[0][1]
            last_path  = frames[-1][1]
            fs, fe, fc = frame_numbers[0], frame_numbers[-1], len(frame_numbers)

            if fs == fe:
                display_name = f"{base_name}{fs:0{padding}d}{ext}"
            else:
                display_name = f"{base_name}{fs:0{padding}d}-{fe:0{padding}d}{ext}"

            seq_pat = f"{base_name}%0{padding}d{ext}"
            rel_folder = self.safe_relative_text(parent_folder, base_folder)
            path_text = display_name if rel_folder == "." else str(Path(rel_folder) / display_name)

            proxy_pat, proxy_first, proxy_path = find_proxy_for_sequence(
                parent_folder, base_name, padding, ext, proxy_subs, proxy_sfx)

            records.append(AssetRecord(
                item_type="SEQ",
                format_ext=ext,
                display_name=display_name,
                path_text=path_text,
                open_path=str(first_path),
                folder_path=str(parent_folder),
                range_text=f"{fs}-{fe} ({fc}f)",
                frame_start=fs, frame_end=fe, frame_count=fc,
                sequence_pattern=seq_pat,
                first_frame_path=str(first_path),
                last_frame_path=str(last_path),
                proxy_path=proxy_path,
                proxy_sequence_pattern=proxy_pat,
                proxy_first_frame_path=proxy_first,
                mtime=self._get_mtime(first_path),
            ))

        # ── STILL (単体静止画) ────────────────────────────────────────────────
        for path in sorted(single_images, key=lambda p: p.name.lower()):
            proxy = find_proxy_for_video(path, proxy_subs, proxy_sfx)
            records.append(AssetRecord(
                item_type="STILL",
                format_ext=path.suffix.lower(),
                display_name=path.name,
                path_text=self.safe_relative_text(path, base_folder),
                open_path=str(path),
                folder_path=str(path.parent),
                proxy_path=proxy,
                mtime=self._get_mtime(path),
            ))

        return records

    @staticmethod
    def _get_mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except Exception:
            return 0.0

    def apply_filter(self, scan_gen: int | None = None):
        if scan_gen is None:
            scan_gen = self.scan_generation

        # ── サムネイルサイズ更新 ─────────────────────────────────────────────
        tw = self.filter_bar.thumb_size
        self.thumb_w = tw
        self.thumb_h = tw * 9 // 16
        self.asset_grid.setIconSize(QSize(self.thumb_w, self.thumb_h))
        self.asset_grid.setGridSize(QSize(self.thumb_w + GRID_PAD_W,
                                          self.thumb_h + GRID_PAD_H))

        search = self.filter_bar.search_text
        type_f = self.filter_bar.type_filter
        fmt_f  = self.filter_bar.fmt_filter.lower()
        sort_k = self.filter_bar.sort_key

        def matches(r: AssetRecord) -> bool:
            if search and search not in r.display_name.lower() and search not in r.path_text.lower():
                return False
            if type_f == "VIDEO"    and r.item_type != "VIDEO":  return False
            if type_f == "SEQUENCE" and r.item_type != "SEQ":    return False
            if type_f == "STILL"    and r.item_type != "STILL":  return False
            if fmt_f not in ("all formats", "") and r.format_ext != f".{fmt_f}":
                return False
            return True

        filtered = [r for r in self._all_records if matches(r)]

        # ── ソート ────────────────────────────────────────────────────────────
        if sort_k == "Name A→Z":
            filtered.sort(key=lambda r: r.display_name.lower())
        elif sort_k == "Name Z→A":
            filtered.sort(key=lambda r: r.display_name.lower(), reverse=True)
        elif sort_k == "Date (New)":
            filtered.sort(key=lambda r: r.mtime, reverse=True)
        elif sort_k == "Date (Old)":
            filtered.sort(key=lambda r: r.mtime)
        elif sort_k == "Type":
            filtered.sort(key=lambda r: (r.item_type, r.display_name.lower()))

        # ── グリッド再描画 ────────────────────────────────────────────────────
        self.asset_grid.clear()
        self.asset_items.clear()
        self.pending_thumbnail_keys.clear()

        vid = seq = still = 0
        for r in filtered:
            item = self.create_asset_item(r, scan_gen)
            self.asset_grid.addItem(item)
            self.asset_items[r.asset_key()] = item
            if r.item_type == "VIDEO":  vid   += 1
            elif r.item_type == "SEQ":  seq   += 1
            else:                       still += 1

        total = len(filtered)
        self.statusBar().showMessage(
            f"Assets: {total}  |  VIDEO: {vid}  |  SEQ: {seq}  |  STILL: {still}"
            + (f"  |  (filtered from {len(self._all_records)})"
               if total != len(self._all_records) else "")
        )

        if total > 0:
            self.asset_grid.setCurrentRow(0)
            self.info_label.setText(
                "Double-click to open  |  Drag to Nuke  |  Ctrl+Drag to copy before dragging"
            )
        else:
            self.info_label.setText(
                "No assets found." if self._all_records else
                "No supported files in this folder."
            )


    # ── item creation & thumbnails ────────────────────────────────────────────

    def create_asset_item(self, record: AssetRecord, generation: int) -> QListWidgetItem:
        if record.item_type == "SEQ":
            text = f"{record.display_name}\n🎞 {record.range_text}"
        else:
            text = f"{record.display_name}\n{record.item_type}"

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, record)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        item.setSizeHint(QSize(self.thumb_w + GRID_PAD_W, self.thumb_h + GRID_PAD_H))

        cache_path = self.get_thumb_cache_path(record)
        if cache_path.exists():
            item.setIcon(self.icon_from_image_path(cache_path, record.format_ext))
        else:
            item.setIcon(self.get_placeholder_icon(record))
            self.enqueue_thumbnail_job(record, generation)
        return item

    def get_thumb_cache_path(self, record: AssetRecord) -> Path:
        sig = self.build_cache_signature(record)
        h = hashlib.md5(sig.encode("utf-8")).hexdigest()
        return self.thumb_cache_dir / f"{h}.png"

    def build_cache_signature(self, record: AssetRecord) -> str:
        parts = [record.item_type, record.format_ext,
                 record.open_path or "", record.sequence_pattern or "", record.range_text]
        sources = []
        if record.item_type == "SEQ":
            if record.first_frame_path: sources.append(record.first_frame_path)
            if record.last_frame_path:  sources.append(record.last_frame_path)
            parts.append(str(record.frame_count or ""))
        else:
            if record.open_path: sources.append(record.open_path)
        for src in sources:
            parts.append(src)
            try:
                st = os.stat(src)
                parts += [str(st.st_size), str(st.st_mtime_ns)]
            except Exception:
                parts.append("missing")
        return "|".join(parts)

    def enqueue_thumbnail_job(self, record: AssetRecord, generation: int):
        key = record.asset_key()
        if key in self.pending_thumbnail_keys:
            return
        if self.get_thumb_cache_path(record).exists():
            return
        # EXR without OIIO — Qt fallback is still fine for non-EXR formats
        if record.item_type == "VIDEO" and not self.ffmpeg_path:
            return
        self.pending_thumbnail_keys.add(key)
        worker = ThumbnailWorker(
            asset_key=key, record=record, generation=generation,
            output_path=self.get_thumb_cache_path(record),
            ffmpeg_path=self.ffmpeg_path,
            thumb_w=self.thumb_w, thumb_h=self.thumb_h,
        )
        worker.signals.finished.connect(self.on_thumbnail_finished)
        worker.signals.failed.connect(self.on_thumbnail_failed)
        self.thread_pool.start(worker)

    def on_thumbnail_finished(self, asset_key: str, generation: int, thumb_path: str):
        if generation != self.scan_generation:
            return
        self.pending_thumbnail_keys.discard(asset_key)
        item = self.asset_items.get(asset_key)
        if item is None:
            return
        p = Path(thumb_path)
        if not p.exists():
            return
        record: AssetRecord | None = item.data(Qt.ItemDataRole.UserRole)
        fmt_ext = record.format_ext if record else ""
        item.setIcon(self.icon_from_image_path(p, fmt_ext))

    def on_thumbnail_failed(self, asset_key: str, generation: int):
        if generation == self.scan_generation:
            self.pending_thumbnail_keys.discard(asset_key)

    # ── icon / placeholder helpers ────────────────────────────────────────────

    @staticmethod
    def _badge_color(ext: str) -> QColor:
        rgb = FORMAT_BADGE_COLORS.get(ext.lower(), (100, 100, 100))
        return QColor(*rgb)

    @staticmethod
    def draw_format_badge(painter: QPainter, ext: str, canvas_w: int, canvas_h: int):
        label = ext.lstrip(".").upper()[:4]
        if not label:
            return
        color = QColor(*FORMAT_BADGE_COLORS.get(ext.lower(), (90, 90, 90)))
        bw, bh, margin = 36, 14, 4
        bx = canvas_w - bw - margin
        by = margin
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bx, by, bw, bh, 3, 3)
        painter.setPen(QColor(255, 255, 255))
        f = QFont()
        f.setBold(True)
        f.setPointSize(7)
        painter.setFont(f)
        painter.drawText(bx, by, bw, bh, Qt.AlignmentFlag.AlignCenter, label)

    def icon_from_image_path(self, image_path: Path, format_ext: str = "") -> QIcon:
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return self.get_placeholder_icon_generic("N/A", QColor(80, 80, 80))
        canvas = QPixmap(self.thumb_w, self.thumb_h)
        canvas.fill(QColor(24, 24, 24))
        scaled = pixmap.scaled(self.thumb_w, self.thumb_h,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        painter = QPainter(canvas)
        painter.drawPixmap((self.thumb_w - scaled.width()) // 2,
                           (self.thumb_h - scaled.height()) // 2, scaled)
        self.draw_format_badge(painter, format_ext, self.thumb_w, self.thumb_h)
        painter.end()
        return QIcon(canvas)

    def icon_from_qimage(self, image: QImage, format_ext: str = "") -> QIcon:
        canvas = QPixmap(self.thumb_w, self.thumb_h)
        canvas.fill(QColor(24, 24, 24))
        scaled = QPixmap.fromImage(image).scaled(
            self.thumb_w, self.thumb_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        painter = QPainter(canvas)
        painter.drawPixmap((self.thumb_w - scaled.width()) // 2,
                           (self.thumb_h - scaled.height()) // 2, scaled)
        self.draw_format_badge(painter, format_ext, self.thumb_w, self.thumb_h)
        painter.end()
        return QIcon(canvas)

    def get_placeholder_icon(self, record: AssetRecord) -> QIcon:
        if record.item_type == "VIDEO":
            accent = QColor(180, 60, 60)
        elif record.item_type == "SEQ":
            accent = QColor(100, 60, 190)
        else:
            accent = QColor(50, 120, 200)
        return self.get_placeholder_icon_generic(record.item_type, accent,
                                                 format_ext=record.format_ext)

    def get_placeholder_icon_generic(self, label: str, accent: QColor,
                                     loading: bool = True,
                                     format_ext: str = "") -> QIcon:
        key = (label, accent.rgb(), loading, format_ext, self.thumb_w, self.thumb_h)
        if key in self.placeholder_icons:
            return self.placeholder_icons[key]

        pixmap = QPixmap(self.thumb_w, self.thumb_h)
        pixmap.fill(QColor(28, 28, 28))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # border
        pen = QPen(QColor(60, 60, 60))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.thumb_w - 1, self.thumb_h - 1)

        # top accent bar
        painter.fillRect(0, 0, self.thumb_w, 22, accent)
        painter.setPen(QColor(245, 245, 245))
        f = QFont()
        f.setBold(True)
        f.setPointSize(8)
        painter.setFont(f)
        painter.drawText(8, 15, label)

        # body text
        painter.setPen(QColor(140, 140, 140))
        f2 = QFont()
        f2.setPointSize(9)
        painter.setFont(f2)
        body = "Loading…" if loading else "No Thumbnail"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, body)

        # format badge
        if format_ext:
            self.draw_format_badge(painter, format_ext, self.thumb_w, self.thumb_h)
        painter.end()

        icon = QIcon(pixmap)
        self.placeholder_icons[key] = icon
        return icon


    # ── preview system ────────────────────────────────────────────────────────

    def on_preview_mode_changed(self, _state):
        self.stop_overlay_preview()
        self.stop_inline_preview()

    def on_item_hovered(self, item: QListWidgetItem):
        if item is None:
            return
        record: AssetRecord | None = item.data(Qt.ItemDataRole.UserRole)
        if record is None:
            return
        if self.overlay_toggle.isChecked():
            self.stop_inline_preview()
            self.start_overlay_preview(record)
        else:
            if self.hovered_item is item:
                return
            self.stop_overlay_preview()
            self.start_inline_preview(item, record)

    # ── inline preview ────────────────────────────────────────────────────────

    def start_inline_preview(self, item: QListWidgetItem, record: AssetRecord):
        self.stop_inline_preview()
        self.hovered_item = item
        self.hover_original_icon = item.icon()
        self.hover_preview_paths = self.build_hover_preview_paths(record)
        self.hover_preview_index = 0
        if not self.hover_preview_paths:
            return
        self.apply_preview_to_item(self.hover_preview_paths[0], record.format_ext)
        if len(self.hover_preview_paths) > 1:
            self.hover_preview_timer.start()

    def stop_inline_preview(self):
        self.hover_preview_timer.stop()
        if self.hovered_item is not None and self.hover_original_icon is not None:
            self.hovered_item.setIcon(self.hover_original_icon)
        self.hovered_item = None
        self.hover_original_icon = None
        self.hover_preview_paths = []
        self.hover_preview_index = 0

    # ── overlay preview ───────────────────────────────────────────────────────

    def start_overlay_preview(self, record: AssetRecord):
        self.overlay_preview_paths = self.build_hover_preview_paths(record)
        self.overlay_preview_index = 0
        self.overlay_title_label.setText(f"{record.item_type}  ·  {record.display_name}")
        if not self.overlay_preview_paths:
            self.overlay_image_label.setText("Preview not available")
            self.overlay_image_label.setPixmap(QPixmap())
        else:
            self._show_overlay_frame(self.overlay_preview_paths[0])
            if len(self.overlay_preview_paths) > 1:
                self.hover_preview_timer.start()
        self.overlay_preview_widget.show()
        self.overlay_preview_widget.raise_()

    def stop_overlay_preview(self):
        self.hover_preview_timer.stop()
        self.overlay_preview_paths = []
        self.overlay_preview_index = 0
        self.overlay_preview_widget.hide()

    # ── shared advance tick ───────────────────────────────────────────────────

    def advance_inline_preview(self):
        if self.overlay_toggle.isChecked():
            if not self.overlay_preview_paths:
                self.hover_preview_timer.stop()
                return
            self.overlay_preview_index = (
                (self.overlay_preview_index + 1) % len(self.overlay_preview_paths)
            )
            self._show_overlay_frame(self.overlay_preview_paths[self.overlay_preview_index])
        else:
            if self.hovered_item is None or not self.hover_preview_paths:
                self.hover_preview_timer.stop()
                return
            self.hover_preview_index = (
                (self.hover_preview_index + 1) % len(self.hover_preview_paths)
            )
            record: AssetRecord | None = self.hovered_item.data(Qt.ItemDataRole.UserRole)
            fmt = record.format_ext if record else ""
            self.apply_preview_to_item(
                self.hover_preview_paths[self.hover_preview_index], fmt
            )

    def apply_preview_to_item(self, frame_path: str, format_ext: str = ""):
        if self.hovered_item is None:
            return
        image = self.load_preview_image(frame_path)
        if image is None or image.isNull():
            return
        self.hovered_item.setIcon(self.icon_from_qimage(image, format_ext))

    def _show_overlay_frame(self, frame_path: str):
        image = self.load_preview_image(frame_path)
        if image is None or image.isNull():
            self.overlay_image_label.setText("Preview not available")
            self.overlay_image_label.setPixmap(QPixmap())
            return
        pix = QPixmap.fromImage(image).scaled(
            self.overlay_image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.overlay_image_label.setText("")
        self.overlay_image_label.setPixmap(pix)

    def load_preview_image(self, path_text: str) -> QImage | None:
        if not path_text or not os.path.exists(path_text):
            return None
        ext = Path(path_text).suffix.lower()
        if ext == ".exr" and oiio is not None and np is not None:
            try:
                buf = oiio.ImageBuf(path_text)
                pixels = buf.get_pixels(oiio.FLOAT)
                if pixels is None:
                    return None
                img = oiio_pixels_to_qimage(np.asarray(pixels))
                if img is None or img.isNull():
                    return None
                return fit_qimage_to_canvas(img, self.thumb_w, self.thumb_h)
            except Exception:
                return None
        img = QImage(path_text)
        return None if img.isNull() else img

    # ── hover preview frame lists ─────────────────────────────────────────────

    def build_hover_preview_paths(self, record: AssetRecord) -> list[str]:
        if record.item_type == "VIDEO":
            return self.get_video_preview_frames(record)
        if record.item_type == "STILL":
            return [record.open_path] if record.open_path else []
        # SEQ
        cache_key = record.asset_key()
        if cache_key in self.sequence_file_cache:
            return self.sequence_file_cache[cache_key]

        # プロキシシーケンスを優先
        seq_pat = record.proxy_sequence_pattern or record.sequence_pattern
        folder  = Path(record.folder_path)
        if seq_pat and record.proxy_sequence_pattern:
            # proxy は別フォルダの可能性があるのでパターンから絶対パスを組み立て
            folder = Path(seq_pat).parent if os.path.isabs(seq_pat) else folder

        if not seq_pat:
            result = [record.first_frame_path] if record.first_frame_path else []
            self.sequence_file_cache[cache_key] = result
            return result

        m = re.match(r"^(.*)%0(\d+)d(\.[^.]+)$", Path(seq_pat).name)
        if not m:
            result = [record.first_frame_path] if record.first_frame_path else []
            self.sequence_file_cache[cache_key] = result
            return result

        base_name, pad_text, ext = m.groups()
        padding = int(pad_text)
        pat_re = re.compile(rf"^{re.escape(base_name)}(\d{{{padding}}}){re.escape(ext)}$")
        seq_folder = Path(seq_pat).parent if os.sep in seq_pat or "/" in seq_pat else folder

        frames: list[tuple[int, str]] = []
        try:
            for p in seq_folder.iterdir():
                if p.is_file():
                    hit = pat_re.match(p.name)
                    if hit:
                        frames.append((int(hit.group(1)), str(p)))
        except Exception:
            pass

        frames.sort(key=lambda x: x[0])
        paths = [p for _, p in frames]
        if len(paths) > 24:
            step = max(1, len(paths) // 24)
            paths = paths[::step]
        if not paths and record.first_frame_path:
            paths = [record.first_frame_path]

        self.sequence_file_cache[cache_key] = paths
        return paths

    def get_video_preview_frames(self, record: AssetRecord) -> list[str]:
        src = record.proxy_path or record.open_path
        if not src or not os.path.exists(src):
            return []
        key = record.asset_key()
        if key in self.video_preview_cache:
            return self.video_preview_cache[key]
        if not self.ffmpeg_path:
            return []
        folder = self.hover_cache_dir / hashlib.md5(key.encode()).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        existing = sorted(folder.glob("*.png"))
        if not existing:
            cmd = [
                self.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                "-i", src,
                "-vf", f"fps=6,scale={self.thumb_w * 2}:-1:flags=lanczos",
                "-frames:v", "18",
                str(folder / "frame_%03d.png"),
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            existing = sorted(folder.glob("*.png"))
        result = [str(p) for p in existing]
        self.video_preview_cache[key] = result
        return result


    # ── drag & drop ───────────────────────────────────────────────────────────

    def build_drag_payload(self, record: AssetRecord,
                           prefer_nuke_drop: bool = False
                           ) -> tuple[list[str], list[QUrl]]:
        texts: list[str] = []
        urls:  list[QUrl] = []

        if record.item_type == "SEQ":
            if record.sequence_pattern and record.folder_path:
                seq_path = str(Path(record.folder_path) / record.sequence_pattern)
                texts.append(seq_path)
            if prefer_nuke_drop:
                nk = self.build_nuke_read_drop_file(record)
                if nk and nk.exists():
                    return [str(nk)], [QUrl.fromLocalFile(str(nk))]
            if record.first_frame_path and os.path.exists(record.first_frame_path):
                urls.append(QUrl.fromLocalFile(record.first_frame_path))
            if not texts and record.first_frame_path:
                texts = [record.first_frame_path]
            return texts, urls

        if record.open_path:
            texts.append(record.open_path)
            if os.path.exists(record.open_path):
                urls.append(QUrl.fromLocalFile(record.open_path))
        return texts, urls

    def build_nuke_read_drop_file(self, record: AssetRecord) -> Path | None:
        if record.item_type != "SEQ":
            return None
        if not record.sequence_pattern or not record.folder_path:
            return None
        if record.frame_start is None or record.frame_end is None:
            return None
        seq_path = str(Path(record.folder_path) / record.sequence_pattern).replace("\\", "/")
        name_base = re.sub(r"[^A-Za-z0-9_]+", "_", record.display_name)[:40] or "Read"
        nk_text = (
            "Read {\n"
            f' file "{seq_path}"\n'
            f" first {record.frame_start}\n last {record.frame_end}\n"
            f" origfirst {record.frame_start}\n origlast {record.frame_end}\n"
            ' label "[value this.first]-[value this.last]\\n[expression last-first+1]"\n'
            f" name {name_base}\n"
            "}\n"
        )
        h = hashlib.md5(record.asset_key().encode()).hexdigest()
        nk_path = self.nuke_drop_dir / f"{h}.nk"
        try:
            nk_path.write_text(nk_text, encoding="utf-8")
            return nk_path
        except Exception:
            return None

    def handle_copy_drag(self, record: AssetRecord) -> tuple[list[str], list[QUrl]] | None:
        dlg = CopyDestinationDialog(record, self._copy_recent_dirs, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        if not dlg.do_copy:
            return self.build_drag_payload(record)

        dest_dir = Path(dlg.chosen_dir)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Cannot create destination:\n{e}")
            return None

        try:
            if record.item_type == "SEQ":
                copied_first = self._copy_sequence(record, dest_dir)
                if copied_first is None:
                    return None
                # copied payload: use new folder + same pattern
                new_seq_path = str(dest_dir / record.sequence_pattern) if record.sequence_pattern else copied_first
                texts = [new_seq_path]
                urls  = [QUrl.fromLocalFile(copied_first)]
            else:
                src = Path(record.open_path)
                dst = dest_dir / src.name
                shutil.copy2(str(src), str(dst))
                texts = [str(dst)]
                urls  = [QUrl.fromLocalFile(str(dst))]
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Copy failed:\n{e}")
            return None

        # 最近使ったコピー先を更新
        key = str(dest_dir)
        if key in self._copy_recent_dirs:
            self._copy_recent_dirs.remove(key)
        self._copy_recent_dirs.insert(0, key)
        self._copy_recent_dirs = self._copy_recent_dirs[:10]
        self.save_settings()

        return texts, urls

    def _copy_sequence(self, record: AssetRecord, dest_dir: Path) -> str | None:
        """SEQ の全フレームをコピーし、先頭フレームのパスを返す。"""
        if not record.folder_path or not record.sequence_pattern:
            return None
        seq_folder = Path(record.folder_path)
        m = re.match(r"^(.*)%0(\d+)d(\.[^.]+)$", record.sequence_pattern)
        if not m:
            return None
        base_name, pad_text, ext = m.groups()
        padding = int(pad_text)
        pat_re  = re.compile(rf"^{re.escape(base_name)}(\d{{{padding}}}){re.escape(ext)}$")

        frame_files = sorted(
            [p for p in seq_folder.iterdir() if p.is_file() and pat_re.match(p.name)],
            key=lambda p: p.name,
        )
        if not frame_files:
            return None

        progress = QProgressDialog(
            f"Copying {len(frame_files)} frames…", "Cancel", 0, len(frame_files), self
        )
        progress.setWindowTitle("Copying Sequence")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)

        first_dest: str | None = None
        for i, src in enumerate(frame_files):
            if progress.wasCanceled():
                break
            dst = dest_dir / src.name
            shutil.copy2(str(src), str(dst))
            if first_dest is None:
                first_dest = str(dst)
            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()
        return first_dest

    # ── selection info ────────────────────────────────────────────────────────

    def update_selection_info(self, current: QListWidgetItem, _previous):
        if current is None:
            return
        record: AssetRecord | None = current.data(Qt.ItemDataRole.UserRole)
        if record is None:
            return
        cache = self.get_thumb_cache_path(record)
        proxy_line = ""
        if record.proxy_path or record.proxy_first_frame_path:
            proxy_line = f"\nProxy: {record.proxy_path or record.proxy_first_frame_path}"

        if record.item_type == "SEQ":
            text = (
                f"Type: SEQ [{record.format_ext.upper().lstrip('.')}]  "
                f"Frames: {record.range_text}\n"
                f"Name: {record.display_name}\n"
                f"Folder: {record.folder_path}\n"
                f"Pattern: {record.sequence_pattern}"
                f"{proxy_line}\n"
                f"Cache: {cache}"
            )
        elif record.item_type == "VIDEO":
            text = (
                f"Type: VIDEO [{record.format_ext.upper().lstrip('.')}]\n"
                f"Name: {record.display_name}\n"
                f"Path: {record.open_path}"
                f"{proxy_line}\n"
                f"Cache: {cache}"
            )
        else:
            text = (
                f"Type: STILL [{record.format_ext.upper().lstrip('.')}]\n"
                f"Name: {record.display_name}\n"
                f"Path: {record.open_path}"
                f"{proxy_line}\n"
                f"Cache: {cache}"
            )
        self.info_label.setText(text)

    # ── context menus ─────────────────────────────────────────────────────────

    def show_folder_context_menu(self, pos):
        index = self.folder_tree.indexAt(pos)
        folder_path = (Path(self.folder_model.filePath(index))
                       if index.isValid()
                       else (self.current_folder or self.root_folder))
        if folder_path is None:
            return
        in_favs = str(folder_path) in self.favorite_paths
        menu = QMenu(self)
        open_act      = menu.addAction("Open in Explorer")
        add_fav_act   = menu.addAction("Add to Favorites")
        rem_fav_act   = menu.addAction("Remove from Favorites")
        rem_fav_act.setEnabled(in_favs)
        chosen = menu.exec(self.folder_tree.viewport().mapToGlobal(pos))
        if chosen is open_act:
            self.open_folder_in_explorer(folder_path)
        elif chosen is add_fav_act:
            if str(folder_path) not in self.favorite_paths:
                self.favorite_paths.append(str(folder_path))
                self.save_favorites()
        elif chosen is rem_fav_act:
            self.remove_favorite_path(str(folder_path))

    def show_asset_context_menu(self, pos):
        item = self.asset_grid.itemAt(pos)
        if item is None:
            return
        record: AssetRecord | None = item.data(Qt.ItemDataRole.UserRole)
        if record is None:
            return
        menu = QMenu(self)
        play_rv_act  = menu.addAction("▶  Play in RV")
        exr_view_act = None
        if record.format_ext == ".exr":
            exr_view_act = menu.addAction("🔍  Open in exrViewer")
        reveal_act   = menu.addAction("📂  Reveal in Explorer")
        copy_path_act = menu.addAction("📋  Copy Path")
        chosen = menu.exec(self.asset_grid.viewport().mapToGlobal(pos))
        if chosen is play_rv_act:
            self.launch_rv_for_record(record)
        elif exr_view_act and chosen is exr_view_act:
            self.launch_exrviewer_for_record(record)
        elif chosen is reveal_act:
            target = record.first_frame_path if record.item_type == "SEQ" else record.open_path
            self.reveal_in_explorer(target)
        elif chosen is copy_path_act:
            path_to_copy = (
                str(Path(record.folder_path) / record.sequence_pattern)
                if record.item_type == "SEQ" and record.sequence_pattern
                else record.open_path
            )
            QApplication.clipboard().setText(path_to_copy or "")


    # ── open / launch ─────────────────────────────────────────────────────────

    def open_selected_asset(self, item: QListWidgetItem):
        record: AssetRecord | None = item.data(Qt.ItemDataRole.UserRole)
        if record is None:
            return
        if record.item_type == "SEQ":
            self.reveal_in_explorer(record.first_frame_path)
        elif record.item_type == "VIDEO":
            self.launch_rv_for_record(record)
        else:
            if not record.open_path or not os.path.exists(record.open_path):
                QMessageBox.warning(self, "Open Asset", "File does not exist.")
                return
            try:
                os.startfile(record.open_path)
            except Exception as exc:
                QMessageBox.critical(self, "Open Asset", f"Failed to open:\n{exc}")

    def launch_rv_for_record(self, record: AssetRecord):
        rv_path = self._settings.get("rv_path", DEFAULT_RV_PATH)
        if not os.path.exists(rv_path):
            QMessageBox.warning(self, "RV", f"RV not found:\n{rv_path}")
            return

        target = record.open_path
        if record.item_type == "SEQ":
            if record.sequence_pattern and record.folder_path:
                target = str(Path(record.folder_path) / record.sequence_pattern)
            elif record.first_frame_path:
                target = record.first_frame_path

        if not target:
            QMessageBox.warning(self, "RV", "No media path available.")
            return
        # sequence patterns (%04d) are not real files — skip existence check for them
        if "%" not in target and not os.path.exists(target):
            QMessageBox.warning(self, "RV", f"File not found:\n{target}")
            return

        rv_dir  = str(Path(rv_path).parent)
        media   = os.path.normpath(target)

        # Try rvpush first (open in existing session)
        rv_dir_path = Path(rv_path).parent
        for candidate_name in ("rvpush.exe", "rvpush"):
            rvpush = rv_dir_path / candidate_name
            if not rvpush.exists():
                found = shutil.which(candidate_name)
                if found:
                    rvpush = Path(found)
            if rvpush.exists():
                try:
                    r = subprocess.run(
                        [str(rvpush), "set", media],
                        cwd=rv_dir, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, check=False,
                    )
                    if r.returncode in {0, 15}:
                        return
                except Exception:
                    pass

        # Fallback: direct launch
        try:
            subprocess.Popen(["cmd.exe", "/c", rv_path, "-reuse", media], cwd=rv_dir)
        except Exception as exc:
            QMessageBox.critical(self, "RV", f"Failed to launch RV:\n{exc}")

    def launch_exrviewer_for_record(self, record: AssetRecord):
        ev_path = self._settings.get("exr_viewer_path", DEFAULT_EXR_VIEWER_PATH)
        if not os.path.exists(ev_path):
            QMessageBox.warning(self, "exrViewer", f"exrViewer not found:\n{ev_path}")
            return
        target = record.first_frame_path if record.item_type == "SEQ" else record.open_path
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "exrViewer", "EXR file not found.")
            return
        try:
            tmp_dir = self.cache_root / "exrviewer_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["TMP"] = env["TEMP"] = str(tmp_dir)
            subprocess.Popen(
                [ev_path, os.path.normpath(target)],
                cwd=str(Path(ev_path).parent), env=env,
            )
        except Exception as exc:
            QMessageBox.critical(self, "exrViewer", f"Failed to launch:\n{exc}")

    def reveal_in_explorer(self, file_path: str | None):
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Reveal", "File does not exist.")
            return
        try:
            subprocess.run(
                ["explorer", "/select,", os.path.normpath(file_path)], check=False
            )
        except Exception as exc:
            QMessageBox.critical(self, "Reveal", f"Failed:\n{exc}")

    def open_folder_in_explorer(self, folder_path: Path):
        if not folder_path.exists():
            QMessageBox.warning(self, "Open Folder", "Folder does not exist.")
            return
        try:
            subprocess.run(["explorer", os.path.normpath(str(folder_path))], check=False)
        except Exception as exc:
            QMessageBox.critical(self, "Open Folder", f"Failed:\n{exc}")

    # ── info dialog ───────────────────────────────────────────────────────────

    def show_info_dialog(self):
        ffmpeg_text = f"ffmpeg: {self.ffmpeg_path}" if self.ffmpeg_path else "ffmpeg: not found"
        oiio_text   = ("OpenImageIO: available" if oiio is not None and np is not None
                       else "OpenImageIO: not available")
        QMessageBox.information(
            self, "Info",
            "\n".join([
                f"Root: {self.root_folder}",
                f"Cache: {self.cache_root}",
                ffmpeg_text, oiio_text,
                f"Threads: {self.thread_pool.maxThreadCount()}",
            ]),
        )

    # ── event filter ─────────────────────────────────────────────────────────

    def eventFilter(self, watched, event):
        vp = self.asset_grid.viewport()
        if watched is vp:
            if (event.type() == QEvent.Type.Leave
                    and not self.overlay_toggle.isChecked()):
                self.stop_inline_preview()
            elif (event.type() == QEvent.Type.MouseButtonPress
                  and self.overlay_toggle.isChecked()):
                if self.asset_grid.itemAt(event.position().toPoint()) is None:
                    self.stop_overlay_preview()
        elif (self.overlay_preview_widget.isVisible()
              and event.type() == QEvent.Type.MouseButtonPress):
            w = watched
            if (isinstance(w, QWidget)
                    and w is not vp
                    and not self.overlay_preview_widget.isAncestorOf(w)):
                self.stop_overlay_preview()
        return super().eventFilter(watched, event)

    # ── static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def safe_relative_text(path: Path, base: Path) -> str:
        try:
            return str(path.relative_to(base))
        except ValueError:
            return str(path)

    @staticmethod
    def find_ffmpeg() -> str | None:
        local = Path(__file__).resolve().parent / "ffmpeg" / "ffmpeg.exe"
        if local.exists():
            return str(local)
        return shutil.which("ffmpeg")


# ── SECTION 10: ENTRY POINT ──────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
