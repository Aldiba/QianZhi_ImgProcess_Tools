
# image_canvas.py
import cairo
import os
from PyQt5.QtWidgets import QWidget, QMessageBox, QApplication
from PyQt5.QtGui import QPixmap, QImage, QPainter, QMouseEvent, QWheelEvent, QCursor
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QTimer
from text_box import TextBox
from utils import pil_to_qimage, qimage_to_pil, get_font_path

class ImageCanvas(QWidget):
    # 定义信号
    text_box_added = pyqtSignal(TextBox)
    selection_changed = pyqtSignal(list) # 发送当前选中的文本框列表
    text_box_updated = pyqtSignal() # 文本框移动、大小改变时触发

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True) # 启用鼠标跟踪，用于显示鼠标样式

        self.inpaint_image = None  # 去字后的图片 (QImage)
        self.original_image = None # 原始图片 (QImage)
        self.original_image_opacity = 0.5 # 默认透明度 0.0 - 1.0

        self.text_boxes = [] # 当前页面上的所有 TextBox 对象
        self.selected_text_boxes = [] # 当前选中的 TextBox 对象列表

        self.current_mode = "select" # "select", "drag", "resize", "rotate", "draw_text_box"
        self.drag_start_pos = QPoint()
        self.drag_offset = QPoint() # 拖动时的偏移量
        self.resizing_handle = None # 拖动大小的句柄 (e.g., "top_left")
        self.rotating_center = QPoint() # 旋转中心
        self.rotation_start_angle = 0 # 旋转开始角度
        self.rotation_start_value = 0 # 旋转开始时的文本框旋转值

        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 用于双击创建文本框的计时器
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self._single_click_action)
        self.last_click_pos = QPoint()

    def load_images(self, inpaint_path, original_path):
        """加载去字图和原图"""
        try:
            self.inpaint_image = QImage(inpaint_path)
            self.original_image = QImage(original_path)
            if self.inpaint_image.isNull() or self.original_image.isNull():
                raise ValueError("无法加载图片，路径可能不正确或图片损坏。")
            self.update() # 强制重绘
        except Exception as e:
            QMessageBox.critical(self, "图片加载错误", f"加载图片时发生错误: {e}")
            self.inpaint_image = None
            self.original_image = None

    def set_original_image_opacity(self, value):
        """设置原图透明度 (0-100)"""
        self.original_image_opacity = value / 100.0
        self.update()

    def set_text_boxes(self, text_boxes):
        """设置当前页面显示的文本框列表"""
        self.text_boxes = text_boxes
        self.selected_text_boxes = []
        self.update()

    def paintEvent(self, event):
        """绘制事件，负责所有绘图操作"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if not self.inpaint_image:
            painter.drawText(self.rect(), Qt.AlignCenter, "请打开漫画文件夹")
            return

        # 计算图片在画布上的显示区域
        img_width = self.inpaint_image.width() * self.zoom_factor
        img_height = self.inpaint_image.height() * self.zoom_factor

        # 居中显示图片
        display_x = (self.width() - img_width) / 2 + self.offset_x
        display_y = (self.height() - img_height) / 2 + self.offset_y
        display_rect = QRect(int(display_x), int(display_y), int(img_width), int(img_height))

        # 绘制去字后的图片
        painter.drawImage(display_rect, self.inpaint_image)

        # 绘制原始图片（作为透明参考）
        if self.original_image and self.original_image_opacity > 0:
            painter.setOpacity(self.original_image_opacity)
            painter.drawImage(display_rect, self.original_image)
            painter.setOpacity(1.0) # 恢复不透明度

        # 将QPainter的绘图上下文转换为PyCairo上下文
        # 这种方法允许PyCairo在QImage上绘制，然后QImage再由QPainter绘制到QWidget
        # 或者直接在QPainter的设备上获取PyCairo上下文
        # 考虑到性能和兼容性，直接在QPainter上操作可能更直接，但PyCairo的文本渲染更强大
        # 这里我们创建一个临时的QImage，用Cairo绘制，再用QPainter绘制这个QImage
        if self.inpaint_image:
            # 创建一个与inpaint_image相同大小的QImage用于Cairo绘制文本
            # 确保QImage格式兼容Cairo
            temp_image = QImage(self.inpaint_image.size(), QImage.Format_ARGB32_Premultiplied)
            temp_image.fill(Qt.transparent) # 填充透明

            # 获取Cairo上下文
            # Cairo需要一个PyQt5的QImage对象，并且格式必须是Format_ARGB32_Premultiplied
            cairo_surface = cairo.ImageSurface.create_for_data(
                temp_image.bits().as_buffer(temp_image.byteCount()),
                cairo.FORMAT_ARGB32,
                temp_image.width(),
                temp_image.height(),
                temp_image.bytesPerLine()
            )
            ctx = cairo.Context(cairo_surface)

            # 缩放和偏移Cairo上下文以匹配图片显示
            ctx.translate(-display_x / self.zoom_factor, -display_y / self.zoom_factor)
            ctx.scale(1.0 / self.zoom_factor, 1.0 / self.zoom_factor)

            # 绘制所有文本框
            for tb in self.text_boxes:
                # 仅在选中或拖动时绘制边框和控制点
                draw_handles = tb in self.selected_text_boxes or \
                               (self.current_mode in ["drag", "resize", "rotate"] and self.selected_text_boxes and tb == self.selected_text_boxes[0])
                tb.draw(ctx, draw_handles=draw_handles)

            # 将Cairo绘制的QImage绘制到QPainter上
            painter.drawImage(display_rect, temp_image)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        self.drag_start_pos = event.pos()
        self.last_click_pos = event.pos() # 记录单击位置

        # 将鼠标位置转换为图片坐标系
        img_width = self.inpaint_image.width() * self.zoom_factor
        img_height = self.inpaint_image.height() * self.zoom_factor
        display_x = (self.width() - img_width) / 2 + self.offset_x
        display_y = (self.height() - img_height) / 2 + self.offset_y

        # 转换鼠标点击的屏幕坐标到图片内容坐标
        mouse_x_img = (event.x() - display_x) / self.zoom_factor
        mouse_y_img = (event.y() - display_y) / self.zoom_factor
        mouse_point_img = QPoint(int(mouse_x_img), int(mouse_y_img))

        if event.button() == Qt.LeftButton:
            # 检查是否点击了文本框的控制点
            self.resizing_handle = None
            self.current_mode = "select" # 默认选择模式

            # 优先检查拖动大小/旋转句柄
            for tb in self.selected_text_boxes:
                handle = tb.get_handle_at_point(mouse_point_img, self.zoom_factor)
                if handle:
                    if handle == "rotate":
                        self.current_mode = "rotate"
                        self.rotating_center = tb.center_point()
                        # 计算鼠标点击相对于中心的初始角度
                        dx = mouse_point_img.x() - self.rotating_center.x()
                        dy = mouse_point_img.y() - self.rotating_center.y()
                        self.rotation_start_angle = (180 / 3.14159) * cairo.Context.atan2(dy, dx)
                        self.rotation_start_value = tb.rotation
                    else:
                        self.current_mode = "resize"
                        self.resizing_handle = handle
                    self.drag_offset = mouse_point_img - tb.pos() # 记录偏移用于精确调整
                    return # 找到句柄，退出循环

            # 检查是否点击了文本框本身
            clicked_on_text_box = False
            newly_selected_tb = None
            for tb in reversed(self.text_boxes): # 从上层开始检查
                if tb.contains_point(mouse_point_img):
                    clicked_on_text_box = True
                    newly_selected_tb = tb
                    break

            if clicked_on_text_box:
                if event.modifiers() == Qt.ShiftModifier:
                    # Shift + 点击：多选/取消选择
                    if newly_selected_tb in self.selected_text_boxes:
                        self.selected_text_boxes.remove(newly_selected_tb)
                    else:
                        self.selected_text_boxes.append(newly_selected_tb)
                else:
                    # 单击：如果已选中，则进入拖动模式；否则，选中并进入拖动模式
                    if newly_selected_tb not in self.selected_text_boxes:
                        self.selected_text_boxes = [newly_selected_tb]
                    self.current_mode = "drag"
                    # 记录所有选中文本框的初始偏移量
                    self.drag_offset = mouse_point_img - newly_selected_tb.pos()
                    for tb in self.selected_text_boxes:
                        tb._drag_start_pos = tb.pos() # 记录每个文本框的初始位置
            else:
                # 点击空白处：取消所有选中
                self.selected_text_boxes = []
                self.current_mode = "select"

            self.selection_changed.emit(self.selected_text_boxes)
            self.update()

        elif event.button() == Qt.RightButton:
            # 右键菜单由 contextMenuEvent 处理
            pass

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if not self.inpaint_image:
            return

        # 将鼠标位置转换为图片坐标系
        img_width = self.inpaint_image.width() * self.zoom_factor
        img_height = self.inpaint_image.height() * self.zoom_factor
        display_x = (self.width() - img_width) / 2 + self.offset_x
        display_y = (self.height() - img_height) / 2 + self.offset_y

        mouse_x_img = (event.x() - display_x) / self.zoom_factor
        mouse_y_img = (event.y() - display_y) / self.zoom_factor
        mouse_point_img = QPoint(int(mouse_x_img), int(mouse_y_img))

        if self.current_mode == "drag" and self.selected_text_boxes:
            # 拖动选中文本框
            delta_x = mouse_point_img.x() - self.drag_offset.x()
            delta_y = mouse_point_img.y() - self.drag_offset.y()

            # 移动所有选中的文本框
            for tb in self.selected_text_boxes:
                tb.set_pos(tb._drag_start_pos.x() + delta_x, tb._drag_start_pos.y() + delta_y)
            self.update()

        elif self.current_mode == "resize" and self.selected_text_boxes and self.resizing_handle:
            # 调整大小
            tb = self.selected_text_boxes[0] # 只调整第一个选中的文本框
            tb.resize_from_handle(mouse_point_img, self.resizing_handle, self.zoom_factor)
            self.update()

        elif self.current_mode == "rotate" and self.selected_text_boxes:
            # 旋转
            tb = self.selected_text_boxes[0]
            dx = mouse_point_img.x() - self.rotating_center.x()
            dy = mouse_point_img.y() - self.rotating_center.y()
            current_angle = (180 / 3.14159) * cairo.Context.atan2(dy, dx)
            rotation_delta = current_angle - self.rotation_start_angle
            tb.rotation = (self.rotation_start_value + rotation_delta) % 360
            self.update()

        else:
            # 鼠标样式反馈
            cursor = Qt.ArrowCursor
            for tb in self.text_boxes:
                handle = tb.get_handle_at_point(mouse_point_img, self.zoom_factor)
                if handle == "top_left": cursor = Qt.SizeFDiagCursor
                elif handle == "top_right": cursor = Qt.SizeBDiagCursor
                elif handle == "bottom_left": cursor = Qt.SizeBDiagCursor
                elif handle == "bottom_right": cursor = Qt.SizeFDiagCursor
                elif handle == "rotate": cursor = Qt.PointingHandCursor # 旋转图标
                elif tb.contains_point(mouse_point_img): cursor = Qt.SizeAllCursor # 移动图标
                if cursor != Qt.ArrowCursor:
                    break
            self.setCursor(cursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if self.current_mode in ["drag", "resize", "rotate"] and self.selected_text_boxes:
            self.text_box_updated.emit() # 文本框状态改变，通知主窗口保存历史
        self.current_mode = "select"
        self.resizing_handle = None
        self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """鼠标双击事件：创建新文本框"""
        if event.button() == Qt.LeftButton:
            # 将鼠标位置转换为图片坐标系
            img_width = self.inpaint_image.width() * self.zoom_factor
            img_height = self.inpaint_image.height() * self.zoom_factor
            display_x = (self.width() - img_width) / 2 + self.offset_x
            display_y = (self.height() - img_height) / 2 + self.offset_y

            mouse_x_img = (event.x() - display_x) / self.zoom_factor
            mouse_y_img = (event.y() - display_y) / self.zoom_factor

            # 创建一个新的文本框，默认大小和位置
            new_text_box = TextBox(
                x=int(mouse_x_img - 50), # 默认居中于点击位置
                y=int(mouse_y_img - 20),
                width=100,
                height=40,
                text="新文本",
                font_name="SimHei", # 默认字体
                font_size=20,
                color=(0, 0, 0, 1)
            )
            self.text_boxes.append(new_text_box)
            self.selected_text_boxes = [new_text_box]
            self.text_box_added.emit(new_text_box) # 发出信号通知主窗口
            self.selection_changed.emit(self.selected_text_boxes)
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件：缩放和平移"""
        delta = event.angleDelta().y() / 120 # 滚轮步长

        if event.modifiers() == Qt.ShiftModifier:
            # Shift + 滚轮：缩放
            old_zoom_factor = self.zoom_factor
            if delta > 0:
                self.zoom_factor *= 1.1 # 放大
            else:
                self.zoom_factor /= 1.1 # 缩小

            # 保持缩放中心在鼠标位置
            # mouse_pos_in_canvas = event.pos()
            # mouse_pos_in_image = QPoint(
            #     (mouse_pos_in_canvas.x() - self.offset_x - (self.width() - self.inpaint_image.width() * old_zoom_factor) / 2) / old_zoom_factor,
            #     (mouse_pos_in_canvas.y() - self.offset_y - (self.height() - self.inpaint_image.height() * old_zoom_factor) / 2) / old_zoom_factor
            # )
            # self.offset_x -= mouse_pos_in_image.x() * (self.zoom_factor - old_zoom_factor)
            # self.offset_y -= mouse_pos_in_image.y() * (self.zoom_factor - old_zoom_factor)

        elif event.modifiers() == Qt.ControlModifier:
            # Ctrl + 滚轮：左右平移
            self.offset_x += delta * 10 # 调整平移速度
        else:
            # 滚轮：上下平移
            self.offset_y += delta * 10 # 调整平移速度

        self.update()

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QApplication.instance().menu_context_text_box # 从 QApplication 获取全局菜单
        if not menu:
            # 如果没有全局菜单，则创建局部菜单
            menu = self.create_local_context_menu()

        # 将鼠标位置转换为图片坐标系
        img_width = self.inpaint_image.width() * self.zoom_factor
        img_height = self.inpaint_image.height() * self.zoom_factor
        display_x = (self.width() - img_width) / 2 + self.offset_x
        display_y = (self.height() - img_height) / 2 + self.offset_y

        mouse_x_img = (pos.x() - display_x) / self.zoom_factor
        mouse_y_img = (pos.y() - display_y) / self.zoom_factor
        mouse_point_img = QPoint(int(mouse_x_img), int(mouse_y_img))

        clicked_tb = None
        for tb in reversed(self.text_boxes):
            if tb.contains_point(mouse_point_img):
                clicked_tb = tb
                break

        if clicked_tb:
            # 如果右键点击在文本框上，确保它被选中
            if clicked_tb not in self.selected_text_boxes:
                self.selected_text_boxes = [clicked_tb]
                self.selection_changed.emit(self.selected_text_boxes)
                self.update()

            # 启用/禁用菜单项
            for action in menu.actions():
                if action.text() == "删除文本框":
                    action.setEnabled(True)
                elif action.text() == "复制文本框":
                    action.setEnabled(True)
                elif action.text() == "粘贴文本框":
                    # 只有当剪贴板有文本框数据时才启用
                    action.setEnabled(QApplication.instance().clipboard_text_box_data is not None)
        else:
            # 如果右键点击在空白处，禁用删除和复制，启用粘贴（如果剪贴板有数据）
            for action in menu.actions():
                if action.text() == "删除文本框" or action.text() == "复制文本框":
                    action.setEnabled(False)
                elif action.text() == "粘贴文本框":
                    action.setEnabled(QApplication.instance().clipboard_text_box_data is not None)

        menu.exec_(self.mapToGlobal(pos))

    def create_local_context_menu(self):
        """创建右键菜单（如果全局菜单不存在）"""
        menu = QWidget.createStandardContextMenu(self) # 使用Qt的默认上下文菜单

        # 添加自定义动作
        add_action = menu.addAction("添加新文本框")
        add_action.triggered.connect(lambda: self._add_text_box_at_mouse_pos(self.last_click_pos)) # 使用上次点击位置

        delete_action = menu.addAction("删除文本框")
        delete_action.triggered.connect(self._delete_selected_text_boxes)

        copy_action = menu.addAction("复制文本框")
        copy_action.triggered.connect(self._copy_selected_text_boxes)

        paste_action = menu.addAction("粘贴文本框")
        paste_action.triggered.connect(lambda: self._paste_text_box(self.last_click_pos))

        # 将此菜单存储在 QApplication 实例中，以便其他地方可以访问和修改
        QApplication.instance().menu_context_text_box = menu
        return menu

    def _add_text_box_at_mouse_pos(self, canvas_pos):
        """在指定画布位置添加新文本框"""
        # 将画布位置转换为图片坐标系
        img_width = self.inpaint_image.width() * self.zoom_factor
        img_height = self.inpaint_image.height() * self.zoom_factor
        display_x = (self.width() - img_width) / 2 + self.offset_x
        display_y = (self.height() - img_height) / 2 + self.offset_y

        mouse_x_img = (canvas_pos.x() - display_x) / self.zoom_factor
        mouse_y_img = (canvas_pos.y() - display_y) / self.zoom_factor

        new_text_box = TextBox(
            x=int(mouse_x_img - 50),
            y=int(mouse_y_img - 20),
            width=100,
            height=40,
            text="新文本",
            font_name="SimHei",
            font_size=20,
            color=(0, 0, 0, 1)
        )
        self.text_boxes.append(new_text_box)
        self.selected_text_boxes = [new_text_box]
        self.text_box_added.emit(new_text_box)
        self.selection_changed.emit(self.selected_text_boxes)
        self.update()

    def _delete_selected_text_boxes(self):
        """删除所有选中的文本框"""
        if QMessageBox.question(self, "确认删除", "确定要删除选中的文本框吗？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            for tb in self.selected_text_boxes:
                if tb in self.text_boxes:
                    self.text_boxes.remove(tb)
            self.selected_text_boxes = []
            self.selection_changed.emit(self.selected_text_boxes)
            self.text_box_updated.emit() # 状态改变，通知主窗口保存历史
            self.update()

    def _copy_selected_text_boxes(self):
        """复制选中的文本框数据到剪贴板"""
        if self.selected_text_boxes:
            # 复制第一个选中的文本框
            QApplication.instance().clipboard_text_box_data = self.selected_text_boxes[0].to_dict()
            QMessageBox.information(self, "复制成功", "文本框已复制。")
        else:
            QMessageBox.warning(self, "无选中", "请选择要复制的文本框。")

    def _paste_text_box(self, canvas_pos):
        """从剪贴板粘贴文本框"""
        clipboard_data = QApplication.instance().clipboard_text_box_data
        if clipboard_data:
            new_tb = TextBox.from_dict(clipboard_data)

            # 将粘贴位置设置为鼠标右键点击的位置，并稍微偏移
            img_width = self.inpaint_image.width() * self.zoom_factor
            img_height = self.inpaint_image.height() * self.zoom_factor
            display_x = (self.width() - img_width) / 2 + self.offset_x
            display_y = (self.height() - img_height) / 2 + self.offset_y

            paste_x_img = (canvas_pos.x() - display_x) / self.zoom_factor
            paste_y_img = (canvas_pos.y() - display_y) / self.zoom_factor

            new_tb.x = int(paste_x_img + 10) # 稍微偏移，避免完全重叠
            new_tb.y = int(paste_y_img + 10)
            self.text_boxes.append(new_tb)
            self.selected_text_boxes = [new_tb]
            self.text_box_added.emit(new_tb) # 视为新增，触发历史保存
            self.selection_changed.emit(self.selected_text_boxes)
            self.update()
        else:
            QMessageBox.warning(self, "无数据", "剪贴板中没有可粘贴的文本框数据。")

    def save_rendered_image(self, output_path, text_boxes_to_render):
        """将当前画布内容（图片+文本）渲染并保存为图片文件"""
        if not self.inpaint_image:
            raise ValueError("没有加载图片，无法保存。")

        # 创建一个与inpaint_image相同大小的QImage用于Cairo绘制
        # 确保QImage格式兼容Cairo
        final_image = QImage(self.inpaint_image.size(), QImage.Format_ARGB32_Premultiplied)
        final_image.fill(Qt.white) # 填充白色背景或使用inpaint_image作为底图

        painter = QPainter(final_image)
        painter.drawImage(0, 0, self.inpaint_image) # 绘制去字后的图片作为底图

        # 将QPainter的绘图上下文转换为PyCairo上下文
        cairo_surface = cairo.ImageSurface.create_for_data(
            final_image.bits().as_buffer(final_image.byteCount()),
            cairo.FORMAT_ARGB32,
            final_image.width(),
            final_image.height(),
            final_image.bytesPerLine()
        )
        ctx = cairo.Context(cairo_surface)

        # 绘制所有文本框，不绘制句柄和边框
        for tb in text_boxes_to_render:
            tb.draw(ctx, draw_handles=False)

        # 将QImage保存为文件
        # PyQt5的QImage可以直接保存为多种格式
        final_image.save(output_path)

    def _single_click_action(self):
        """处理单击事件（如果不是双击）"""
        # 如果计时器到期，说明是单击，可以在这里处理单击逻辑
        # 例如，如果点击空白处，取消所有选择
        pass

