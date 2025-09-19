
# text_box.py
import cairo
import math
from PyQt5.QtCore import QPoint, QRect, QSize
from utils import get_font_path

class TextBox:
    def __init__(self, x, y, width, height, text="",
                 font_name="Arial", font_size=16, color=(0, 0, 0, 1),
                 stroke_width=0, stroke_color=(0, 0, 0, 1),
                 shadow_offset=(0, 0), shadow_color=(0, 0, 0, 0.5),
                 h_scale=1.0, v_scale=1.0, line_spacing=1.0, char_spacing=0,
                 is_vertical=False, rotation=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text

        self.font_name = font_name
        self.font_size = font_size
        self.color = color # RGBA (0-1)
        self.stroke_width = stroke_width
        self.stroke_color = stroke_color
        self.shadow_offset = shadow_offset # (dx, dy)
        self.shadow_color = shadow_color
        self.h_scale = h_scale # 水平缩放
        self.v_scale = v_scale # 垂直缩放
        self.line_spacing = line_spacing # 行间距倍数
        self.char_spacing = char_spacing # 字符间距 (像素)
        self.is_vertical = is_vertical # 是否竖排
        self.rotation = rotation # 旋转角度 (度)

        self._drag_start_pos = QPoint(x, y) # 用于多选拖动时记录初始位置

    def to_dict(self):
        """将文本框属性转换为字典，用于保存和历史记录"""
        return {
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "text": self.text, "font_name": self.font_name, "font_size": self.font_size,
            "color": self.color, "stroke_width": self.stroke_width,
            "stroke_color": self.stroke_color, "shadow_offset": self.shadow_offset,
            "shadow_color": self.shadow_color, "h_scale": self.h_scale,
            "v_scale": self.v_scale, "line_spacing": self.line_spacing,
            "char_spacing": self.char_spacing, "is_vertical": self.is_vertical,
            "rotation": self.rotation
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建TextBox实例"""
        return cls(**data)

    def pos(self):
        return QPoint(self.x, self.y)

    def rect(self):
        return QRect(self.x, self.y, self.width, self.height)

    def center_point(self):
        return QPoint(self.x + self.width // 2, self.y + self.height // 2)

    def apply_format(self, format_data):
        """应用格式数据到文本框"""
        self.text = format_data.get("text", self.text)
        self.font_name = format_data.get("font_name", self.font_name)
        self.font_size = format_data.get("font_size", self.font_size)
        self.color = format_data.get("color", self.color)
        self.stroke_width = format_data.get("stroke_width", self.stroke_width)
        self.stroke_color = format_data.get("stroke_color", self.stroke_color)
        self.shadow_offset = format_data.get("shadow_offset", self.shadow_offset)
        self.shadow_color = format_data.get("shadow_color", self.shadow_color)
        self.h_scale = format_data.get("h_scale", self.h_scale)
        self.v_scale = format_data.get("v_scale", self.v_scale)
        self.line_spacing = format_data.get("line_spacing", self.line_spacing)
        self.char_spacing = format_data.get("char_spacing", self.char_spacing)
        self.is_vertical = format_data.get("is_vertical", self.is_vertical)
        self.rotation = format_data.get("rotation", self.rotation)

    def draw(self, ctx: cairo.Context, draw_handles=False):
        """
        使用 PyCairo 绘制文本框。
        ctx: Cairo 上下文
        draw_handles: 是否绘制边框和控制点
        """
        ctx.save() # 保存当前上下文状态

        # 移动到文本框中心，然后旋转
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        ctx.translate(center_x, center_y)
        ctx.rotate(math.radians(self.rotation))
        ctx.translate(-center_x, -center_y) # 移回原点，但现在是旋转后的坐标系

        # 设置字体
        # PyCairo的select_font_face需要字体文件名或系统名称
        # 这里尝试使用系统字体路径，如果找不到，则回退到通用字体
        font_path = get_font_path(self.font_name)
        if font_path and os.path.exists(font_path):
            ctx.set_font_face(cairo.ToyFontFace(self.font_name))
        else:
            ctx.select_font_face(self.font_name,
                                 cairo.FONT_SLANT_NORMAL,
                                 cairo.FONT_WEIGHT_NORMAL)

        ctx.set_font_size(self.font_size)

        # 应用水平和垂直缩放
        # 注意：PyCairo的scale会影响所有后续绘制，包括描边宽度
        # 更好的做法是计算缩放后的字体度量，或者在绘制文本后再应用描边
        # 这里简化处理，直接在绘制前缩放
        ctx.translate(self.x, self.y)
        ctx.scale(self.h_scale, self.v_scale)
        ctx.translate(-self.x, -self.y)

        # 计算文本布局
        lines = self.text.split('\n')
        current_y = self.y + self.font_size # 初始Y位置

        for line_idx, line in enumerate(lines):
            if self.is_vertical:
                # 竖排文本（每个字符旋转并堆叠）
                current_x_vertical = self.x + self.width - self.font_size # 从右往左写
                for char_idx, char in enumerate(line):
                    # 绘制阴影
                    if self.shadow_color[3] > 0: # 检查alpha
                        ctx.set_source_rgba(*self.shadow_color)
                        ctx.move_to(current_x_vertical + self.shadow_offset[0],
                                    current_y + self.shadow_offset[1] + char_idx * (self.font_size + self.char_spacing))
                        ctx.show_text(char)

                    # 绘制描边
                    if self.stroke_width > 0:
                        ctx.set_source_rgba(*self.stroke_color)
                        ctx.set_line_width(self.stroke_width)
                        ctx.text_path(char)
                        ctx.stroke_preserve() # 保持路径，用于填充

                    # 绘制文本
                    ctx.set_source_rgba(*self.color)
                    ctx.move_to(current_x_vertical, current_y + char_idx * (self.font_size + self.char_spacing))
                    ctx.show_text(char)
                current_y += (self.font_size + self.char_spacing) * len(line) * self.line_spacing # 下一行偏移
            else:
                # 横排文本
                text_extents = ctx.text_extents(line)
                # 计算文本在文本框内居中
                text_x = self.x + (self.width / self.h_scale - text_extents.width) / 2
                text_y = current_y

                # 绘制阴影
                if self.shadow_color[3] > 0:
                    ctx.set_source_rgba(*self.shadow_color)
                    ctx.move_to(text_x + self.shadow_offset[0], text_y + self.shadow_offset[1])
                    ctx.show_text(line)

                # 绘制描边
                if self.stroke_width > 0:
                    ctx.set_source_rgba(*self.stroke_color)
                    ctx.set_line_width(self.stroke_width)
                    ctx.move_to(text_x, text_y)
                    ctx.text_path(line)
                    ctx.stroke_preserve() # 保持路径，用于填充

                # 绘制文本
                ctx.set_source_rgba(*self.color)
                ctx.move_to(text_x, text_y)
                ctx.show_text(line)

                current_y += (self.font_size * self.v_scale * self.line_spacing) # 计算下一行Y位置

        ctx.restore() # 恢复上下文状态（移除旋转和缩放）

        if draw_handles:
            # 绘制文本框边框和控制点
            ctx.save()
            # 再次应用旋转，因为边框和句柄也需要旋转
            ctx.translate(center_x, center_y)
            ctx.rotate(math.radians(self.rotation))
            ctx.translate(-center_x, -center_y)

            # 绘制边框
            ctx.set_source_rgba(0, 0.5, 1, 0.8) # 蓝色半透明
            ctx.set_line_width(2)
            ctx.rectangle(self.x, self.y, self.width, self.height)
            ctx.stroke()

            # 绘制控制点
            handle_size = 8
            handles = self.get_handles_rects(handle_size)
            for handle_name, rect in handles.items():
                if handle_name == "rotate":
                    ctx.set_source_rgba(1, 0, 0, 1) # 红色旋转点
                else:
                    ctx.set_source_rgba(0.8, 0.8, 0.8, 1) # 灰色控制点
                ctx.rectangle(rect.x(), rect.y(), rect.width(), rect.height())
                ctx.fill()
            ctx.restore()

    def contains_point(self, point: QPoint):
        """检查点是否在文本框内（考虑旋转）"""
        # 将点转换到文本框的局部坐标系（未旋转前）
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        # 将点平移到原点，然后反向旋转
        translated_x = point.x() - center_x
        translated_y = point.y() - center_y

        rotated_x = translated_x * math.cos(math.radians(-self.rotation)) - \
                    translated_y * math.sin(math.radians(-self.rotation))
        rotated_y = translated_x * math.sin(math.radians(-self.rotation)) + \
                    translated_y * math.cos(math.radians(-self.rotation))

        # 移回文本框的左上角
        local_x = rotated_x + center_x - self.x
        local_y = rotated_y + center_y - self.y

        return 0 <= local_x <= self.width and 0 <= local_y <= self.height

    def get_handles_rects(self, handle_size):
        """获取控制点的矩形区域"""
        half_handle = handle_size / 2
        # 考虑旋转后的句柄位置
        # 句柄位置是相对于文本框的，然后整个文本框旋转
        # 我们可以先计算未旋转时的句柄位置，然后将其旋转
        handles = {
            "top_left": QPoint(self.x, self.y),
            "top_right": QPoint(self.x + self.width, self.y),
            "bottom_left": QPoint(self.x, self.y + self.height),
            "bottom_right": QPoint(self.x + self.width, self.y + self.height),
            "rotate": QPoint(self.x + self.width / 2, self.y - 20) # 旋转手柄在顶部中间稍微上方
        }

        rotated_handles = {}
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        for name, p in handles.items():
            # 将点平移到原点
            translated_x = p.x() - center_x
            translated_y = p.y() - center_y

            # 旋转
            rotated_x = translated_x * math.cos(math.radians(self.rotation)) - \
                        translated_y * math.sin(math.radians(self.rotation))
            rotated_y = translated_x * math.sin(math.radians(self.rotation)) + \
                        translated_y * math.cos(math.radians(self.rotation))

            # 移回中心点
            final_x = rotated_x + center_x
            final_y = rotated_y + center_y

            rotated_handles[name] = QRect(
                int(final_x - half_handle),
                int(final_y - half_handle),
                handle_size,
                handle_size
            )
        return rotated_handles

    def get_handle_at_point(self, point: QPoint, zoom_factor):
        """检查点是否在某个控制点上"""
        # 句柄大小也应随缩放因子调整，使其在屏幕上保持可见大小
        handle_size_on_screen = 8 / zoom_factor # 屏幕上8像素，反算到图片坐标系
        handles = self.get_handles_rects(handle_size_on_screen)
        for name, rect in handles.items():
            if rect.contains(point):
                return name
        return None

    def resize_from_handle(self, mouse_point_img: QPoint, handle: str, zoom_factor: float):
        """
        根据拖动的句柄调整文本框大小。
        mouse_point_img: 鼠标在图片坐标系中的位置
        handle: 被拖动的句柄名称
        """
        # 将鼠标点转换到文本框的局部坐标系（未旋转前）
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        translated_x = mouse_point_img.x() - center_x
        translated_y = mouse_point_img.y() - center_y

        rotated_x = translated_x * math.cos(math.radians(-self.rotation)) - \
                    translated_y * math.sin(math.radians(-self.rotation))
        rotated_y = translated_x * math.sin(math.radians(-self.rotation)) + \
                    translated_y * math.cos(math.radians(-self.rotation))

        # 移回文本框的左上角
        local_mouse_x = rotated_x + center_x - self.x
        local_mouse_y = rotated_y + center_y - self.y

        # 记录原始的右下角和左上角，用于计算新的宽度和高度
        old_right = self.x + self.width
        old_bottom = self.y + self.height

        new_x, new_y, new_width, new_height = self.x, self.y, self.width, self.height

        min_size = 20 # 最小尺寸

        if handle == "top_left":
            new_x = local_mouse_x + self.x # 鼠标点即为新的左上角
            new_y = local_mouse_y + self.y
            new_width = old_right - new_x
            new_height = old_bottom - new_y
        elif handle == "top_right":
            new_y = local_mouse_y + self.y
            new_width = local_mouse_x
            new_height = old_bottom - new_y
        elif handle == "bottom_left":
            new_x = local_mouse_x + self.x
            new_width = old_right - new_x
            new_height = local_mouse_y
        elif handle == "bottom_right":
            new_width = local_mouse_x
            new_height = local_mouse_y

        # 确保宽度和高度不小于最小尺寸
        if new_width < min_size:
            if handle in ["top_left", "bottom_left"]:
                new_x = old_right - min_size
            new_width = min_size
        if new_height < min_size:
            if handle in ["top_left", "top_right"]:
                new_y = old_bottom - min_size
            new_height = min_size

        self.x, self.y, self.width, self.height = new_x, new_y, new_width, new_height

    def set_pos(self, x, y):
        self.x = x
        self.y = y

