# main.py
import sys
import os
import shutil
import cairo
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QPushButton, QFileDialog, QMessageBox, QSizePolicy, QAction,
    QShortcut
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QKeySequence

# 导入自定义模块
from image_canvas import ImageCanvas
from ui_panels import TextPropertiesPanel, ThumbnailPanel
from history_manager import HistoryManager
from text_box import TextBox
from utils import get_system_fonts, load_image_paths, create_required_dirs, save_image_with_text

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("轻量化漫画嵌字软件")
        self.setGeometry(100, 100, 1200, 800) # 初始窗口大小

        self.current_dir = None
        self.original_image_paths = []
        self.inpaint_image_paths = []
        self.current_page_index = -1
        self.text_boxes = [] # 当前页的所有文本框
        self.selected_text_boxes = []

        self.history_manager = HistoryManager()

        self._init_ui()
        self._init_shortcuts()

    def _init_ui(self):
        # 创建中央小部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左侧面板：缩略图预览 ---
        self.thumbnail_panel = ThumbnailPanel()
        self.thumbnail_panel.setFixedWidth(150) # 固定宽度
        self.thumbnail_panel.thumbnail_clicked.connect(self._switch_page_from_thumbnail)
        main_layout.addWidget(self.thumbnail_panel)

        # --- 中间区域：图片画布和底部滑块 ---
        center_layout = QVBoxLayout()
        self.image_canvas = ImageCanvas()
        self.image_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # 允许扩展
        self.image_canvas.text_box_added.connect(self._add_text_box_to_canvas)
        self.image_canvas.selection_changed.connect(self._update_selected_text_boxes)
        self.image_canvas.text_box_updated.connect(self._on_text_box_updated)
        center_layout.addWidget(self.image_canvas)

        # 底部透明度滑块
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50) # 默认50%透明度
        self.opacity_slider.setToolTip("调整原图透明度")
        self.opacity_slider.valueChanged.connect(self.image_canvas.set_original_image_opacity)
        center_layout.addWidget(self.opacity_slider)
        main_layout.addLayout(center_layout)

        # --- 右侧面板：文字属性设置 ---
        self.text_properties_panel = TextPropertiesPanel(get_system_fonts())
        self.text_properties_panel.setFixedWidth(250) # 固定宽度
        self.text_properties_panel.apply_format_to_selection.connect(self._apply_format_to_selected_text_boxes)
        main_layout.addWidget(self.text_properties_panel)

        # --- 菜单栏 ---
        self._create_menu_bar()

        # 初始禁用UI元素，直到文件夹打开
        self._set_ui_enabled(False)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        open_folder_action = QAction("打开文件夹...", self)
        open_folder_action.triggered.connect(self._open_folder)
        file_menu.addAction(open_folder_action)

        save_action = QAction("保存当前页", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_current_page)
        file_menu.addAction(save_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

    def _init_shortcuts(self):
        # Ctrl+Z 和 Ctrl+Y 已经在菜单栏中设置了快捷键
        pass

    def _set_ui_enabled(self, enabled):
        """根据是否加载了文件夹来启用/禁用UI元素"""
        self.thumbnail_panel.setEnabled(enabled)
        self.image_canvas.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)
        self.text_properties_panel.setEnabled(enabled)
        # 菜单栏的保存、撤销、重做也应受控，但这里简化处理

    def _open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择漫画文件夹")
        if folder_path:
            self.current_dir = folder_path
            QMessageBox.information(self, "文件夹已选择", f"已选择文件夹: {self.current_dir}")
            self._load_manga_folder(folder_path)
            self._set_ui_enabled(True)

    def _load_manga_folder(self, folder_path):
        """加载漫画文件夹，处理inpaint和qianresult目录"""
        try:
            self.original_image_paths = load_image_paths(folder_path)
            if not self.original_image_paths:
                QMessageBox.warning(self, "无图片", "所选文件夹中没有找到任何图片文件。")
                self._set_ui_enabled(False)
                return

            self.inpaint_dir, self.qianresult_dir = create_required_dirs(folder_path)
            self.inpaint_image_paths = [
                os.path.join(self.inpaint_dir, os.path.basename(p))
                for p in self.original_image_paths
            ]

            # 确保inpaint文件夹有对应的图片副本
            for orig_path, inpaint_path in zip(self.original_image_paths, self.inpaint_image_paths):
                if not os.path.exists(inpaint_path):
                    shutil.copy2(orig_path, inpaint_path)
                    print(f"复制 {orig_path} 到 {inpaint_path}")

            self.thumbnail_panel.load_thumbnails(self.original_image_paths)

            # 默认加载第一页
            self._switch_page(0)

        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载文件夹时发生错误: {e}")
            self._set_ui_enabled(False)

    def _switch_page_from_thumbnail(self, index):
        """从缩略图点击事件切换页面"""
        if index != self.current_page_index:
            self._switch_page(index)

    def _switch_page(self, new_index):
        """切换到指定页面，并处理自动保存"""
        if self.current_page_index != -1:
            # 自动保存当前页的文本框状态
            self._save_text_boxes_for_page(self.current_page_index, self.text_boxes)

        self.current_page_index = new_index
        # 从qianresult目录加载该页的文本框数据（如果存在）
        self.text_boxes = self._load_text_boxes_for_page(new_index)
        self.selected_text_boxes = [] # 清除选择

        # 加载图片到画布
        original_path = self.original_image_paths[new_index]
        inpaint_path = self.inpaint_image_paths[new_index]
        self.image_canvas.load_images(inpaint_path, original_path)
        self.image_canvas.set_text_boxes(self.text_boxes) # 将文本框传递给画布
        self.image_canvas.update() # 强制重绘

        # 清空历史记录，因为切换页面意味着新的编辑会话
        self.history_manager.clear()
        self.history_manager.save_state(self._get_current_state())

        self.thumbnail_panel.set_current_selected(new_index) # 更新缩略图面板的选中状态

    def _save_text_boxes_for_page(self, page_index, text_boxes_to_save):
        """将指定页的文本框数据保存到文件"""
        if page_index == -1 or not text_boxes_to_save:
            return

        # 文本框数据保存为JSON文件，与inpaint图片同名但后缀为.json
        inpaint_img_path = self.inpaint_image_paths[page_index]
        json_path = os.path.splitext(inpaint_img_path)[0] + ".json"

        data_to_save = [tb.to_dict() for tb in text_boxes_to_save]
        try:
            import json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print(f"文本框数据已保存到: {json_path}")
        except Exception as e:
            print(f"保存文本框数据失败: {e}")

    def _load_text_boxes_for_page(self, page_index):
        """加载指定页的文本框数据"""
        if page_index == -1:
            return []

        inpaint_img_path = self.inpaint_image_paths[page_index]
        json_path = os.path.splitext(inpaint_img_path)[0] + ".json"

        if os.path.exists(json_path):
            try:
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                text_boxes = [TextBox.from_dict(d) for d in data]
                print(f"文本框数据已从 {json_path} 加载。")
                return text_boxes
            except Exception as e:
                print(f"加载文本框数据失败: {e}")
                return []
        return []

    def _save_current_page(self):
        """保存当前页的嵌字图片到qianresult文件夹"""
        if self.current_page_index == -1:
            QMessageBox.warning(self, "保存失败", "没有加载任何页面。")
            return

        inpaint_img_path = self.inpaint_image_paths[self.current_page_index]
        output_filename = os.path.basename(inpaint_img_path)
        output_path = os.path.join(self.qianresult_dir, output_filename)

        try:
            # 调用ImageCanvas的方法来渲染并保存图片
            self.image_canvas.save_rendered_image(output_path, self.text_boxes)
            # 同时保存文本框数据
            self._save_text_boxes_for_page(self.current_page_index, self.text_boxes)
            QMessageBox.information(self, "保存成功", f"当前页面已保存到: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存当前页面时发生错误: {e}")

    def _add_text_box_to_canvas(self, text_box):
        """当画布上添加新文本框时调用"""
        self.text_boxes.append(text_box)
        self.selected_text_boxes = [text_box] # 新建的文本框自动选中
        self.text_properties_panel.load_text_box_properties(text_box)
        self.history_manager.save_state(self._get_current_state())
        self.image_canvas.update()

    def _update_selected_text_boxes(self, selected_tbs):
        """更新当前选中的文本框列表，并同步到属性面板"""
        self.selected_text_boxes = selected_tbs
        if len(selected_tbs) == 1:
            self.text_properties_panel.load_text_box_properties(selected_tbs[0])
        else:
            self.text_properties_panel.clear_properties() # 多选或无选时清空面板

    def _on_text_box_updated(self):
        """当文本框在画布上被移动、改变大小等时调用"""
        self.history_manager.save_state(self._get_current_state())

    def _apply_format_to_selected_text_boxes(self, format_data):
        """将格式应用到所有选中的文本框"""
        if not self.selected_text_boxes:
            QMessageBox.warning(self, "无选中", "请先选择一个或多个文本框。")
            return

        self.history_manager.save_state(self._get_current_state()) # 保存当前状态以便撤销

        for tb in self.selected_text_boxes:
            tb.apply_format(format_data)
        self.image_canvas.update() # 强制重绘
        self.history_manager.save_state(self._get_current_state()) # 保存应用格式后的状态

    def _get_current_state(self):
        """获取当前页面所有文本框的深拷贝状态"""
        return [tb.to_dict() for tb in self.text_boxes]

    def _restore_state(self, state):
        """恢复到给定的文本框状态"""
        self.text_boxes = [TextBox.from_dict(d) for d in state]
        self.selected_text_boxes = [] # 恢复状态后取消所有选择
        self.image_canvas.set_text_boxes(self.text_boxes)
        self.image_canvas.update()
        self.text_properties_panel.clear_properties() # 清空面板

    def _undo(self):
        """撤销操作"""
        state = self.history_manager.undo()
        if state is not None:
            self._restore_state(state)
            print("执行撤销操作。")
        else:
            print("无法撤销，已是最初状态。")

    def _redo(self):
        """重做操作"""
        state = self.history_manager.redo()
        if state is not None:
            self._restore_state(state)
            print("执行重做操作。")
        else:
            print("无法重做，已是最新状态。")

    def closeEvent(self, event):
        """窗口关闭事件，自动保存当前页"""
        if self.current_page_index != -1:
            reply = QMessageBox.question(self, '保存确认',
                                         "是否保存当前页的修改？",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                         QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self._save_current_page()
            elif reply == QMessageBox.Cancel:
                event.ignore() # 取消关闭
                return
        event.accept() # 接受关闭


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
