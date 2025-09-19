
# ui_panels.py
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QSpinBox, QColorDialog, QLineEdit, QCheckBox, QSlider, QGroupBox,
    QScrollArea, QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt5.QtGui import QColor, QPixmap, QImage
from PyQt5.QtCore import Qt, QSize, pyqtSignal

from text_box import TextBox # 导入TextBox类
from utils import pil_to_qimage, qimage_to_pil, get_font_path # 导入辅助函数
from PIL import Image # Pillow库

class TextPropertiesPanel(QWidget):
    # 定义信号，当格式被应用时发出
    apply_format_to_selection = pyqtSignal(dict)

    def __init__(self, system_fonts, parent=None):
        super().__init__(parent)
        self.system_fonts = system_fonts
        self._init_ui()
        self.current_text_box = None # 当前正在编辑的文本框

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop) # 顶部对齐

        # --- 文本内容 ---
        text_group = self._create_collapsible_group("文本内容")
        text_layout = QVBoxLayout(text_group)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("在此输入文本")
        self.text_input.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self.text_input)
        main_layout.addWidget(text_group)

        # --- 字体设置 ---
        font_group = self._create_collapsible_group("字体设置")
        font_layout = QVBoxLayout(font_group)

        font_name_layout = QHBoxLayout()
        font_name_layout.addWidget(QLabel("字体:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(sorted(self.system_fonts))
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        font_name_layout.addWidget(self.font_combo)
        font_layout.addLayout(font_name_layout)

        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(16)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        font_size_layout.addWidget(self.font_size_spin)
        font_layout.addLayout(font_size_layout)

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        self.color_button = QPushButton("选择颜色")
        self.color_button.clicked.connect(self._select_text_color)
        self.current_text_color = QColor(0, 0, 0) # 默认黑色
        self._update_color_button_style(self.color_button, self.current_text_color)
        color_layout.addWidget(self.color_button)
        font_layout.addLayout(color_layout)

        main_layout.addWidget(font_group)

        # --- 描边设置 ---
        stroke_group = self._create_collapsible_group("描边设置")
        stroke_layout = QVBoxLayout(stroke_group)

        stroke_width_layout = QHBoxLayout()
        stroke_width_layout.addWidget(QLabel("宽度:"))
        self.stroke_width_spin = QSpinBox()
        self.stroke_width_spin.setRange(0, 20)
        self.stroke_width_spin.setValue(0)
        self.stroke_width_spin.valueChanged.connect(self._on_stroke_width_changed)
        stroke_width_layout.addWidget(self.stroke_width_spin)
        stroke_layout.addLayout(stroke_width_layout)

        stroke_color_layout = QHBoxLayout()
        stroke_color_layout.addWidget(QLabel("颜色:"))
        self.stroke_color_button = QPushButton("选择颜色")
        self.stroke_color_button.clicked.connect(self._select_stroke_color)
        self.current_stroke_color = QColor(0, 0, 0) # 默认黑色
        self._update_color_button_style(self.stroke_color_button, self.current_stroke_color)
        stroke_color_layout.addWidget(self.stroke_color_button)
        stroke_layout.addLayout(stroke_color_layout)

        main_layout.addWidget(stroke_group)

        # --- 阴影设置 ---
        shadow_group = self._create_collapsible_group("阴影设置")
        shadow_layout = QVBoxLayout(shadow_group)

        shadow_offset_x_layout = QHBoxLayout()
        shadow_offset_x_layout.addWidget(QLabel("X偏移:"))
        self.shadow_offset_x_spin = QSpinBox()
        self.shadow_offset_x_spin.setRange(-50, 50)
        self.shadow_offset_x_spin.setValue(0)
        self.shadow_offset_x_spin.valueChanged.connect(self._on_shadow_offset_changed)
        shadow_offset_x_layout.addWidget(self.shadow_offset_x_spin)
        shadow_layout.addLayout(shadow_offset_x_layout)

        shadow_offset_y_layout = QHBoxLayout()
        shadow_offset_y_layout.addWidget(QLabel("Y偏移:"))
        self.shadow_offset_y_spin = QSpinBox()
        self.shadow_offset_y_spin.setRange(-50, 50)
        self.shadow_offset_y_spin.setValue(0)
        self.shadow_offset_y_spin.valueChanged.connect(self._on_shadow_offset_changed)
        shadow_offset_y_layout.addWidget(self.shadow_offset_y_spin)
        shadow_layout.addLayout(shadow_offset_y_layout)

        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(QLabel("颜色:"))
        self.shadow_color_button = QPushButton("选择颜色")
        self.shadow_color_button.clicked.connect(self._select_shadow_color)
        self.current_shadow_color = QColor(0, 0, 0, 128) # 默认半透明黑色
        self._update_color_button_style(self.shadow_color_button, self.current_shadow_color)
        shadow_color_layout.addWidget(self.shadow_color_button)
        shadow_layout.addLayout(shadow_color_layout)

        main_layout.addWidget(shadow_group)

        # --- 排版和高级设置 ---
        layout_group = self._create_collapsible_group("排版与高级")
        layout_layout = QVBoxLayout(layout_group)

        self.is_vertical_checkbox = QCheckBox("竖排文本")
        self.is_vertical_checkbox.stateChanged.connect(self._on_is_vertical_changed)
        layout_layout.addWidget(self.is_vertical_checkbox)

        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("旋转角度:"))
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(0, 359)
        self.rotation_spin.setValue(0)
        self.rotation_spin.valueChanged.connect(self._on_rotation_changed)
        rotation_layout.addWidget(self.rotation_spin)
        layout_layout.addLayout(rotation_layout)

        h_scale_layout = QHBoxLayout()
        h_scale_layout.addWidget(QLabel("水平缩放:"))
        self.h_scale_spin = QSpinBox()
        self.h_scale_spin.setRange(10, 200)
        self.h_scale_spin.setValue(100)
        self.h_scale_spin.setSuffix("%")
        self.h_scale_spin.valueChanged.connect(self._on_scale_changed)
        h_scale_layout.addWidget(self.h_scale_spin)
        layout_layout.addLayout(h_scale_layout)

        v_scale_layout = QHBoxLayout()
        v_scale_layout.addWidget(QLabel("垂直缩放:"))
        self.v_scale_spin = QSpinBox()
        self.v_scale_spin.setRange(10, 200)
        self.v_scale_spin.setValue(100)
        self.v_scale_spin.setSuffix("%")
        self.v_scale_spin.valueChanged.connect(self._on_scale_changed)
        v_scale_layout.addWidget(self.v_scale_spin)
        layout_layout.addLayout(v_scale_layout)

        line_spacing_layout = QHBoxLayout()
        line_spacing_layout.addWidget(QLabel("行间距:"))
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(50, 200)
        self.line_spacing_spin.setValue(100)
        self.line_spacing_spin.setSuffix("%")
        self.line_spacing_spin.valueChanged.connect(self._on_line_spacing_changed)
        line_spacing_layout.addWidget(self.line_spacing_spin)
        layout_layout.addLayout(line_spacing_layout)

        char_spacing_layout = QHBoxLayout()
        char_spacing_layout.addWidget(QLabel("字间距:"))
        self.char_spacing_spin = QSpinBox()
        self.char_spacing_spin.setRange(-10, 50)
        self.char_spacing_spin.setValue(0)
        self.char_spacing_spin.valueChanged.connect(self._on_char_spacing_changed)
        char_spacing_layout.addWidget(self.char_spacing_spin)
        layout_layout.addLayout(char_spacing_layout)

        main_layout.addWidget(layout_group)

        # 添加一个弹簧，将所有内容推到顶部
        main_layout.addStretch(1)

    def _create_collapsible_group(self, title):
        """创建可折叠的QGroupBox"""
        group_box = QGroupBox(title)
        group_box.setCheckable(True) # 使其可折叠
        group_box.setChecked(True) # 默认展开
        group_box.setStyleSheet("QGroupBox::indicator { width: 10px; height: 10px; }") # 调整指示器大小
        return group_box

    def _update_color_button_style(self, button, color):
        """更新颜色按钮的背景色以显示当前颜色"""
        button.setStyleSheet(f"background-color: {color.name()};")

    def load_text_box_properties(self, text_box: TextBox):
        """加载选中文本框的属性到面板"""
        self.current_text_box = text_box
        # 暂时断开信号，避免循环触发
        self._disconnect_signals()

        self.text_input.setText(text_box.text)
        self.font_combo.setCurrentText(text_box.font_name)
        self.font_size_spin.setValue(text_box.font_size)
        self.current_text_color = QColor.fromRgbF(*text_box.color)
        self._update_color_button_style(self.color_button, self.current_text_color)

        self.stroke_width_spin.setValue(text_box.stroke_width)
        self.current_stroke_color = QColor.fromRgbF(*text_box.stroke_color)
        self._update_color_button_style(self.stroke_color_button, self.current_stroke_color)

        self.shadow_offset_x_spin.setValue(text_box.shadow_offset[0])
        self.shadow_offset_y_spin.setValue(text_box.shadow_offset[1])
        self.current_shadow_color = QColor.fromRgbF(*text_box.shadow_color)
        self._update_color_button_style(self.shadow_color_button, self.current_shadow_color)

        self.is_vertical_checkbox.setChecked(text_box.is_vertical)
        self.rotation_spin.setValue(int(text_box.rotation))
        self.h_scale_spin.setValue(int(text_box.h_scale * 100))
        self.v_scale_spin.setValue(int(text_box.v_scale * 100))
        self.line_spacing_spin.setValue(int(text_box.line_spacing * 100))
        self.char_spacing_spin.setValue(int(text_box.char_spacing))

        # 重新连接信号
        self._connect_signals()

    def clear_properties(self):
        """清空属性面板，当没有文本框被选中时调用"""
        self.current_text_box = None
        self._disconnect_signals()
        self.text_input.setText("")
        # 重置其他控件到默认值或禁用
        self.font_combo.setCurrentIndex(0)
        self.font_size_spin.setValue(16)
        self._update_color_button_style(self.color_button, QColor(0,0,0))
        self.stroke_width_spin.setValue(0)
        self._update_color_button_style(self.stroke_color_button, QColor(0,0,0))
        self.shadow_offset_x_spin.setValue(0)
        self.shadow_offset_y_spin.setValue(0)
        self._update_color_button_style(self.shadow_color_button, QColor(0,0,0,128))
        self.is_vertical_checkbox.setChecked(False)
        self.rotation_spin.setValue(0)
        self.h_scale_spin.setValue(100)
        self.v_scale_spin.setValue(100)
        self.line_spacing_spin.setValue(100)
        self.char_spacing_spin.setValue(0)
        self._connect_signals()

    def _disconnect_signals(self):
        """断开所有控件的信号连接"""
        self.text_input.textChanged.disconnect(self._on_text_changed)
        self.font_combo.currentTextChanged.disconnect(self._on_font_changed)
        self.font_size_spin.valueChanged.disconnect(self._on_font_size_changed)
        self.stroke_width_spin.valueChanged.disconnect(self._on_stroke_width_changed)
        self.shadow_offset_x_spin.valueChanged.disconnect(self._on_shadow_offset_changed)
        self.shadow_offset_y_spin.valueChanged.disconnect(self._on_shadow_offset_changed)
        self.is_vertical_checkbox.stateChanged.disconnect(self._on_is_vertical_changed)
        self.rotation_spin.valueChanged.disconnect(self._on_rotation_changed)
        self.h_scale_spin.valueChanged.disconnect(self._on_scale_changed)
        self.v_scale_spin.valueChanged.disconnect(self._on_scale_changed)
        self.line_spacing_spin.valueChanged.disconnect(self._on_line_spacing_changed)
        self.char_spacing_spin.valueChanged.disconnect(self._on_char_spacing_changed)

    def _connect_signals(self):
        """重新连接所有控件的信号"""
        self.text_input.textChanged.connect(self._on_text_changed)
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        self.stroke_width_spin.valueChanged.connect(self._on_stroke_width_changed)
        self.shadow_offset_x_spin.valueChanged.connect(self._on_shadow_offset_changed)
        self.shadow_offset_y_spin.valueChanged.connect(self._on_shadow_offset_changed)
        self.is_vertical_checkbox.stateChanged.connect(self._on_is_vertical_changed)
        self.rotation_spin.valueChanged.connect(self._on_rotation_changed)
        self.h_scale_spin.valueChanged.connect(self._on_scale_changed)
        self.v_scale_spin.valueChanged.connect(self._on_scale_changed)
        self.line_spacing_spin.valueChanged.connect(self._on_line_spacing_changed)
        self.char_spacing_spin.valueChanged.connect(self._on_char_spacing_changed)

    def _get_current_format_data(self):
        """获取当前面板上的所有格式设置"""
        return {
            "text": self.text_input.text(),
            "font_name": self.font_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "color": self.current_text_color.getRgbF(),
            "stroke_width": self.stroke_width_spin.value(),
            "stroke_color": self.current_stroke_color.getRgbF(),
            "shadow_offset": (self.shadow_offset_x_spin.value(), self.shadow_offset_y_spin.value()),
            "shadow_color": self.current_shadow_color.getRgbF(),
            "h_scale": self.h_scale_spin.value() / 100.0,
            "v_scale": self.v_scale_spin.value() / 100.0,
            "line_spacing": self.line_spacing_spin.value() / 100.0,
            "char_spacing": self.char_spacing_spin.value(),
            "is_vertical": self.is_vertical_checkbox.isChecked(),
            "rotation": self.rotation_spin.value()
        }

    # --- 信号槽函数，更新文本框属性并触发重绘 ---
    def _on_text_changed(self, text):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_font_changed(self, font_name):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_font_size_changed(self, size):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _select_text_color(self):
        color = QColorDialog.getColor(self.current_text_color, self, "选择文本颜色")
        if color.isValid():
            self.current_text_color = color
            self._update_color_button_style(self.color_button, color)
            self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_stroke_width_changed(self, width):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _select_stroke_color(self):
        color = QColorDialog.getColor(self.current_stroke_color, self, "选择描边颜色")
        if color.isValid():
            self.current_stroke_color = color
            self._update_color_button_style(self.stroke_color_button, color)
            self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_shadow_offset_changed(self, value):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _select_shadow_color(self):
        color = QColorDialog.getColor(self.current_shadow_color, self, "选择阴影颜色")
        if color.isValid():
            self.current_shadow_color = color
            self._update_color_button_style(self.shadow_color_button, color)
            self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_is_vertical_changed(self, state):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_rotation_changed(self, angle):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_scale_changed(self, value):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_line_spacing_changed(self, value):
        self.apply_format_to_selection.emit(self._get_current_format_data())

    def _on_char_spacing_changed(self, value):
        self.apply_format_to_selection.emit(self._get_current_format_data())


class ThumbnailPanel(QWidget):
    thumbnail_clicked = pyqtSignal(int) # 发送点击的索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_paths = []
        self.current_selected_index = -1

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # 禁用水平滚动条

        self.list_widget = QListWidget()
        self.list_widget.setFlow(QListWidget.TopToBottom) # 垂直排列
        self.list_widget.setSpacing(5) # 缩略图间距
        self.list_widget.setIconSize(QSize(120, 90)) # 缩略图大小
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setStyleSheet("""
            QListWidget::item:selected {
                border: 2px solid #007bff; /* 选中边框 */
                background-color: #e0f0ff; /* 选中背景 */
            }
            QListWidget::item {
                padding: 5px; /* 内部填充 */
            }
        """)

        self.scroll_area.setWidget(self.list_widget)
        main_layout.addWidget(self.scroll_area)

    def load_thumbnails(self, image_paths):
        """加载图片路径并创建缩略图列表项"""
        self.image_paths = image_paths
        self.list_widget.clear()

        for i, path in enumerate(image_paths):
            item = QListWidgetItem()
            item.setText(f"第 {i+1} 页")
            item.setData(Qt.UserRole, path) # 存储原始路径
            item.setSizeHint(QSize(140, 100)) # 列表项大小
            self.list_widget.addItem(item)

            # 异步加载缩略图以避免UI阻塞
            self._load_thumbnail_async(item, path)

    def _load_thumbnail_async(self, item, path):
        """异步加载单个缩略图"""
        # 这是一个简化的异步加载，实际应用中可能需要线程池
        # 这里只是延迟加载，模拟"点击后加载"
        # 真正的异步加载需要QThreadPool或QThread
        # 为了演示目的，我们只在需要时生成缩略图，而不是预先加载所有
        # 这里的thumbnail_path只是一个占位符，实际在_on_item_clicked中加载完整图片
        pixmap = QPixmap(self.list_widget.iconSize())
        pixmap.fill(Qt.lightGray) # 占位符
        item.setIcon(QPixmap(pixmap))


    def _on_item_clicked(self, item):
        """处理缩略图点击事件"""
        index = self.list_widget.row(item)
        self.thumbnail_clicked.emit(index)

    def set_current_selected(self, index):
        """设置当前选中的缩略图"""
        if 0 <= index < self.list_widget.count():
            self.list_widget.setCurrentRow(index)
            self.current_selected_index = index

            # 确保选中项可见
            self.list_widget.scrollToItem(self.list_widget.item(index), QListWidget.EnsureVisible)

            # 实际加载缩略图并更新图标
            item = self.list_widget.item(index)
            image_path = item.data(Qt.UserRole)
            try:
                # 使用Pillow加载并生成缩略图
                img = Image.open(image_path).convert("RGB")
                img.thumbnail((self.list_widget.iconSize().width(), self.list_widget.iconSize().height()), Image.LANCZOS)
                qimage = pil_to_qimage(img)
                item.setIcon(QPixmap.fromImage(qimage))
            except Exception as e:
                print(f"加载缩略图失败: {e}")
                item.setIcon(QPixmap()) # 清除图标
```python
# history_manager.py
import copy

class HistoryManager:
    def __init__(self):
        self.history = []
        self.current_state_index = -1

    def save_state(self, state):
        """保存当前状态到历史记录"""
        # 移除当前索引之后的所有“未来”状态（如果进行了撤销后又进行了新操作）
        if self.current_state_index < len(self.history) - 1:
            self.history = self.history[:self.current_state_index + 1]
        
        # 深度拷贝状态，确保修改不会影响历史记录
        self.history.append(copy.deepcopy(state))
        self.current_state_index = len(self.history) - 1
        # print(f"状态已保存。当前历史记录长度: {len(self.history)}, 索引: {self.current_state_index}")

    def undo(self):
        """撤销到上一个状态"""
        if self.current_state_index > 0:
            self.current_state_index -= 1
            # print(f"执行撤销。新索引: {self.current_state_index}")
            return copy.deepcopy(self.history[self.current_state_index])
        # print("无法撤销，已是最初状态。")
        return None

    def redo(self):
        """重做到下一个状态"""
        if self.current_state_index < len(self.history) - 1:
            self.current_state_index += 1
            # print(f"执行重做。新索引: {self.current_state_index}")
            return copy.deepcopy(self.history[self.current_state_index])
        # print("无法重做，已是最新状态。")
        return None

    def clear(self):
        """清空所有历史记录"""
        self.history = []
        self.current_state_index = -1
        # print("历史记录已清空。")

```python
# utils.py
import os
import glob
import shutil
import platform
from PyQt5.QtGui import QImage, QPixmap
from PIL import Image, ImageDraw, ImageFont
import cairo

def get_system_fonts():
    """获取系统可用字体列表"""
    fonts = set()
    if platform.system() == "Windows":
        font_dirs = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft\\Windows\\Fonts")
        ]
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for font_file in glob.glob(os.path.join(font_dir, "*.ttf")):
                    try:
                        # Pillow可以用来读取字体名称
                        font = ImageFont.truetype(font_file, 10) # 随便一个大小
                        fonts.add(font.font_variant) # 获取字体名称
                    except Exception:
                        pass
                for font_file in glob.glob(os.path.join(font_dir, "*.ttc")):
                    try:
                        # 对于.ttc文件，可能包含多个字体
                        # Pillow的ImageFont.truetype可以接受index参数
                        # 但这里简单起见，只尝试加载，如果成功就添加文件名
                        font = ImageFont.truetype(font_file, 10)
                        fonts.add(font.font_variant)
                    except Exception:
                        pass
    elif platform.system() == "Darwin": # macOS
        font_dirs = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts")
        ]
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for font_file in glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf")):
                    try:
                        font = ImageFont.truetype(font_file, 10)
                        fonts.add(font.font_variant)
                    except Exception:
                        pass
    else: # Linux
        font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.local/share/fonts")
        ]
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for font_file in glob.glob(os.path.join(font_dir, "**/*.ttf"), recursive=True) + \
                                 glob.glob(os.path.join(font_dir, "**/*.otf"), recursive=True):
                    try:
                        font = ImageFont.truetype(font_file, 10)
                        fonts.add(font.font_variant)
                    except Exception:
                        pass
    # 确保至少有一些通用字体
    if not fonts:
        fonts.add("Arial")
        fonts.add("SimHei")
        fonts.add("Times New Roman")
    return sorted(list(fonts))

# 缓存字体路径，避免重复查找
_font_path_cache = {}

def get_font_path(font_name):
    """根据字体名称获取字体文件路径，用于PyCairo"""
    if font_name in _font_path_cache:
        return _font_path_cache[font_name]

    # 这是一个简化的查找，实际可能需要更复杂的字体匹配逻辑
    # PyCairo通常能直接通过字体名称找到系统字体，但如果需要精确路径，则需要查找
    # 暂时返回None，让PyCairo尝试自行查找
    # 如果PyCairo无法找到，可以考虑在这里实现更复杂的字体文件查找逻辑
    # 例如：遍历get_system_fonts()找到的字体文件，并用Pillow验证其名称
    
    # 示例：如果需要精确路径，可以这样尝试查找
    # for font_dir in ["C:\\Windows\\Fonts", "/System/Library/Fonts", "/Library/Fonts", "/usr/share/fonts", os.path.expanduser("~/Library/Fonts"), os.path.expanduser("~/.local/share/fonts")]:
    #     if os.path.exists(font_dir):
    #         for ext in ["ttf", "otf", "ttc"]:
    #             font_file = os.path.join(font_dir, f"{font_name}.{ext}")
    #             if os.path.exists(font_file):
    #                 _font_path_cache[font_name] = font_file
    #                 return font_file
    #             # 尝试不区分大小写
    #             font_file = os.path.join(font_dir, f"{font_name.lower()}.{ext}")
    #             if os.path.exists(font_file):
    #                 _font_path_cache[font_name] = font_file
    #                 return font_file
    #             # 尝试模糊匹配
    #             for f in glob.glob(os.path.join(font_dir, f"*.{ext}")):
    #                 try:
    #                     pil_font = ImageFont.truetype(f, 10)
    #                     if font_name.lower() in pil_font.font_variant.lower():
    #                         _font_path_cache[font_name] = f
    #                         return f
    #                 except Exception:
    #                     pass
    
    return None # PyCairo通常能直接通过名称找到，无需精确路径

def load_image_paths(folder_path):
    """加载文件夹中所有支持的图片文件路径"""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
    image_paths = []
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(folder_path, ext)))
    image_paths.sort() # 按文件名排序
    return image_paths

def create_required_dirs(base_dir):
    """创建inpaint和qianresult文件夹"""
    inpaint_dir = os.path.join(base_dir, "inpaint")
    qianresult_dir = os.path.join(base_dir, "qianresult")

    os.makedirs(inpaint_dir, exist_ok=True)
    os.makedirs(qianresult_dir, exist_ok=True)
    return inpaint_dir, qianresult_dir

def pil_to_qimage(pil_image: Image.Image):
    """将PIL Image转换为QImage"""
    if pil_image.mode == "RGB":
        return QImage(pil_image.tobytes("raw", "RGB"), pil_image.width, pil_image.height, QImage.Format_RGB888)
    elif pil_image.mode == "RGBA":
        return QImage(pil_image.tobytes("raw", "RGBA"), pil_image.width, pil_image.height, QImage.Format_ARGB32)
    else:
        # 转换为RGB或RGBA以兼容
        return QImage(pil_image.convert("RGBA").tobytes("raw", "RGBA"), pil_image.width, pil_image.height, QImage.Format_ARGB32)

def qimage_to_pil(q_image: QImage):
    """将QImage转换为PIL Image"""
    buffer = q_image.constBits()
    # 根据QImage的格式选择PIL的模式
    if q_image.format() == QImage.Format_RGB888:
        return Image.frombuffer("RGB", (q_image.width(), q_image.height()), buffer, "raw", "RGB", 0, 1)
    elif q_image.format() == QImage.Format_ARGB32:
        return Image.frombuffer("RGBA", (q_image.width(), q_image.height()), buffer, "raw", "BGRA", 0, 1)
    elif q_image.format() == QImage.Format_ARGB32_Premultiplied:
        # Cairo通常使用这个格式，需要特殊处理
        return Image.frombuffer("RGBA", (q_image.width(), q_image.height()), buffer, "raw", "RGBA", 0, 1).transpose(Image.FLIP_TOP_BOTTOM)
    else:
        # 转换为RGBA以兼容
        return Image.frombuffer("RGBA", (q_image.convertToFormat(QImage.Format_ARGB32).width(), q_image.convertToFormat(QImage.Format_ARGB32).height()), q_image.convertToFormat(QImage.Format_ARGB32).constBits(), "raw", "BGRA", 0, 1)

def save_image_with_text(image_path, text_boxes, output_path):
    """
    加载图片，绘制文本框，然后保存。
    这个函数现在由 ImageCanvas.save_rendered_image 替代，
    但保留作为通用工具函数示例。
    """
    try:
        # 使用Pillow加载图片
        img = Image.open(image_path).convert("RGBA") # 确保有alpha通道

        # 创建一个与PIL Image兼容的Cairo表面
        # PyCairo需要一个可写的缓冲区，因此我们直接从PIL图像的像素数据创建
        surface = cairo.ImageSurface.create_for_data(
            bytearray(img.tobytes()),
            cairo.FORMAT_ARGB32, # PIL的RGBA通常对应Cairo的ARGB32
            img.width,
            img.height,
            img.width * 4 # 4 bytes per pixel (RGBA)
        )
        ctx = cairo.Context(surface)

        # 绘制所有文本框
        for tb in text_boxes:
            tb.draw(ctx, draw_handles=False) # 保存时不要绘制句柄

        # 将Cairo表面数据转换回PIL Image
        # Cairo的ARGB32是BGRA顺序，PIL的RGBA是RGBA顺序，可能需要转换
        buf = surface.get_data()
        final_pil_img = Image.frombuffer(
            "RGBA", (img.width, img.height), buf, "raw", "ARGB", 0, 1
        )
        final_pil_img.save(output_path)
        print(f"图片已保存到: {output_path}")
    except Exception as e:
        print(f"保存图片失败: {e}")

