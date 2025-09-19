import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os

class ImageCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量裁剪工具")
        
        self.image_path = None
        self.cropped_image = None
        self.original_image = None
        
        self.left_crop = tk.IntVar(value=0)
        self.right_crop = tk.IntVar(value=0)
        self.top_crop = tk.IntVar(value=0)
        self.bottom_crop = tk.IntVar(value=0)

        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 路径选择区域
        path_frame = ttk.LabelFrame(main_frame, text="1. 选择图片文件夹")
        path_frame.pack(fill=tk.X, pady=5)
        
        self.path_label = ttk.Label(path_frame, text="未选择路径", width=50)
        self.path_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        browse_button = ttk.Button(path_frame, text="浏览", command=self.browse_folder)
        browse_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # 裁剪设置和预览区域
        control_frame = ttk.LabelFrame(main_frame, text="2. 裁剪设置与预览")
        control_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 预览区域
        preview_frame = ttk.Frame(control_frame)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(preview_frame, bg="gray", relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.crop_rect = self.canvas.create_rectangle(0, 0, 0, 0, outline='red', width=2, dash=(5, 5))
        
        self.top_line = self.canvas.create_line(0, 0, 0, 0, fill='red', width=2)
        self.bottom_line = self.canvas.create_line(0, 0, 0, 0, fill='red', width=2)
        self.left_line = self.canvas.create_line(0, 0, 0, 0, fill='red', width=2)
        self.right_line = self.canvas.create_line(0, 0, 0, 0, fill='red', width=2)
        
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        
        # 裁剪参数输入区域
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(side=tk.RIGHT, padx=5, pady=5, anchor=tk.N)
        
        ttk.Label(param_frame, text="左侧裁剪距离 (px):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.left_entry = ttk.Entry(param_frame, textvariable=self.left_crop, width=10)
        self.left_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(param_frame, text="右侧裁剪距离 (px):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.right_entry = ttk.Entry(param_frame, textvariable=self.right_crop, width=10)
        self.right_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(param_frame, text="顶部裁剪距离 (px):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.top_entry = ttk.Entry(param_frame, textvariable=self.top_crop, width=10)
        self.top_entry.grid(row=2, column=1, pady=5)
        
        ttk.Label(param_frame, text="底部裁剪距离 (px):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.bottom_entry = ttk.Entry(param_frame, textvariable=self.bottom_crop, width=10)
        self.bottom_entry.grid(row=3, column=1, pady=5)
        
        self.left_crop.trace_add("write", self.update_preview_from_entry)
        self.right_crop.trace_add("write", self.update_preview_from_entry)
        self.top_crop.trace_add("write", self.update_preview_from_entry)
        self.bottom_crop.trace_add("write", self.update_preview_from_entry)
        
        # 批量处理区域
        process_frame = ttk.LabelFrame(main_frame, text="3. 批量处理")
        process_frame.pack(fill=tk.X, pady=5)
        
        self.process_button = ttk.Button(process_frame, text="开始批量裁剪", command=self.process_images)
        self.process_button.pack(pady=5)
        
    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.path_label.config(text=folder_path)
            self.load_first_image()

    def load_first_image(self):
        image_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        if not image_files:
            messagebox.showwarning("警告", "所选文件夹中没有找到图片文件。")
            self.image_path = None
            self.canvas.delete("all")
            return
            
        first_image_path = os.path.join(self.folder_path, image_files[0])
        self.image_path = first_image_path
        
        try:
            self.original_image = Image.open(first_image_path)
            self.display_image()
        except Exception as e:
            messagebox.showerror("错误", f"无法加载预览图片：{e}")
            
    def display_image(self):
        if not self.original_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_width, img_height = self.original_image.size
        
        # 调整图片大小以适应画布
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        self.display_ratio = ratio
        
        resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(resized_image)
        
        self.canvas.delete("all")
        
        # 居中显示图片
        x_offset = (canvas_width - new_width) / 2
        y_offset = (canvas_height - new_height) / 2
        
        self.canvas.create_image(x_offset, y_offset, image=self.photo_image, anchor=tk.NW)
        
        self.image_x_offset = x_offset
        self.image_y_offset = y_offset
        self.image_display_width = new_width
        self.image_display_height = new_height
        
        self.update_crop_lines()

    def update_crop_lines(self):
        if not self.original_image:
            return

        left = self.image_x_offset + self.left_crop.get() * self.display_ratio
        right = self.image_x_offset + self.image_display_width - self.right_crop.get() * self.display_ratio
        top = self.image_y_offset + self.top_crop.get() * self.display_ratio
        bottom = self.image_y_offset + self.image_display_height - self.bottom_crop.get() * self.display_ratio
        
        self.canvas.coords(self.left_line, left, self.image_y_offset, left, self.image_y_offset + self.image_display_height)
        self.canvas.coords(self.right_line, right, self.image_y_offset, right, self.image_y_offset + self.image_display_height)
        self.canvas.coords(self.top_line, self.image_x_offset, top, self.image_x_offset + self.image_display_width, top)
        self.canvas.coords(self.bottom_line, self.image_x_offset, bottom, self.image_x_offset + self.image_display_width, bottom)
        
    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.dragged_line = None
        
        left_coord = self.image_x_offset + self.left_crop.get() * self.display_ratio
        right_coord = self.image_x_offset + self.image_display_width - self.right_crop.get() * self.display_ratio
        top_coord = self.image_y_offset + self.top_crop.get() * self.display_ratio
        bottom_coord = self.image_y_offset + self.image_display_height - self.bottom_crop.get() * self.display_ratio

        if abs(event.x - left_coord) < 5:
            self.dragged_line = 'left'
        elif abs(event.x - right_coord) < 5:
            self.dragged_line = 'right'
        elif abs(event.y - top_coord) < 5:
            self.dragged_line = 'top'
        elif abs(event.y - bottom_coord) < 5:
            self.dragged_line = 'bottom'
            
    def do_drag(self, event):
        if not self.dragged_line:
            return
            
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        if self.dragged_line == 'left':
            new_val = max(0, self.left_crop.get() + int(dx / self.display_ratio))
            self.left_crop.set(new_val)
        elif self.dragged_line == 'right':
            new_val = max(0, self.right_crop.get() - int(dx / self.display_ratio))
            self.right_crop.set(new_val)
        elif self.dragged_line == 'top':
            new_val = max(0, self.top_crop.get() + int(dy / self.display_ratio))
            self.top_crop.set(new_val)
        elif self.dragged_line == 'bottom':
            new_val = max(0, self.bottom_crop.get() - int(dy / self.display_ratio))
            self.bottom_crop.set(new_val)
            
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def stop_drag(self, event):
        self.dragged_line = None
        self.update_crop_lines()

    def update_preview_from_entry(self, *args):
        try:
            # 确保输入框内容是数字
            self.left_crop.get()
            self.right_crop.get()
            self.top_crop.get()
            self.bottom_crop.get()
            self.update_crop_lines()
        except tk.TclError:
            pass # 忽略非数字输入

    def process_images(self):
        if not self.folder_path:
            messagebox.showwarning("警告", "请先选择图片文件夹。")
            return
            
        try:
            left = self.left_crop.get()
            right = self.right_crop.get()
            top = self.top_crop.get()
            bottom = self.bottom_crop.get()
            
            if left < 0 or right < 0 or top < 0 or bottom < 0:
                messagebox.showerror("错误", "裁剪距离不能为负数。")
                return
            
            output_folder = filedialog.askdirectory(title="选择裁剪后图片的保存路径")
            if not output_folder:
                return

        except tk.TclError:
            messagebox.showerror("错误", "裁剪距离请输入数字。")
            return
            
        self.process_button.config(state=tk.DISABLED, text="处理中...")
        self.root.update_idletasks()
        
        image_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        
        if not image_files:
            messagebox.showwarning("警告", "所选文件夹中没有找到图片文件，无法进行批量处理。")
            self.process_button.config(state=tk.NORMAL, text="开始批量裁剪")
            return

        for filename in image_files:
            try:
                img_path = os.path.join(self.folder_path, filename)
                img = Image.open(img_path)
                
                width, height = img.size
                
                # 检查裁剪距离是否过大
                if left + right >= width or top + bottom >= height:
                    messagebox.showwarning("警告", f"文件 '{filename}' 裁剪距离过大，将跳过。")
                    continue
                
                # 定义裁剪区域
                # (left, top, right, bottom)
                cropped_img = img.crop((left, top, width - right, height - bottom))
                
                # 保存裁剪后的图片
                output_path = os.path.join(output_folder, f"cropped_{filename}")
                cropped_img.save(output_path)
                
            except Exception as e:
                messagebox.showerror("错误", f"处理文件 '{filename}' 时出错：{e}")
                
        messagebox.showinfo("完成", f"所有图片已裁剪完成并保存到:\n{output_folder}")
        self.process_button.config(state=tk.NORMAL, text="开始批量裁剪")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropperApp(root)
    root.mainloop()