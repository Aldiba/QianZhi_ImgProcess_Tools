import sys
import os
import json
import uuid
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QScrollArea, QSizePolicy,
    QTextEdit, QComboBox, QSpinBox, QSlider, QColorDialog, QMessageBox,
    QFrame, QGroupBox, QListWidget, QLineEdit, QDoubleSpinBox, 
    QListWidgetItem, QMenu, QTabWidget, QToolBar 
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase,
    QMouseEvent, QWheelEvent, QTransform, QIcon, QPen, QPainterPath
)
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QPointF 

from PIL import Image, ImageQt # Pillow is still used for image file I/O

# --- Global Constants and Configurations ---
INPAINT_FOLDER = "inpainted"
QIANRESULT_FOLDER = "qianresult"
PRESET_FILE = "text_presets.json"
PAGE_DATA_FILE = "page_data.json"
# Changed default font to a common Chinese font for better compatibility
DEFAULT_FONT = "Microsoft YaHei UI" 
DEFAULT_FONT_SIZE = 24
DEFAULT_TEXT_COLOR = "#000000"
THUMBNAIL_SIZE = QSize(80, 120) # QSize for PySide6

# --- Helper Functions ---
def get_image_files(folder_path):
    """Get paths of all supported image files in the folder, sorted by filename"""
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
    return sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(image_extensions) and os.path.isfile(os.path.join(folder_path, f))
    ])

# --- TextBox Class ---
class TextBox:
    """Represents an editable text box"""
    def __init__(self, x, y, text="", font_family=DEFAULT_FONT, font_size=DEFAULT_FONT_SIZE, 
                 color=DEFAULT_TEXT_COLOR, is_vertical=False, stroke_width=0, 
                 stroke_color="#FFFFFF", shadow_offset_x=0, shadow_offset_y=0, 
                 shadow_color="#000000", line_spacing=0, rotation=0.0, scale_x=1.0, scale_y=1.0):
        self.id = str(uuid.uuid4())
        self.x = x
        self.y = y
        self.text = text
        self.font_family = font_family
        self.font_size = font_size
        self.color = QColor(color)
        self.is_vertical = is_vertical
        self.stroke_width = stroke_width
        self.stroke_color = QColor(stroke_color)
        self.shadow_offset_x = shadow_offset_x
        self.shadow_offset_y = shadow_offset_y
        self.shadow_color = QColor(shadow_color)
        self.line_spacing = line_spacing
        self.rotation = rotation # Rotation angle (degrees)
        self.scale_x = scale_x # Horizontal scale
        self.scale_y = scale_y # Vertical scale

        self.width = 0
        self.height = 0

    def get_qfont(self):
        """Get PySide6 QFont object"""
        font = QFont(self.font_family, self.font_size)
        return font

    def calculate_bbox(self, painter):
        """Calculate the bounding box of the text box (in original image coordinates)"""
        font = self.get_qfont()
        painter.setFont(font) # Set font for accurate metrics
        metrics = painter.fontMetrics()

        if self.is_vertical:
            max_char_width = 0
            total_height = 0
            for char in self.text:
                char_rect = metrics.boundingRect(char)
                max_char_width = max(max_char_width, char_rect.width())
                total_height += metrics.height() + self.line_spacing
            self.width = max_char_width
            self.height = total_height - self.line_spacing if total_height > 0 else 0
        else:
            # For horizontal text, use boundingRect to get size
            # QRect(0, 0, large_width, large_height) is a common pattern for unbounded text rect calculation
            text_rect = metrics.boundingRect(QRect(0, 0, 10000, 10000), Qt.TextFlag.TextWordWrap, self.text)
            self.width = text_rect.width()
            self.height = text_rect.height() + (self.text.count('\n') * self.line_spacing) # Account for spacing on newlines

    def draw(self, painter):
        """Draw text in the given QPainter context with stroke and shadow using QPainterPath."""
        painter.save() # Save current painter state

        font = self.get_qfont()
        painter.setFont(font)
        metrics = painter.fontMetrics()

        # 1. Create QPainterPath for the text
        text_path = QPainterPath()
        if not self.is_vertical:
            # For horizontal text, add the entire text as a path
            # QPointF(self.x, self.y + metrics.ascent()) is the baseline for horizontal text
            text_path.addText(QPointF(self.x, self.y + metrics.ascent()), font, self.text)
        else:
            # For vertical text, add each character separately
            current_y = self.y
            for char in self.text:
                # QPointF(self.x, current_y + metrics.ascent()) is the baseline for each vertical character
                text_path.addText(QPointF(self.x, current_y + metrics.ascent()), font, char)
                current_y += metrics.height() + self.line_spacing

        # 2. Apply text-specific transformations (rotation, scale) to the path
        # These transformations are relative to the text box's center
        transform = QTransform()
        transform.translate(self.x + self.width / 2, self.y + self.height / 2)
        transform.rotate(self.rotation)
        transform.scale(self.scale_x, self.scale_y)
        transform.translate(-(self.x + self.width / 2), -(self.y + self.height / 2))
        
        transformed_path = transform.map(text_path)

        # 3. Draw shadow (stroke and fill)
        if self.shadow_offset_x != 0 or self.shadow_offset_y != 0:
            shadow_transform = QTransform()
            shadow_transform.translate(self.shadow_offset_x, self.shadow_offset_y)
            shadow_path = shadow_transform.map(transformed_path)

            # Draw shadow stroke
            if self.stroke_width > 0:
                # Use stroke_width directly for consistent scaling with main text
                painter.setPen(QPen(self.shadow_color, self.stroke_width, Qt.SolidLine, Qt.RoundJoin, Qt.RoundCap)) 
                painter.setBrush(Qt.NoBrush) # Important: stroke should not fill
                painter.drawPath(shadow_path)
            
            # Draw shadow fill
            painter.setPen(Qt.NoPen) # Important: fill should not have a pen
            painter.setBrush(self.shadow_color)
            painter.drawPath(shadow_path)

        # 4. Draw main text (stroke and fill)
        # Draw main text stroke (if stroke_width > 0)
        if self.stroke_width > 0:
            # Use stroke_width directly. QPen width is in device pixels.
            # The visual thickness will be affected by the canvas zoom_level,
            # but the numerical value passed here should be what the user set.
            painter.setPen(QPen(self.stroke_color, self.stroke_width, Qt.SolidLine, Qt.RoundJoin, Qt.RoundCap)) 
            painter.setBrush(Qt.NoBrush) # Important: stroke should not fill
            painter.drawPath(transformed_path)

        # Draw main text fill (always draw to ensure text is visible even with stroke_width=0)
        painter.setPen(Qt.NoPen) # Important: fill should not have a pen
        painter.setBrush(self.color)
        painter.drawPath(transformed_path)

        painter.restore() # Restore painter state

    def is_point_in_bbox(self, px, py):
        """Check if point (px, py) is within the text box's bounding box (considering transformations)"""
        # For simplicity, we'll use an AABB check based on the untransformed bounding box.
        # For perfect collision with rotated/scaled boxes, you'd transform the point back
        # by the inverse of the text box's transform and check against the untransformed bbox.
        # This current implementation will be less accurate for rotated boxes.
        return self.x <= px <= (self.x + self.width) and self.y <= py <= (self.y + self.height)

    def to_dict(self):
        """Convert TextBox object to dictionary for serialization"""
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "color": self.color.name(), # Save QColor as hex string
            "is_vertical": self.is_vertical,
            "stroke_width": self.stroke_width,
            "stroke_color": self.stroke_color.name(),
            "shadow_offset_x": self.shadow_offset_x,
            "shadow_offset_y": self.shadow_offset_y,
            "shadow_color": self.shadow_color.name(),
            "line_spacing": self.line_spacing,
            "rotation": self.rotation,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y
        }

    @staticmethod
    def from_dict(data):
        """Create TextBox object from dictionary"""
        tb = TextBox(data["x"], data["y"], data["text"],
                     data.get("font_family", DEFAULT_FONT), 
                     data.get("font_size", DEFAULT_FONT_SIZE), 
                     data.get("color", DEFAULT_TEXT_COLOR),
                     data.get("is_vertical", False),
                     data.get("stroke_width", 0),
                     data.get("stroke_color", "#FFFFFF"),
                     data.get("shadow_offset_x", 0),
                     data.get("shadow_offset_y", 0),
                     data.get("shadow_color", "#000000"),
                     data.get("line_spacing", 0),
                     data.get("rotation", 0.0),
                     data.get("scale_x", 1.0),
                     data.get("scale_y", 1.0))
        tb.id = data["id"]
        return tb

# --- Main Image Display Widget ---
class ImageCanvas(QWidget):
    def __init__(self, main_app_instance=None): # Accept main_app_instance as argument
        super().__init__(main_app_instance) # Pass it to QWidget parent
        self.main_app = main_app_instance # Store reference to MangaTypesetterApp
        self.setBackgroundRole(self.backgroundRole().NoRole) # Transparent background
        self.setMouseTracking(True) # Enable mouse move events even without button pressed
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.image_pixmap = QPixmap()
        self.display_image_pil = None # PIL image with text rendered
        self.zoom_level = 1.0
        self.offset = QPointF(0, 0) # Offset for pan

        self.text_boxes = []
        self.selected_text_boxes = []
        self.drag_start_pos = QPoint()
        self.dragging_textbox = False
        self.panning_canvas = False # New flag for panning
        self.current_scale_factor = 1.0 # For internal scaling of painter

    def set_image(self, pixmap):
        """Set the QPixmap to be displayed"""
        self.image_pixmap = pixmap
        self.update_canvas_size()
        self.update() # Trigger repaint

    def clear_image(self):
        self.display_image_pil = None # Still keeping this for potential future PIL operations
        self.image_pixmap = QPixmap()
        self.text_boxes = []
        self.selected_text_boxes = []
        self.zoom_level = 1.0
        self.offset = QPointF(0, 0)
        self.update_canvas_size()
        self.update()

    def update_canvas_size(self):
        """Update the minimum size of the canvas based on image and zoom level, to enable scrollbars"""
        if not self.image_pixmap.isNull():
            scaled_width = int(self.image_pixmap.width() * self.zoom_level)
            scaled_height = int(self.image_pixmap.height() * self.zoom_level)
            self.setMinimumSize(scaled_width, scaled_height)
        else:
            self.setMinimumSize(0, 0)

    def paintEvent(self, event):
        """Paint event: draws the image and text boxes"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Apply pan offset first
        painter.translate(self.offset)

        # Apply zoom transformation
        painter.scale(self.zoom_level, self.zoom_level)

        if not self.image_pixmap.isNull():
            # Draw the base image (which already has inpaint + original + text rendered by main app)
            painter.drawPixmap(0, 0, self.image_pixmap)

        # Draw selection rectangles for selected text boxes
        # These are drawn on top of the rendered image
        painter.setPen(QColor(255, 0, 0, 255)) # Red outline
        painter.setBrush(Qt.NoBrush)
        # Scale pen width with zoom so it appears consistent
        painter.setPen(QPen(QColor(255, 0, 0, 255), 2 / self.zoom_level)) 

        for tb in self.selected_text_boxes:
            # The bbox of TextBox is in original image coordinates
            # We need to draw it relative to the current painter's coordinate system (which is already scaled)
            rect = QRect(int(tb.x), int(tb.y), int(tb.width), int(tb.height))
            painter.drawRect(rect)
        
        painter.end()


    def mousePressEvent(self, event: QMouseEvent):
        """Mouse press event"""
        # Convert mouse position to original image coordinates
        mouse_x_pan_adjusted = (event.position().x() - self.offset.x())
        mouse_y_pan_adjusted = (event.position().y() - self.offset.y())
        click_x_original = mouse_x_pan_adjusted / self.zoom_level
        click_y_original = mouse_y_pan_adjusted / self.zoom_level

        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint() # Mouse position in widget coordinates
            
            clicked_a_box = False
            clicked_box = None

            for tb in reversed(self.text_boxes):
                if tb.is_point_in_bbox(click_x_original, click_y_original):
                    clicked_box = tb
                    clicked_a_box = True
                    break
            
            if event.modifiers() & Qt.ShiftModifier: # Shift key is pressed (multi-select)
                if clicked_box:
                    if clicked_box in self.selected_text_boxes:
                        self.selected_text_boxes.remove(clicked_box)
                    else:
                        self.selected_text_boxes.append(clicked_box)
            else: # Single select
                self.selected_text_boxes = []
                if clicked_box:
                    self.selected_text_boxes.append(clicked_box)
            
            if self.selected_text_boxes:
                self.dragging_textbox = True
            else:
                self.dragging_textbox = False # Not dragging a textbox
            
            # Emit signal to update UI in main app
            self.main_app._update_text_box_ui()
            self.update() # Trigger repaint for selection rectangles

        elif event.button() == Qt.MiddleButton: # Middle button for panning
            self.drag_start_pos = event.position().toPoint()
            self.panning_canvas = True
            self.setCursor(Qt.ClosedHandCursor) # Change cursor to closed hand
        
        elif event.button() == Qt.RightButton:
            self.main_app._show_context_menu(event.globalPosition().toPoint(), click_x_original, click_y_original)


    def mouseMoveEvent(self, event: QMouseEvent):
        """Mouse move event"""
        if event.buttons() & Qt.LeftButton and self.dragging_textbox: # Left button and dragging textbox
            delta = event.position().toPoint() - self.drag_start_pos
            
            if self.selected_text_boxes and not self.image_pixmap.isNull():
                img_width, img_height = self.image_pixmap.width(), self.image_pixmap.height()
                
                # Convert delta from scaled canvas pixels to original image pixels
                move_x_original = delta.x() / self.zoom_level
                move_y_original = delta.y() / self.zoom_level

                for tb in self.selected_text_boxes:
                    tb.x += move_x_original
                    tb.y += move_y_original
                    # Limit text box within image bounds
                    tb.x = max(0, min(tb.x, img_width - tb.width))
                    tb.y = max(0, min(tb.y, img_height - tb.height))
                
                self.drag_start_pos = event.position().toPoint() # Reset drag start for continuous dragging
                self.main_app._update_text_box_ui() # Update UI with new position
                self.main_app.update_image_display() # Redraw image with new text box positions
        
        elif event.buttons() & Qt.MiddleButton and self.panning_canvas: # Middle button and panning canvas
            delta = event.position().toPoint() - self.drag_start_pos
            self.offset += delta
            self.drag_start_pos = event.position().toPoint() # Reset drag start for continuous panning
            self._clamp_offset() # Clamp offset after panning
            self.update() # Trigger repaint for pan
            self.setCursor(Qt.ClosedHandCursor) # Ensure cursor stays closed hand during pan
        else:
            self.setCursor(Qt.ArrowCursor) # Default cursor when not dragging/panning

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Mouse release event"""
        if event.button() == Qt.LeftButton:
            self.dragging_textbox = False
            self.main_app.update_image_display() # Ensure final state is drawn
        elif event.button() == Qt.MiddleButton:
            self.panning_canvas = False
            self.setCursor(Qt.ArrowCursor) # Reset cursor to arrow

    def wheelEvent(self, event: QWheelEvent):
        """Wheel event: zoom or pan"""
        if self.image_pixmap.isNull(): return

        # Get mouse position relative to the image (in original image coordinates)
        mouse_pos_in_image = (event.position().x() - self.offset.x()) / self.zoom_level, \
                             (event.position().y() - self.offset.y()) / self.zoom_level

        if event.modifiers() & Qt.ShiftModifier: # Shift + Wheel (Zoom)
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
            self.zoom_level *= zoom_factor
            self.zoom_level = max(0.1, min(self.zoom_level, 10.0)) # Limit zoom range

            # Adjust offset to keep mouse position fixed
            self.offset.setX(event.position().x() - mouse_pos_in_image[0] * self.zoom_level)
            self.offset.setY(event.position().y() - mouse_pos_in_image[1] * self.zoom_level)

            self.update_canvas_size() # Update minimum size for scroll area
            self._clamp_offset() # Clamp offset after zoom
            self.main_app.update_image_display() # Redraw main image after zoom
        elif event.modifiers() & Qt.ControlModifier: # Ctrl + Wheel (Horizontal pan)
            scroll_amount = 20 if event.angleDelta().y() > 0 else -20
            self.offset.setX(self.offset.x() + scroll_amount)
            self._clamp_offset() # Clamp offset after pan
            self.update()
        else: # Wheel (Vertical pan)
            scroll_amount = 20 if event.angleDelta().y() > 0 else -20
            self.offset.setY(self.offset.y() + scroll_amount)
            self._clamp_offset() # Clamp offset after pan
            self.update()

    def _clamp_offset(self):
        """Clamps the offset to keep the image within view and allow scrolling."""
        if not self.image_pixmap.isNull():
            scaled_width = self.image_pixmap.width() * self.zoom_level
            scaled_height = self.image_pixmap.height() * self.zoom_level
            
            # Get viewport size from the scroll area
            # Accessing main_app.scroll_area directly as ImageCanvas is a widget inside it.
            viewport_rect = self.main_app.scroll_area.viewport().rect()
            viewport_width = viewport_rect.width()
            viewport_height = viewport_rect.height()

            # Calculate maximum negative offsets (image edge aligns with viewport edge)
            # If image is smaller than viewport, max_offset will be positive or zero, centering it.
            # The min_x/y_offset is always 0 (top-left of image should not go beyond top-left of viewport)
            # The max_x/y_offset is the point where the right/bottom edge of the image aligns with the right/bottom edge of the viewport.
            # If scaled_width < viewport_width, the image should be centered, meaning offset should be positive.
            # So, the range for x is [max(viewport_width - scaled_width, 0), 0]
            # Example: viewport_width=800, scaled_width=1000 => range [-200, 0]
            # Example: viewport_width=800, scaled_width=600 => range [200, 0] (but we want it centered, so it should be 100)
            # This clamping logic needs to ensure the image is always visible and centered if smaller than viewport.

            # Simplified clamping:
            # If image is larger than viewport, clamp between (viewport - image) and 0.
            # If image is smaller than viewport, center it.
            
            if scaled_width < viewport_width:
                self.offset.setX((viewport_width - scaled_width) / 2)
            else:
                self.offset.setX(max(viewport_width - scaled_width, min(0.0, self.offset.x())))

            if scaled_height < viewport_height:
                self.offset.setY((viewport_height - scaled_height) / 2)
            else:
                self.offset.setY(max(viewport_height - scaled_height, min(0.0, self.offset.y())))


# --- Main Application Class ---
class MangaTypesetterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("轻量漫画嵌字工具 (PySide6)")
        self.setGeometry(100, 100, 1400, 800)
        self.setMinimumSize(800, 600) # Set a minimum size for the main window

        self.current_folder = None
        self.image_files = []
        self.current_image_index = -1

        self.original_image_path = None
        self.inpaint_image_path = None
        
        self.current_base_inpaint_img = None # PIL Image
        self.current_base_original_img = None # PIL Image

        self.text_boxes = []
        self.selected_text_boxes = []

        self.original_image_alpha = 0.5
        self.font_family_var = DEFAULT_FONT
        self.text_direction_var = "横排"

        self.stroke_width_var = 0
        self.stroke_color_var = "#FFFFFF"
        self.shadow_offset_x_var = 0
        self.shadow_offset_y_var = 0
        self.shadow_color_var = "#000000"
        self.line_spacing_var = 0
        self.rotation_var = 0.0
        self.scale_x_var = 1.0
        self.scale_y_var = 1.0

        self.page_data = {}
        self.presets = {}

        self._load_presets()
        # Call _load_system_fonts BEFORE _create_widgets to ensure self.system_fonts is populated
        self._load_system_fonts() 
        self._create_widgets() # This will now create all widgets as attributes
        self._bind_signals()

    def _load_system_fonts(self):
        """Load installed system fonts, prioritizing common Chinese fonts."""
        self.system_fonts = [] # Initialize self.system_fonts here
        for family in QFontDatabase.families():
            self.system_fonts.append(family)
        self.system_fonts.sort()

        # Prioritize common Chinese fonts if available
        # This helps ensure Chinese characters are rendered correctly.
        preferred_chinese_fonts = ["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
        found_preferred = False
        for font_name in preferred_chinese_fonts:
            if font_name in self.system_fonts:
                self.font_family_var = font_name
                found_preferred = True
                break
        
        if not found_preferred and self.system_fonts:
            # Fallback to the first available system font if no preferred Chinese fonts are found
            self.font_family_var = self.system_fonts[0] 
            QMessageBox.warning(self, "警告", f"未找到推荐的中文字体 ({', '.join(preferred_chinese_fonts)})。将使用系统默认字体 '{self.font_family_var}'，可能不支持中文显示。")
        elif not self.system_fonts:
            # Fallback to hardcoded Arial if no fonts found at all
            self.font_family_var = "Arial" 
            QMessageBox.warning(self, "警告", "未找到任何系统字体。将使用 'Arial'，可能不支持中文显示。请确保您的系统安装了字体。")
        
        # Removed the problematic lines that accessed self.font_family_combobox here.
        # The combobox population and setting of current text is now handled in _create_widgets.


    def _create_widgets(self):
        """Create GUI elements"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Initialize all widgets first ---
        self.text_entry = QTextEdit()
        self.text_entry.setFixedHeight(80)
        self.font_family_combobox = QComboBox()
        # Populate with system fonts. self.system_fonts is now guaranteed to be populated.
        self.font_family_combobox.addItems(self.system_fonts) 
        # Set initial text based on loaded font_family_var from _load_system_fonts
        self.font_family_combobox.setCurrentText(self.font_family_var) 
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 100)
        self.font_size_spinbox.setValue(DEFAULT_FONT_SIZE)
        self.color_button = QPushButton("选择颜色")
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setStyleSheet(f"background-color: {DEFAULT_TEXT_COLOR}; border: 1px solid gray;")
        self.current_text_color = QColor(DEFAULT_TEXT_COLOR)
        self.text_direction_combobox = QComboBox()
        self.text_direction_combobox.addItems(["横排", "竖排"])

        self.stroke_width_spinbox = QSpinBox()
        self.stroke_width_spinbox.setRange(0, 10)
        self.stroke_color_button = QPushButton("选择")
        self.stroke_color_preview = QLabel()
        self.stroke_color_preview.setFixedSize(20, 20)
        self.stroke_color_preview.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid gray;")
        self.current_stroke_color = QColor("#FFFFFF")

        self.shadow_offset_x_spinbox = QSpinBox()
        self.shadow_offset_x_spinbox.setRange(-50, 50)
        self.shadow_offset_y_spinbox = QSpinBox()
        self.shadow_offset_y_spinbox.setRange(-50, 50)
        self.shadow_color_button = QPushButton("选择")
        self.shadow_color_preview = QLabel()
        self.shadow_color_preview.setFixedSize(20, 20)
        self.shadow_color_preview.setStyleSheet(f"background-color: #000000; border: 1px solid gray;")
        self.current_shadow_color = QColor("#000000")

        self.line_spacing_spinbox = QSpinBox()
        # Adjusted range to allow negative values for line spacing
        self.line_spacing_spinbox.setRange(-20, 50) 
        self.rotation_spinbox = QSpinBox()
        self.rotation_spinbox.setRange(-180, 180)
        self.rotation_spinbox.setValue(0)
        self.scale_x_spinbox = QDoubleSpinBox()
        self.scale_x_spinbox.setRange(0.1, 5.0)
        self.scale_x_spinbox.setSingleStep(0.1)
        self.scale_x_spinbox.setValue(1.0)
        self.scale_y_spinbox = QDoubleSpinBox()
        self.scale_y_spinbox.setRange(0.1, 5.0)
        self.scale_y_spinbox.setSingleStep(0.1)
        self.scale_y_spinbox.setValue(1.0)

        self.preset_name_entry = QLineEdit()
        self.save_preset_button = QPushButton("保存当前预设")
        self.load_preset_button = QPushButton("加载预设")
        self.preset_listbox = QListWidget()
        self.preset_listbox.setFixedHeight(80)

        self.add_text_button = QPushButton("添加文本框")
        self.apply_format_button = QPushButton("应用格式到选中框")

        # --- Top Toolbar (includes Open Folder, Save, Fullscreen buttons) ---
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        open_folder_action = toolbar.addAction("打开文件夹")
        open_folder_action.triggered.connect(self.open_folder)

        save_image_action = toolbar.addAction("保存嵌字图")
        save_image_action.triggered.connect(self.save_typeset_image)

        toolbar.addSeparator()

        self.fullscreen_button = QPushButton("全屏")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_button)


        # --- Left Image Preview Panel ---
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setFixedWidth(150)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.addWidget(QLabel("图片预览"))

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(THUMBNAIL_SIZE)
        self.thumbnail_list.setSpacing(5)
        left_layout.addWidget(self.thumbnail_list)
        main_layout.addWidget(self.left_panel)

        # --- Middle Image Display Area ---
        # Pass 'self' (MangaTypesetterApp instance) as the main_app_instance to ImageCanvas
        self.image_canvas = ImageCanvas(main_app_instance=self) 
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_canvas)
        self.scroll_area.setAlignment(Qt.AlignCenter) # Center the image initially

        # --- Right Control Panel (now tabbed) ---
        self.control_panel = QFrame()
        self.control_panel.setFrameShape(QFrame.StyledPanel)
        self.control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(self.control_panel)

        self.tab_widget = QTabWidget()
        control_layout.addWidget(self.tab_widget)

        # --- Text Content/Font Tab ---
        text_tab_widget = QWidget()
        text_tab_layout = QVBoxLayout(text_tab_widget)
        text_tab_layout.addWidget(QLabel("文本内容:"))
        text_tab_layout.addWidget(self.text_entry)
        text_tab_layout.addWidget(QLabel("字体家族:"))
        text_tab_layout.addWidget(self.font_family_combobox)
        text_tab_layout.addWidget(QLabel("字体大小:"))
        text_tab_layout.addWidget(self.font_size_spinbox)
        text_tab_layout.addWidget(QLabel("文本颜色:"))
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch(1)
        text_tab_layout.addLayout(color_layout)
        text_tab_layout.addWidget(QLabel("文本方向:"))
        text_tab_layout.addWidget(self.text_direction_combobox)
        text_tab_layout.addStretch(1) # Push content to top

        text_tab_scroll_area = QScrollArea()
        text_tab_scroll_area.setWidgetResizable(True)
        text_tab_scroll_area.setWidget(text_tab_widget)
        self.tab_widget.addTab(text_tab_scroll_area, "文本/字体")

        # --- Stroke Settings Tab ---
        stroke_tab_widget = QWidget()
        stroke_tab_layout = QVBoxLayout(stroke_tab_widget)
        
        # Corrected QGroupBox usage
        stroke_group = QGroupBox("描边设置")
        stroke_group_layout = QVBoxLayout(stroke_group) # Use QVBoxLayout for vertical arrangement inside group
        stroke_group_layout.addWidget(QLabel("宽度:"))
        stroke_group_layout.addWidget(self.stroke_width_spinbox)
        stroke_group_layout.addWidget(QLabel("颜色:"))
        stroke_color_layout = QHBoxLayout()
        stroke_color_layout.addWidget(self.stroke_color_button)
        stroke_color_layout.addWidget(self.stroke_color_preview)
        stroke_color_layout.addStretch(1)
        stroke_group_layout.addLayout(stroke_color_layout)
        stroke_tab_layout.addWidget(stroke_group) # Add the QGroupBox to the tab layout
        stroke_tab_layout.addStretch(1)

        stroke_tab_scroll_area = QScrollArea()
        stroke_tab_scroll_area.setWidgetResizable(True)
        stroke_tab_scroll_area.setWidget(stroke_tab_widget)
        self.tab_widget.addTab(stroke_tab_scroll_area, "描边")

        # --- Shadow Settings Tab ---
        shadow_tab_widget = QWidget()
        shadow_tab_layout = QVBoxLayout(shadow_tab_widget)
        
        # Corrected QGroupBox usage
        shadow_group = QGroupBox("阴影设置")
        shadow_group_layout = QVBoxLayout(shadow_group)
        shadow_offset_layout = QHBoxLayout()
        shadow_offset_layout.addWidget(QLabel("X偏移:"))
        shadow_offset_layout.addWidget(self.shadow_offset_x_spinbox)
        shadow_offset_layout.addWidget(QLabel("Y偏移:"))
        shadow_offset_layout.addWidget(self.shadow_offset_y_spinbox)
        shadow_group_layout.addLayout(shadow_offset_layout)

        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(QLabel("颜色:"))
        shadow_color_layout.addWidget(self.shadow_color_button)
        shadow_color_layout.addWidget(self.shadow_color_preview)
        shadow_color_layout.addStretch(1)
        shadow_group_layout.addLayout(shadow_color_layout)
        shadow_tab_layout.addWidget(shadow_group) # Add the QGroupBox to the tab layout
        shadow_tab_layout.addStretch(1)

        shadow_tab_scroll_area = QScrollArea()
        shadow_tab_scroll_area.setWidgetResizable(True)
        shadow_tab_scroll_area.setWidget(shadow_tab_widget)
        self.tab_widget.addTab(shadow_tab_scroll_area, "阴影")

        # --- Transform Settings Tab (Rotation and Scale) ---
        transform_tab_widget = QWidget()
        transform_tab_layout = QVBoxLayout(transform_tab_widget)
        
        # Corrected QGroupBox usage
        transform_group = QGroupBox("变换设置")
        transform_group_layout = QVBoxLayout(transform_group)
        transform_group_layout.addWidget(QLabel("旋转 (度):"))
        transform_group_layout.addWidget(self.rotation_spinbox)
        transform_group_layout.addWidget(QLabel("X缩放:"))
        transform_group_layout.addWidget(self.scale_x_spinbox)
        transform_group_layout.addWidget(QLabel("Y缩放:"))
        transform_group_layout.addWidget(self.scale_y_spinbox)
        transform_group_layout.addWidget(QLabel("行间距:"))
        transform_group_layout.addWidget(self.line_spacing_spinbox)
        transform_tab_layout.addWidget(transform_group) # Add the QGroupBox to the tab layout
        transform_tab_layout.addStretch(1)

        transform_tab_scroll_area = QScrollArea()
        transform_tab_scroll_area.setWidgetResizable(True)
        transform_tab_scroll_area.setWidget(transform_tab_widget)
        self.tab_widget.addTab(transform_tab_scroll_area, "变换/间距")

        # --- Preset Functionality Tab ---
        preset_tab_widget = QWidget()
        preset_tab_layout = QVBoxLayout(preset_tab_widget)
        
        # Corrected QGroupBox usage
        preset_group = QGroupBox("文本格式预设")
        preset_group_layout = QVBoxLayout(preset_group)
        preset_group_layout.addWidget(QLabel("预设名称:"))
        preset_group_layout.addWidget(self.preset_name_entry)
        preset_buttons_layout = QHBoxLayout()
        preset_buttons_layout.addWidget(self.save_preset_button)
        preset_buttons_layout.addWidget(self.load_preset_button)
        preset_group_layout.addLayout(preset_buttons_layout)
        preset_group_layout.addWidget(self.preset_listbox)
        preset_tab_layout.addWidget(preset_group) # Add the QGroupBox to the tab layout
        preset_tab_layout.addStretch(1)

        preset_tab_scroll_area = QScrollArea()
        preset_tab_scroll_area.setWidgetResizable(True)
        preset_tab_scroll_area.setWidget(preset_tab_widget)
        self.tab_widget.addTab(preset_tab_scroll_area, "预设")

        # --- Restrictions Tab ---
        restrictions_tab_widget = QWidget()
        restrictions_tab_layout = QVBoxLayout(restrictions_tab_widget)
        restrictions_label = QLabel("<b>功能限制:</b><br>"
                                   "• 无法精确控制字间距<br>"
                                   "• 竖排仅为字符堆叠，非东亚标准格式")
        restrictions_label.setWordWrap(True)
        restrictions_tab_layout.addWidget(restrictions_label)
        restrictions_tab_layout.addStretch(1)

        restrictions_tab_scroll_area = QScrollArea()
        restrictions_tab_scroll_area.setWidgetResizable(True)
        restrictions_tab_scroll_area.setWidget(restrictions_tab_widget)
        self.tab_widget.addTab(restrictions_tab_scroll_area, "限制")


        control_layout.addStretch(1) # Push buttons to top

        control_layout.addWidget(self.add_text_button)
        control_layout.addWidget(self.apply_format_button)

        main_layout.addWidget(self.control_panel)

        # --- Original Image Transparency Control (moved below main canvas) ---
        alpha_control_layout = QHBoxLayout()
        alpha_control_layout.addWidget(QLabel("原图透明度:"))
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(0, 100) # 0-100 for 0.0-1.0
        self.alpha_slider.setValue(int(self.original_image_alpha * 100))
        alpha_control_layout.addWidget(self.alpha_slider)
        
        # Adjusting the layout structure to place alpha slider below the canvas
        canvas_and_alpha_container = QWidget() # Create a QWidget to hold the QVBoxLayout
        canvas_and_alpha_layout = QVBoxLayout(canvas_and_alpha_container) # Set the layout on the container widget
        canvas_and_alpha_layout.addWidget(self.scroll_area, 1) # Stretch factor 1
        canvas_and_alpha_layout.addLayout(alpha_control_layout)
        
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(canvas_and_alpha_container, 1) # Add the container widget to the main layout
        main_layout.addWidget(self.control_panel)


    def _bind_signals(self):
        """Bind widget signals"""
        self.add_text_button.clicked.connect(self.add_text_box)
        self.apply_format_button.clicked.connect(self.apply_format_to_selected)
        self.color_button.clicked.connect(self.choose_color)
        self.stroke_color_button.clicked.connect(lambda: self.choose_color_for("stroke"))
        self.shadow_color_button.clicked.connect(lambda: self.choose_color_for("shadow"))

        self.text_entry.textChanged.connect(self._on_text_change)
        self.font_family_combobox.currentTextChanged.connect(self._on_text_change)
        self.font_size_spinbox.valueChanged.connect(self._on_text_change)
        self.text_direction_combobox.currentTextChanged.connect(self._on_text_change)
        self.stroke_width_spinbox.valueChanged.connect(self._on_text_change)
        self.shadow_offset_x_spinbox.valueChanged.connect(self._on_text_change)
        self.shadow_offset_y_spinbox.valueChanged.connect(self._on_text_change)
        self.line_spacing_spinbox.valueChanged.connect(self._on_text_change)
        self.rotation_spinbox.valueChanged.connect(self._on_text_change)
        self.scale_x_spinbox.valueChanged.connect(self._on_text_change)
        self.scale_y_spinbox.valueChanged.connect(self._on_text_change)

        self.alpha_slider.valueChanged.connect(self._on_alpha_slider_changed)
        
        self.thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)

        self.save_preset_button.clicked.connect(self.save_current_preset)
        self.load_preset_button.clicked.connect(self.load_selected_preset)
        self.preset_listbox.itemClicked.connect(self._on_preset_select) 

    def _on_alpha_slider_changed(self, value):
        self.original_image_alpha = value / 100.0
        self.update_image_display()

    def _on_thumbnail_clicked(self, item):
        if isinstance(item, QListWidgetItem):
            index = self.thumbnail_list.row(item)
            self.load_image_by_index(index)

    def _on_text_change(self):
        """When text input or format changes, update the preview of selected text boxes in real-time"""
        if self.selected_text_boxes:
            for tb in self.selected_text_boxes:
                tb.text = self.text_entry.toPlainText()
                tb.font_family = self.font_family_combobox.currentText()
                tb.font_size = self.font_size_spinbox.value()
                tb.color = self.current_text_color
                tb.is_vertical = (self.text_direction_combobox.currentText() == "竖排")
                tb.stroke_width = self.stroke_width_spinbox.value()
                tb.stroke_color = self.current_stroke_color
                tb.shadow_offset_x = self.shadow_offset_x_spinbox.value()
                tb.shadow_offset_y = self.shadow_offset_y_spinbox.value()
                tb.shadow_color = self.current_shadow_color
                tb.line_spacing = self.line_spacing_spinbox.value()
                tb.rotation = self.rotation_spinbox.value()
                tb.scale_x = self.scale_x_spinbox.value()
                tb.scale_y = self.scale_y_spinbox.value()
            self.update_image_display()

    def update_preset_listbox(self):
        """Update the preset list box"""
        self.preset_listbox.clear()
        for name in self.presets.keys():
            self.preset_listbox.addItem(name)

    def _load_presets(self):
        """Load presets from file"""
        self.presets = {}
        if os.path.exists(PRESET_FILE):
            try:
                with open(PRESET_FILE, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Warning", "Preset file corrupted, reset.")
                self.presets = {}

    def _save_presets(self):
        """Save presets to file"""
        with open(PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=4)

    def save_current_preset(self):
        """Save current text box format as preset"""
        preset_name = self.preset_name_entry.text().strip()
        if not preset_name:
            QMessageBox.warning(self, "Warning", "Please enter a preset name!")
            return
        
        current_format = {
            "text": self.text_entry.toPlainText(),
            "font_family": self.font_family_combobox.currentText(),
            "font_size": self.font_size_spinbox.value(),
            "color": self.current_text_color.name(),
            "is_vertical": (self.text_direction_combobox.currentText() == "竖排"),
            "stroke_width": self.stroke_width_spinbox.value(),
            "stroke_color": self.current_stroke_color.name(),
            "shadow_offset_x": self.shadow_offset_x_spinbox.value(),
            "shadow_offset_y": self.shadow_offset_y_spinbox.value(),
            "shadow_color": self.current_shadow_color.name(),
            "line_spacing": self.line_spacing_spinbox.value(),
            "rotation": self.rotation_spinbox.value(),
            "scale_x": self.scale_x_spinbox.value(),
            "scale_y": self.scale_y_spinbox.value()
        }
        self.presets[preset_name] = current_format
        self._save_presets()
        self.update_preset_listbox()
        QMessageBox.information(self, "Success", f"Preset '{preset_name}' saved.")

    def load_selected_preset(self):
        """Load selected preset to control panel"""
        selected_items = self.preset_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a preset!")
            return
        
        preset_name = selected_items[0].text()
        preset_data = self.presets.get(preset_name)
        if preset_data:
            self.text_entry.setText(preset_data.get("text", ""))
            self.font_family_combobox.setCurrentText(preset_data.get("font_family", DEFAULT_FONT))
            self.font_size_spinbox.setValue(preset_data.get("font_size", DEFAULT_FONT_SIZE))
            self.current_text_color = QColor(preset_data.get("color", DEFAULT_TEXT_COLOR))
            self.color_preview.setStyleSheet(f"background-color: {self.current_text_color.name()}; border: 1px solid gray;")
            self.text_direction_combobox.setCurrentText("竖排" if preset_data.get("is_vertical", False) else "横排")
            self.stroke_width_spinbox.setValue(preset_data.get("stroke_width", 0))
            self.current_stroke_color = QColor(preset_data.get("stroke_color", "#FFFFFF"))
            self.stroke_color_preview.setStyleSheet(f"background-color: {self.current_stroke_color.name()}; border: 1px solid gray;")
            self.shadow_offset_x_spinbox.setValue(preset_data.get("shadow_offset_x", 0))
            self.shadow_offset_y_spinbox.setValue(preset_data.get("shadow_offset_y", 0))
            self.current_shadow_color = QColor(preset_data.get("shadow_color", "#000000"))
            self.shadow_color_preview.setStyleSheet(f"background-color: {self.current_shadow_color.name()}; border: 1px solid gray;")
            self.line_spacing_spinbox.setValue(preset_data.get("line_spacing", 0))
            self.rotation_spinbox.setValue(preset_data.get("rotation", 0.0))
            self.scale_x_spinbox.setValue(preset_data.get("scale_x", 1.0))
            self.scale_y_spinbox.setValue(preset_data.get("scale_y", 1.0))

            self.preset_name_entry.setText(preset_name)
            
            # If a text box is selected, apply to it as well
            if self.selected_text_boxes:
                self.apply_format_to_selected()
            else:
                self.update_image_display()
        QMessageBox.information(self, "Success", f"Preset '{preset_name}' loaded.")

    def _on_preset_select(self, item): 
        """When preset list box selection changes, automatically fill preset name into input box"""
        if item:
            preset_name = item.text()
            self.preset_name_entry.setText(preset_name)
            # Optionally load the preset directly on click
            # self.load_selected_preset() # Uncomment if you want auto-load on click

    def choose_color(self):
        """Open color picker for main text color"""
        color = QColorDialog.getColor(self.current_text_color, self, "选择文本颜色")
        if color.isValid():
            self.current_text_color = color
            self.color_preview.setStyleSheet(f"background-color: {self.current_text_color.name()}; border: 1px solid gray;")
            self._on_text_change()

    def choose_color_for(self, target):
        """Open color picker for stroke or shadow color"""
        if target == "stroke":
            initial_color = self.current_stroke_color
            title = "选择描边颜色"
        elif target == "shadow":
            initial_color = self.current_shadow_color
            title = "选择阴影颜色"
        else:
            return

        color = QColorDialog.getColor(initial_color, self, title)
        if color.isValid():
            if target == "stroke":
                self.current_stroke_color = color
                self.stroke_color_preview.setStyleSheet(f"background-color: {self.current_stroke_color.name()}; border: 1px solid gray;")
            elif target == "shadow":
                self.current_shadow_color = color
                self.shadow_color_preview.setStyleSheet(f"background-color: {self.current_shadow_color.name()}; border: 1px solid gray;")
            self._on_text_change()

    def open_folder(self):
        """Open manga folder"""
        folder_selected = QFileDialog.getExistingDirectory(self, "选择漫画文件夹")
        if folder_selected:
            if self.current_folder and self.inpaint_image_path:
                self._save_current_page_data()

            self.current_folder = folder_selected
            inpaint_path = os.path.join(self.current_folder, INPAINT_FOLDER)
            qianresult_path = os.path.join(self.current_folder, QIANRESULT_FOLDER)

            os.makedirs(inpaint_path, exist_ok=True)
            os.makedirs(qianresult_path, exist_ok=True)
            print(f"Ensured '{INPAINT_FOLDER}' and '{QIANRESULT_FOLDER}' folders exist.")

            self.image_files = get_image_files(inpaint_path)
            
            if not self.image_files:
                QMessageBox.warning(self, "Warning", f"No images found in '{inpaint_path}' folder. Please place inpaint images.")
                self.current_image_index = -1
                self.image_canvas.clear_image()
                self.current_base_inpaint_img = None
                self.current_base_original_img = None
                self.thumbnail_list.clear()
                return

            self._load_all_page_data()
            self._populate_thumbnail_previews()
            
            self.current_image_index = 0
            self.load_image_by_index(self.current_image_index)

    def _populate_thumbnail_previews(self):
        """Populate left image preview menu"""
        self.thumbnail_list.clear()
        for i, img_path in enumerate(self.image_files):
            try:
                pil_img = Image.open(img_path)
                pil_img.thumbnail((THUMBNAIL_SIZE.width(), THUMBNAIL_SIZE.height()), Image.Resampling.NEAREST)
                qimage = ImageQt.toqimage(pil_img)
                pixmap = QPixmap.fromImage(qimage)

                item = QListWidgetItem(QIcon(pixmap), f"{os.path.basename(img_path)}\n第 {i+1} 页")
                self.thumbnail_list.addItem(item)
            except Exception as e:
                print(f"Failed to load thumbnail {img_path}: {e}")
                item = QListWidgetItem(f"{os.path.basename(img_path)}\n页 {i+1}\n(加载失败)")
                self.thumbnail_list.addItem(item)

    def load_image_by_index(self, index):
        """Load image by index, and handle save/load logic for page switching"""
        if not self.image_files:
            return

        if self.current_image_index != -1 and self.inpaint_image_path:
            self._save_current_page_data()

        self.current_image_index = index
        self.inpaint_image_path = self.image_files[self.current_image_index]
        base_filename = os.path.basename(self.inpaint_image_path)
        self.original_image_path = os.path.join(self.current_folder, base_filename)

        self.text_boxes = []
        if self.inpaint_image_path in self.page_data:
            for tb_dict in self.page_data[self.inpaint_image_path]:
                self.text_boxes.append(TextBox.from_dict(tb_dict))
        
        self.selected_text_boxes = []
        self._update_text_box_ui()

        self.image_canvas.zoom_level = 1.0 # Reset zoom
        self.image_canvas.offset = QPointF(0, 0) # Reset pan

        try:
            self.current_base_inpaint_img = Image.open(self.inpaint_image_path).convert("RGBA")
            if os.path.exists(self.original_image_path):
                self.current_base_original_img = Image.open(self.original_image_path).convert("RGBA")
                if self.current_base_original_img.size != self.current_base_inpaint_img.size:
                    self.current_base_original_img = self.current_base_original_img.resize(
                        self.current_base_inpaint_img.size, Image.Resampling.LANCZOS)
            else:
                self.current_base_original_img = None
        except Exception as e:
            QMessageBox.critical(self, "Image Load Error", f"Failed to load image: {self.inpaint_image_path}\nError: {e}")
            self.current_base_inpaint_img = None
            self.current_base_original_img = None
            self.image_canvas.clear_image()
            return

        self.setWindowTitle(f"轻量漫画嵌字工具 (PySide6) - {base_filename}")
        self.update_image_display()

    def _save_current_page_data(self):
        """Save current page's text box data to in-memory page_data and to file"""
        if self.inpaint_image_path:
            self.page_data[self.inpaint_image_path] = [tb.to_dict() for tb in self.text_boxes]
            self._save_all_page_data_to_file()

    def _load_all_page_data(self):
        """Load all page's text box data from file"""
        page_data_path = os.path.join(self.current_folder, PAGE_DATA_FILE)
        if os.path.exists(page_data_path):
            try:
                with open(page_data_path, 'r', encoding='utf-8') as f:
                    self.page_data = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Warning", "Page data file corrupted, reset.")
                self.page_data = {}
        else:
            self.page_data = {}

    def _save_all_page_data_to_file(self):
        """Save all in-memory page data to file"""
        if self.current_folder:
            page_data_path = os.path.join(self.current_folder, PAGE_DATA_FILE)
            with open(page_data_path, 'w', encoding='utf-8') as f:
                json.dump(self.page_data, f, ensure_ascii=False, indent=4)

    def _on_closing(self):
        """Handle window closing event, save current page data and exit"""
        if self.current_folder and self.inpaint_image_path:
            self._save_current_page_data()
        self.close() # Close the QMainWindow

    def update_image_display(self):
        """
        Update canvas display based on current image, original image transparency, and text boxes.
        Composes the final image with text and transparency, then passes it to the canvas.
        """
        if not self.current_base_inpaint_img:
            self.image_canvas.clear_image()
            return

        # 1. Start with the inpaint image
        # Convert PIL image to QImage for drawing with QPainter
        # Ensure it's RGBA for transparency handling
        base_qimage = ImageQt.toqimage(self.current_base_inpaint_img).convertToFormat(QImage.Format_RGBA8888)
        
        painter = QPainter(base_qimage)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 2. Blend original image with transparency if available
        if self.current_base_original_img:
            original_qimage = ImageQt.toqimage(self.current_base_original_img).convertToFormat(QImage.Format_RGBA8888)
            
            # Set painter opacity for blending
            painter.setOpacity(self.original_image_alpha)
            painter.drawPixmap(0, 0, QPixmap.fromImage(original_qimage))
            painter.setOpacity(1.0) # Reset opacity for drawing text

        # 3. Draw all text boxes onto the QImage
        # Pass the current text boxes and selected text boxes to the canvas
        # This ensures the canvas has the latest list of text boxes for selection drawing
        self.image_canvas.text_boxes = self.text_boxes
        self.image_canvas.selected_text_boxes = self.selected_text_boxes

        for tb in self.text_boxes:
            # Calculate bounding box for each text box (needed for selection and transformations)
            # This needs to be done on a painter that is not affected by current canvas zoom/pan,
            # so the painter on base_qimage is perfect for this.
            tb.calculate_bbox(painter)
            tb.draw(painter) # Draw the text box with its properties

        painter.end() # End painting on the QImage

        # 4. Pass the final composed QImage (as QPixmap) to the ImageCanvas
        self.image_canvas.set_image(QPixmap.fromImage(base_qimage))

    def _update_text_box_ui(self):
        """Update right control panel to display properties of selected text box"""
        if self.selected_text_boxes:
            first_selected = self.selected_text_boxes[0]
            self.text_entry.setText(first_selected.text)
            self.font_family_combobox.setCurrentText(first_selected.font_family)
            self.font_size_spinbox.setValue(first_selected.font_size)
            self.current_text_color = first_selected.color
            self.color_preview.setStyleSheet(f"background-color: {self.current_text_color.name()}; border: 1px solid gray;")
            self.text_direction_combobox.setCurrentText("竖排" if first_selected.is_vertical else "横排")
            self.stroke_width_spinbox.setValue(first_selected.stroke_width)
            self.current_stroke_color = first_selected.stroke_color
            self.stroke_color_preview.setStyleSheet(f"background-color: {self.current_stroke_color.name()}; border: 1px solid gray;")
            self.shadow_offset_x_spinbox.setValue(first_selected.shadow_offset_x)
            self.shadow_offset_y_spinbox.setValue(first_selected.shadow_offset_y)
            self.current_shadow_color = first_selected.shadow_color
            self.shadow_color_preview.setStyleSheet(f"background-color: {self.current_shadow_color.name()}; border: 1px solid gray;")
            self.line_spacing_spinbox.setValue(first_selected.line_spacing)
            self.rotation_spinbox.setValue(first_selected.rotation)
            self.scale_x_spinbox.setValue(first_selected.scale_x)
            self.scale_y_spinbox.setValue(first_selected.scale_y)
        else:
            self.text_entry.clear()
            # Ensure these are set to actual defaults, not just DEFAULT_FONT constant
            # as DEFAULT_FONT might not be in system_fonts if it was a fallback.
            # Use the actual font_family_var determined by _load_system_fonts.
            self.font_family_combobox.setCurrentText(self.font_family_var) 
            self.font_size_spinbox.setValue(DEFAULT_FONT_SIZE)
            self.current_text_color = QColor(DEFAULT_TEXT_COLOR)
            self.color_preview.setStyleSheet(f"background-color: {DEFAULT_TEXT_COLOR}; border: 1px solid gray;")
            self.text_direction_combobox.setCurrentText("横排")
            self.stroke_width_spinbox.setValue(0)
            self.current_stroke_color = QColor("#FFFFFF")
            self.stroke_color_preview.setStyleSheet(f"background-color: #FFFFFF; border: 1px solid gray;")
            self.shadow_offset_x_spinbox.setValue(0)
            self.shadow_offset_y_spinbox.setValue(0)
            self.current_shadow_color = QColor("#000000")
            self.shadow_color_preview.setStyleSheet(f"background-color: #000000; border: 1px solid gray;")
            self.line_spacing_spinbox.setValue(0)
            self.rotation_spinbox.setValue(0)
            self.scale_x_spinbox.setValue(1.0)
            self.scale_y_spinbox.setValue(1.0)

    def add_text_box(self, x_original=None, y_original=None):
        """Add a new text box at the center of the image or at a specified position"""
        if not self.current_base_inpaint_img:
            QMessageBox.warning(self.centralWidget(), "Warning", "Please open a manga folder first.") 
            return

        img_width, img_height = self.current_base_inpaint_img.size

        # Ensure the text entry has a default value if empty, before creating the new text box
        if not self.text_entry.toPlainText().strip():
            self.text_entry.setText("新文本框")

        if x_original is None or y_original is None:
            new_x = img_width // 4
            new_y = img_height // 4
        else:
            new_x = x_original
            new_y = y_original

        new_text_box = TextBox(new_x, new_y,
                               text=self.text_entry.toPlainText(), # Use the updated text_entry content
                               font_family=self.font_family_combobox.currentText(),
                               font_size=self.font_size_spinbox.value(),
                               color=self.current_text_color.name(),
                               is_vertical=(self.text_direction_combobox.currentText() == "竖排"),
                               stroke_width=self.stroke_width_spinbox.value(),
                               stroke_color=self.current_stroke_color.name(),
                               shadow_offset_x=self.shadow_offset_x_spinbox.value(),
                               shadow_offset_y=self.shadow_offset_y_spinbox.value(),
                               shadow_color=self.current_shadow_color.name(),
                               line_spacing=self.line_spacing_spinbox.value(),
                               rotation=self.rotation_spinbox.value(),
                               scale_x=self.scale_x_spinbox.value(),
                               scale_y=self.scale_y_spinbox.value())
        self.text_boxes.append(new_text_box)
        self.selected_text_boxes = [new_text_box]
        self._update_text_box_ui()
        self.update_image_display()

    def apply_format_to_selected(self):
        """Apply format from right panel to all selected text boxes"""
        if self.selected_text_boxes:
            for tb in self.selected_text_boxes:
                tb.text = self.text_entry.toPlainText()
                tb.font_family = self.font_family_combobox.currentText()
                tb.font_size = self.font_size_spinbox.value()
                tb.color = self.current_text_color
                tb.is_vertical = (self.text_direction_combobox.currentText() == "竖排")
                tb.stroke_width = self.stroke_width_spinbox.value()
                tb.stroke_color = self.current_stroke_color
                tb.shadow_offset_x = self.shadow_offset_x_spinbox.value()
                tb.shadow_offset_y = self.shadow_offset_y_spinbox.value()
                tb.shadow_color = self.current_shadow_color
                tb.line_spacing = self.line_spacing_spinbox.value()
                tb.rotation = self.rotation_spinbox.value()
                tb.scale_x = self.scale_x_spinbox.value()
                tb.scale_y = self.scale_y_spinbox.value()
            self.update_image_display()
        else:
            QMessageBox.warning(self.centralWidget(), "Warning", "No text box selected.") 

    def _show_context_menu(self, global_pos: QPoint, click_x_original, click_y_original):
        """Display right-click context menu"""
        menu = QMenu(self)
        
        clicked_on_textbox = False
        for tb in self.text_boxes:
            if tb.is_point_in_bbox(click_x_original, click_y_original):
                clicked_on_textbox = True
                break

        if clicked_on_textbox:
            menu.addAction("删除选中文本框", self.delete_selected_text_box)
            menu.addAction("置于顶层", self.bring_to_front)
            menu.addAction("置于底层", self.send_to_back)
        else:
            menu.addAction("在此处添加文本框", lambda: self.add_text_box(click_x_original, click_y_original))
        
        menu.exec_(global_pos)

    def delete_selected_text_box(self):
        """Delete all currently selected text boxes"""
        if self.selected_text_boxes:
            self.text_boxes = [tb for tb in self.text_boxes if tb not in self.selected_text_boxes]
            self.selected_text_boxes = []
            self._update_text_box_ui()
            self.update_image_display()
        else:
            QMessageBox.warning(self.centralWidget(), "Warning", "No text box selected.") 

    def bring_to_front(self):
        """Bring selected text box to front"""
        if self.selected_text_boxes:
            for tb in self.selected_text_boxes:
                if tb in self.text_boxes:
                    self.text_boxes.remove(tb)
                    self.text_boxes.append(tb)
            self.update_image_display()

    def send_to_back(self):
        """Send selected text box to back"""
        if self.selected_text_boxes:
            for tb in self.selected_text_boxes:
                if tb in self.text_boxes:
                    self.text_boxes.remove(tb)
                    self.text_boxes.insert(0, tb)
            self.update_image_display()

    def save_typeset_image(self):
        """Render current image and all text boxes and save to qianresult folder"""
        if not self.current_base_inpaint_img:
            QMessageBox.warning(self.centralWidget(), "Warning", "No image to save. Please open a manga folder first.") 
            return

        try:
            # Create a QImage from the inpaint image
            final_qimage = ImageQt.toqimage(self.current_base_inpaint_img).convertToFormat(QImage.Format_RGBA8888)
            painter = QPainter(final_qimage)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)

            # Blend original image with transparency if available
            if self.current_base_original_img:
                original_qimage = ImageQt.toqimage(self.current_base_original_img).convertToFormat(QImage.Format_RGBA8888)
                painter.setOpacity(self.original_image_alpha)
                painter.drawPixmap(0, 0, QPixmap.fromImage(original_qimage))
                painter.setOpacity(1.0) # Reset opacity

            # Draw all text boxes onto the QImage
            for tb in self.text_boxes:
                # Calculate bbox for accurate drawing (already done in update_image_display, but safe to re-do)
                tb.calculate_bbox(painter) 
                tb.draw(painter)
            painter.end()

            # Convert QImage back to PIL Image for saving
            final_img_pil_with_text = ImageQt.fromqimage(final_qimage)

            base_filename = os.path.basename(self.inpaint_image_path)
            name, ext = os.path.splitext(base_filename)
            save_filename = f"{name}_typeset{ext}"
            save_path = os.path.join(self.current_folder, QIANRESULT_FOLDER, save_filename)

            final_img_pil_with_text.save(save_path)
            QMessageBox.information(self.centralWidget(), "Save Successful", f"Typeset image saved to:\n{save_path}") 
        except Exception as e:
            QMessageBox.critical(self.centralWidget(), "Save Failed", f"Error saving typeset image: {e}") 

    def toggle_fullscreen(self): 
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_button.setText("全屏")
        else:
            self.showFullScreen()
            self.fullscreen_button.setText("退出全屏")

    def undo(self):
        QMessageBox.information(self.centralWidget(), "Feature Hint", "Undo feature to be implemented.") 

    def redo(self):
        QMessageBox.information(self.centralWidget(), "Feature Hint", "Redo feature to be implemented.") 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MangaTypesetterApp()
    window.show()
    sys.exit(app.exec())
