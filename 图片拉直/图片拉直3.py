import os
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk

def straighten_and_crop(image_cv, contour):
    """
    【V4.0 逻辑】 - 修复了旋转180度的问题
    仅对图像进行微调拉直（+/- 45度以内），尊重原始拍摄方向，防止倒转。
    """
    # 获取最小外接矩形
    rect = cv2.minAreaRect(contour)
    (cx, cy), (w, h), angle = rect

    # OpenCV 的 minAreaRect 角度定义比较复杂，不同版本表现不同。
    # 下面的逻辑用于确保我们只进行微小的旋转校正，而不是大幅度翻转。
    
    # 如果宽比高长（说明是横向的矩形），且角度很大，可能是检测到了竖向纹理
    # 我们通过交换宽高和调整角度，将旋转限制在 -45 到 45 度之间
    # 这样可以保证图片永远是"头朝上"（假设你拍摄时大致是正的）
    
    # 规范化角度到 (-45, 45] 区间
    if angle < -45:
        angle += 90
        w, h = h, w
    elif angle > 45:
        angle -= 90
        w, h = h, w

    # 如果还是横向的（w > h），但你想强制竖向（类似旧代码逻辑），
    # 可以在这里加判断。但为了防止180度翻转，建议保持拍摄时的方向。
    # 下面的代码仅做拉直，不强制转90度，这样最安全。

    (h_img, w_img) = image_cv.shape[:2]
    center = (w_img // 2, h_img // 2)
    
    # 获取旋转矩阵
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # 旋转轮廓点以计算新的边界框
    contour_points = contour.reshape(-1, 1, 2).astype(np.float32)
    rotated_contour_points = cv2.transform(contour_points, M)
    
    x, y, w_crop, h_crop = cv2.boundingRect(rotated_contour_points)

    # 防止空图
    if w_crop <= 0 or h_crop <= 0:
        return np.full((10, 10, 3), 255, dtype=np.uint8)

    # 调整平移量，确保裁剪区域在视野内
    M[0, 2] -= x
    M[1, 2] -= y

    # 执行旋转和裁剪
    final_image = cv2.warpAffine(
        image_cv, M, (w_crop, h_crop),
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_CONSTANT, 
        borderValue=(255, 255, 255)
    )
    
    return final_image

class InteractiveProcessorWindow(tk.Toplevel):
    def __init__(self, parent, file_list, output_dir):
        super().__init__(parent)
        self.title("交互式处理")
        self.withdraw()
        self.file_list = file_list
        self.output_dir = output_dir
        self.current_index = 0
        self.selected_color = None
        self.current_contour = None
        
        # === 新增：用于存储第一张图的标准尺寸 ===
        self.reference_size = None  # 格式: (width, height)
        # =====================================

        self.info_label = ttk.Label(self, text="文件名", font=("Helvetica", 10))
        self.info_label.pack(pady=5)
        
        self.canvas = tk.Canvas(self, bg="gray")
        self.canvas.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(control_frame, text="颜色容差:").pack(side=tk.LEFT, padx=(0, 5))
        self.tolerance_var = tk.IntVar(value=30)
        self.tolerance_slider = ttk.Scale(control_frame, from_=1, to=100, orient=tk.HORIZONTAL, variable=self.tolerance_var, command=self.update_preview)
        self.tolerance_slider.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.tolerance_label = ttk.Label(control_frame, text="30")
        self.tolerance_label.pack(side=tk.LEFT, padx=(5, 0))
        
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        self.confirm_btn = ttk.Button(button_frame, text="确认并处理下一张", command=self.process_and_next)
        self.confirm_btn.pack(side=tk.LEFT, padx=5)
        self.skip_btn = ttk.Button(button_frame, text="跳过", command=self.skip)
        self.skip_btn.pack(side=tk.LEFT, padx=5)
        
        self.canvas.bind("<Button-1>", self.on_color_pick)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.load_image()
        self.deiconify()
        self.grab_set()
        
    def process_and_next(self):
        if self.current_contour is None:
            messagebox.showwarning("提示", "未能生成有效的轮廓。请尝试点击其他背景区域或调整容差。", parent=self)
            return
        
        # 1. 提取并拉直内容
        processed_image = straighten_and_crop(self.image_cv_orig, self.current_contour)
        
        # === 修改：统一尺寸逻辑 ===
        current_h, current_w = processed_image.shape[:2]
        
        if self.reference_size is None:
            # 如果是第一张成功的图片，将其尺寸设为基准
            self.reference_size = (current_w, current_h)
            final_image = processed_image
            print(f"基准尺寸已设置为: {self.reference_size}")
        else:
            # 如果已有基准，强制调整为基准尺寸
            target_w, target_h = self.reference_size
            # 使用 LANCZOS4 插值以获得较好的缩放质量
            final_image = cv2.resize(processed_image, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        # =======================

        # 保存图像
        output_path = os.path.join(self.output_dir, os.path.basename(self.file_list[self.current_index]))
        final_image_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
        img_to_save = Image.fromarray(final_image_rgb)
        img_to_save.save(output_path)
        
        # 处理下一张
        self.current_index += 1
        self.load_image()

    def load_image(self):
        if self.current_index >= len(self.file_list):
            self.finish_processing()
            return
            
        self.canvas.delete("all")
        self.selected_color = None
        self.current_contour = None
        
        filepath = self.file_list[self.current_index]
        progress_text = f"正在处理: {os.path.basename(filepath)} ({self.current_index + 1}/{len(self.file_list)})"
        if self.reference_size:
            progress_text += f" [锁定尺寸: {self.reference_size[0]}x{self.reference_size[1]}]"
        
        self.info_label.config(text=progress_text)
        
        self.image_pil_orig = Image.open(filepath)
        if self.image_pil_orig.mode != 'RGB':
            self.image_pil_orig = self.image_pil_orig.convert('RGB')
        self.image_cv_orig = np.array(self.image_pil_orig)[:, :, ::-1]
        
        self.image_pil_display = self.image_pil_orig.copy()
        max_w = self.winfo_screenwidth() * 0.7
        max_h = self.winfo_screenheight() * 0.7
        self.image_pil_display.thumbnail((max_w, max_h))
        
        self.display_w, self.display_h = self.image_pil_display.size
        self.scale_factor = self.image_pil_orig.width / self.display_w
        
        self.image_cv_display = np.array(self.image_pil_display)[:, :, ::-1]
        self.image_tk = ImageTk.PhotoImage(self.image_pil_display)
        
        self.canvas.config(width=self.display_w, height=self.display_h)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)
        
        self.update_idletasks()
        self.geometry(f"{self.display_w+40}x{self.display_h+120}")

    def on_color_pick(self, event):
        x, y = event.x, event.y
        if 0 <= x < self.display_w and 0 <= y < self.display_h:
            self.selected_color = self.image_cv_display[y, x]
            self.update_preview()

    def update_preview(self, event=None):
        if self.selected_color is None: return
        
        self.tolerance_label.config(text=str(self.tolerance_var.get()))
        tolerance = self.tolerance_var.get()
        
        lower_bound = np.array([max(0, c - tolerance) for c in self.selected_color])
        upper_bound = np.array([min(255, c + tolerance) for c in self.selected_color])
        
        mask = cv2.inRange(self.image_cv_display, lower_bound, upper_bound)
        mask_inv = cv2.bitwise_not(mask)
        
        contours, _ = cv2.findContours(mask_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.canvas.delete("preview_box")
        if contours:
            largest_contour_display = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour_display) < 100:
                self.current_contour = None
                return
                
            rect = cv2.minAreaRect(largest_contour_display)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            self.canvas.create_polygon(tuple(box.flatten()), outline='red', width=2, fill='', tags="preview_box")
            
            self.current_contour = (largest_contour_display * self.scale_factor).astype(int)

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
        self.root.title("图片半自动拉直工具")
        self.root.geometry("500x180")
        
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        
        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="输入文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.input_entry = ttk.Entry(frame, textvariable=self.input_folder, width=40)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_input_btn = ttk.Button(frame, text="浏览...", command=self.browse_input)
        self.browse_input_btn.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(frame, text="输出文件夹:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_entry = ttk.Entry(frame, textvariable=self.output_folder, width=40)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.browse_output_btn = ttk.Button(frame, text="浏览...", command=self.browse_output)
        self.browse_output_btn.grid(row=1, column=2, padx=5, pady=5)
        
        self.start_button = ttk.Button(frame, text="开始处理", command=self.start_processing)
        self.start_button.grid(row=2, column=1, padx=5, pady=20)
        
    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder: self.input_folder.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder: self.output_folder.set(folder)

    def start_processing(self):
        input_dir, output_dir = self.input_folder.get(), self.output_folder.get()
        
        if not input_dir or not output_dir:
            messagebox.showerror("错误", "请选择输入和输出文件夹。")
            return
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        files_to_process = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(supported_formats)]
        
        if not files_to_process:
            messagebox.showinfo("提示", "输入文件夹中没有找到支持的图片文件。")
            return
            
        interactive_window = InteractiveProcessorWindow(self.root, files_to_process, output_dir)
        self.root.wait_window(interactive_window)

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = MainApp(root)
    root.mainloop()