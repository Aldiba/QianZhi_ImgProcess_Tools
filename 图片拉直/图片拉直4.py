import os
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk

# ==========================================
# 核心图像处理逻辑 (保持 V4.0 的修复和标准化)
# ==========================================
def straighten_and_crop(image_cv, contour):
    """
    根据轮廓旋转图像（微调 +/- 45度），防止翻转。
    """
    rect = cv2.minAreaRect(contour)
    (cx, cy), (w, h), angle = rect

    # 角度规范化，防止180度翻转
    if angle < -45:
        angle += 90
        w, h = h, w
    elif angle > 45:
        angle -= 90
        w, h = h, w

    (h_img, w_img) = image_cv.shape[:2]
    center = (w_img // 2, h_img // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    contour_points = contour.reshape(-1, 1, 2).astype(np.float32)
    rotated_contour_points = cv2.transform(contour_points, M)
    
    x, y, w_crop, h_crop = cv2.boundingRect(rotated_contour_points)

    if w_crop <= 0 or h_crop <= 0:
        return np.full((10, 10, 3), 255, dtype=np.uint8)

    M[0, 2] -= x
    M[1, 2] -= y

    final_image = cv2.warpAffine(
        image_cv, M, (w_crop, h_crop),
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_CONSTANT, 
        borderValue=(255, 255, 255)
    )
    
    return final_image

# ==========================================
# 交互式处理窗口 (V5.0 重大升级)
# ==========================================
class InteractiveProcessorWindow(tk.Toplevel):
    def __init__(self, parent, file_list, output_dir):
        super().__init__(parent)
        self.title("交互式处理 - 滚轮缩放 | 右键拖拽 | 左键取色")
        
        # 1. 窗口最大化
        self.state('zoomed') 
        
        self.file_list = file_list
        self.output_dir = output_dir
        self.current_index = 0
        
        # 数据状态
        self.reference_size = None
        self.selected_color = None
        self.current_contour_orig = None # 存储基于原图坐标的轮廓
        
        # 视图状态
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # 布局 - 顶部信息
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        self.info_label = ttk.Label(top_frame, text="准备就绪", font=("微软雅黑", 12, "bold"))
        self.info_label.pack()

        # 布局 - 中间画布 (核心区域)
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#404040", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 布局 - 底部控制面板
        control_panel = ttk.Frame(self)
        control_panel.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

        # 左侧：颜色预览
        color_frame = ttk.LabelFrame(control_panel, text="当前选中颜色")
        color_frame.pack(side=tk.LEFT, padx=10)
        self.color_preview = tk.Label(color_frame, bg="white", width=10, height=2, relief="sunken")
        self.color_preview.pack(padx=5, pady=5)
        self.color_text = ttk.Label(color_frame, text="未选择")
        self.color_text.pack(padx=5, pady=2)

        # 中间：容差滑块
        slider_frame = ttk.LabelFrame(control_panel, text="颜色容差 (Sensitivity)")
        slider_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.tolerance_var = tk.IntVar(value=30)
        self.tolerance_slider = ttk.Scale(slider_frame, from_=1, to=100, orient=tk.HORIZONTAL, variable=self.tolerance_var, command=self.update_preview_trigger)
        self.tolerance_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        self.tolerance_label = ttk.Label(slider_frame, text="30", font=("Arial", 12))
        self.tolerance_label.pack(side=tk.RIGHT, padx=10)

        # 右侧：操作按钮
        btn_frame = ttk.Frame(control_panel)
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        style = ttk.Style()
        style.configure("Big.TButton", font=("微软雅黑", 12))
        
        self.skip_btn = ttk.Button(btn_frame, text="跳过 (Skip)", style="Big.TButton", command=self.skip)
        self.skip_btn.pack(side=tk.LEFT, padx=10)
        
        self.confirm_btn = ttk.Button(btn_frame, text="确认并下一张 (Enter)", style="Big.TButton", command=self.process_and_next)
        self.confirm_btn.pack(side=tk.LEFT, padx=10)

        # === 事件绑定 ===
        # 1. 缩放
        self.canvas.bind("<MouseWheel>", self.on_zoom) # Windows
        self.canvas.bind("<Button-4>", self.on_zoom)   # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_zoom)   # Linux scroll down
        
        # 2. 平移 (右键拖拽)
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        
        # 3. 取色 (左键点击)
        self.canvas.bind("<Button-1>", self.on_pick_color)
        
        # 4. 快捷键
        self.bind("<Return>", lambda e: self.process_and_next())
        self.bind("<space>", lambda e: self.process_and_next())
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 加载第一张图
        self.load_image()
        self.deiconify()
        self.grab_set()

    def load_image(self):
        if self.current_index >= len(self.file_list):
            self.finish_processing()
            return

        self.canvas.delete("all")
        self.selected_color = None
        self.current_contour_orig = None
        self.color_preview.config(bg="white")
        self.color_text.config(text="未选择")
        
        # 重置视图
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

        filepath = self.file_list[self.current_index]
        info_text = f"正在处理: {os.path.basename(filepath)} ({self.current_index + 1}/{len(self.file_list)})"
        if self.reference_size:
            info_text += f"  [锁定输出尺寸: {self.reference_size[0]}x{self.reference_size[1]}]"
        self.info_label.config(text=info_text)

        # 读取原图
        pil_img = Image.open(filepath)
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        self.image_pil_orig = pil_img
        self.image_cv_orig = np.array(pil_img)[:, :, ::-1]
        
        # 计算初始适应屏幕的缩放比例
        screen_w = self.winfo_screenwidth() * 0.8
        screen_h = self.winfo_screenheight() * 0.7
        w_ratio = screen_w / self.image_pil_orig.width
        h_ratio = screen_h / self.image_pil_orig.height
        self.base_scale = min(w_ratio, h_ratio, 1.0) # 初始不放大，只缩小
        
        self.zoom_level = self.base_scale
        
        self.redraw_image()

    def redraw_image(self):
        """核心绘制函数：根据当前缩放和平移重绘图像"""
        if not hasattr(self, 'image_pil_orig'): return

        # 1. 计算目标尺寸
        new_w = int(self.image_pil_orig.width * self.zoom_level)
        new_h = int(self.image_pil_orig.height * self.zoom_level)
        
        # 2. 只有当尺寸变化较大时才重新 Resize (简单优化)
        # 为了流畅性，这里每次都 resize，Pillow 的 resize 速度在现代 CPU 上通常足够快
        # 使用 Nearest 在缩放操作时最快，但质量差；LANCZOS 最慢。这里用 BILINEAR 平衡
        self.image_pil_display = self.image_pil_orig.resize((new_w, new_h), Image.BILINEAR)
        self.image_tk = ImageTk.PhotoImage(self.image_pil_display)
        
        # 3. 更新 Canvas
        self.canvas.delete("img_tag")
        # 注意：我们将图像放在 (pan_x, pan_y) 位置
        self.canvas.create_image(self.pan_x, self.pan_y, anchor=tk.NW, image=self.image_tk, tags="img_tag")
        self.canvas.tag_lower("img_tag") # 确保图片在框线下面
        
        # 4. 如果有轮廓，也需要重绘
        self.draw_preview_contour()

    # === 交互逻辑 ===
    
    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.start_pan_x = self.pan_x
        self.start_pan_y = self.pan_y
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def do_pan(self, event):
        # 计算位移
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        self.pan_x = self.start_pan_x + dx
        self.pan_y = self.start_pan_y + dy
        
        # 移动所有元素
        self.canvas.delete("all") # 清除旧的
        self.canvas.create_image(self.pan_x, self.pan_y, anchor=tk.NW, image=self.image_tk, tags="img_tag")
        self.draw_preview_contour()

    def on_zoom(self, event):
        # 获取鼠标当前在 Canvas 上的位置
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # 判断滚轮方向
        if event.num == 5 or event.delta < 0:
            factor = 0.9
        else:
            factor = 1.1
            
        # 限制缩放范围
        new_zoom = self.zoom_level * factor
        if new_zoom < 0.05 or new_zoom > 10: return
        
        # 计算缩放前的鼠标相对于图片的相对坐标 (0~1)
        # 图片当前绘制位置是 self.pan_x, self.pan_y
        # 鼠标相对于图片左上角的像素距离
        rel_x = (event.x - self.pan_x) / self.zoom_level
        rel_y = (event.y - self.pan_y) / self.zoom_level
        
        self.zoom_level = new_zoom
        
        # 计算新的平移量，使得鼠标指向的图片点位置不变
        # 新的图片左上角 = 鼠标位置 - (新缩放比例 * 相对距离)
        self.pan_x = event.x - (rel_x * self.zoom_level)
        self.pan_y = event.y - (rel_y * self.zoom_level)
        
        self.redraw_image()

    def on_pick_color(self, event):
        """处理点击取色"""
        # 1. 计算点击点相对于图片的坐标
        # canvas 坐标 (event.x, event.y) -> 图片内坐标
        img_x = int((event.x - self.pan_x) / self.zoom_level)
        img_y = int((event.y - self.pan_y) / self.zoom_level)
        
        # 边界检查
        if 0 <= img_x < self.image_pil_orig.width and 0 <= img_y < self.image_pil_orig.height:
            # 从原图中获取颜色，保证最准确
            rgb = self.image_pil_orig.getpixel((img_x, img_y))
            # PIL是RGB, OpenCV是BGR
            self.selected_color = (rgb[0], rgb[1], rgb[2]) # RGB tuple
            
            # 更新 UI
            hex_color = '#%02x%02x%02x' % self.selected_color
            self.color_preview.config(bg=hex_color)
            self.color_text.config(text=f"RGB: {self.selected_color}")
            
            # 触发预览更新
            self.update_preview()

    def update_preview_trigger(self, event=None):
        # 延迟一点更新，防止滑动条卡顿，或者直接更新
        self.tolerance_label.config(text=str(self.tolerance_var.get()))
        self.update_preview()

    def update_preview(self):
        if self.selected_color is None: return
        
        tolerance = self.tolerance_var.get()
        
        # 这里的计算策略：
        # 为了速度，我们不应该在 4K 原图上做 cv2.inRange，那样会卡。
        # 我们应该在一个较小的“工作图”上做运算，得到轮廓后，再映射回原图坐标。
        
        # 创建一个工作图 (固定最大边长 1000px，保证速度)
        work_scale = 1000 / max(self.image_pil_orig.width, self.image_pil_orig.height)
        if work_scale > 1: work_scale = 1
        
        w_work = int(self.image_pil_orig.width * work_scale)
        h_work = int(self.image_pil_orig.height * work_scale)
        
        img_work = cv2.resize(self.image_cv_orig, (w_work, h_work))
        
        # OpenCV 需要 BGR
        target_bgr = self.selected_color[::-1] # RGB to BGR
        
        lower_bound = np.array([max(0, c - tolerance) for c in target_bgr])
        upper_bound = np.array([min(255, c + tolerance) for c in target_bgr])
        
        mask = cv2.inRange(img_work, lower_bound, upper_bound)
        mask_inv = cv2.bitwise_not(mask)
        
        contours, _ = cv2.findContours(mask_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.canvas.delete("preview_box")
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) < 50:
                self.current_contour_orig = None
                return
            
            # 将轮廓坐标从 work 尺寸映射回 orig 尺寸
            self.current_contour_orig = (largest / work_scale).astype(np.int32)
            self.draw_preview_contour()
        else:
            self.current_contour_orig = None

    def draw_preview_contour(self):
        if self.current_contour_orig is None: return
        
        # 将原图坐标的 contour 映射到当前 display 坐标
        # Display Point = Orig Point * Zoom + Pan
        
        # 1. 缩放
        cnt_scaled = self.current_contour_orig.astype(float) * self.zoom_level
        # 2. 平移
        cnt_final = cnt_scaled + [self.pan_x, self.pan_y]
        
        # 计算最小矩形用于绘制
        rect = cv2.minAreaRect(cnt_final.astype(np.int32))
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        
        self.canvas.delete("preview_box")
        # 绘制加粗红线
        self.canvas.create_polygon(tuple(box.flatten()), outline='#FF0000', width=3, fill='', tags="preview_box")

    def process_and_next(self):
        if self.current_contour_orig is None:
            messagebox.showwarning("提示", "未检测到有效区域，请点击背景取色。", parent=self)
            return
        
        # 对原图进行裁剪
        processed_image = straighten_and_crop(self.image_cv_orig, self.current_contour_orig)
        
        # 统一尺寸逻辑
        current_h, current_w = processed_image.shape[:2]
        
        if self.reference_size is None:
            self.reference_size = (current_w, current_h)
            final_image = processed_image
        else:
            target_w, target_h = self.reference_size
            final_image = cv2.resize(processed_image, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        # 保存
        output_path = os.path.join(self.output_dir, os.path.basename(self.file_list[self.current_index]))
        final_image_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
        Image.fromarray(final_image_rgb).save(output_path)
        
        print(f"已保存: {output_path}")
        self.current_index += 1
        self.load_image()

    def skip(self):
        self.current_index += 1
        self.load_image()

    def finish_processing(self):
        messagebox.showinfo("完成", "所有图片已处理完毕！")
        self.destroy()

    def on_close(self):
        if messagebox.askyesno("确认", "您确定要中断处理吗？", parent=self):
            self.destroy()

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批处理工具 - V5.0 专业面板")
        self.root.geometry("600x200") # 初始面板也稍微大一点
        
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        
        frame = ttk.Frame(root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 样式微调
        style = ttk.Style()
        style.configure("TButton", font=("微软雅黑", 10))
        style.configure("TLabel", font=("微软雅黑", 10))
        
        grid_opts = {'padx': 5, 'pady': 10, 'sticky': tk.EW}
        
        ttk.Label(frame, text="输入文件夹:").grid(row=0, column=0, **grid_opts)
        ttk.Entry(frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, **grid_opts)
        ttk.Button(frame, text="浏览...", command=self.browse_input).grid(row=0, column=2, **grid_opts)
        
        ttk.Label(frame, text="输出文件夹:").grid(row=1, column=0, **grid_opts)
        ttk.Entry(frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, **grid_opts)
        ttk.Button(frame, text="浏览...", command=self.browse_output).grid(row=1, column=2, **grid_opts)
        
        start_btn = ttk.Button(frame, text="▶ 开始处理", command=self.start_processing)
        start_btn.grid(row=2, column=1, pady=20, ipadx=20, ipady=5)
        
        frame.columnconfigure(1, weight=1)
        
    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder: self.input_folder.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder: self.output_folder.set(folder)

    def start_processing(self):
        input_dir, output_dir = self.input_folder.get(), self.output_folder.get()
        if not input_dir or not output_dir:
            messagebox.showerror("错误", "请选择文件夹。")
            return
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
        
        if not files:
            messagebox.showinfo("提示", "没有找到图片文件。")
            return
            
        InteractiveProcessorWindow(self.root, files, output_dir)

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = MainApp(root)
    root.mainloop()