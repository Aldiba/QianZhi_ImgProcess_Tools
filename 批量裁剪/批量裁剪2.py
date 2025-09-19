import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import os

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量裁剪")
        self.root.geometry("1000x800")

        self.image_path = None
        self.original_image = None
        self.tk_image = None
        self.crop_image_display = None

        self.crop_top = tk.DoubleVar(value=0)
        self.crop_bottom = tk.DoubleVar(value=0)
        self.crop_left = tk.DoubleVar(value=0)
        self.crop_right = tk.DoubleVar(value=0)

        self.setup_ui()

    def setup_ui(self):
        # Top Frame for controls
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(control_frame, text="1. 选择待处理图片文件夹:").pack(side=tk.LEFT, padx=5)
        self.path_label = tk.Label(control_frame, text="未选择文件夹", width=50, anchor="w", relief=tk.SUNKEN)
        self.path_label.pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="浏览...", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        
        # Crop controls frame
        crop_controls_frame = tk.Frame(self.root, padx=10, pady=10)
        crop_controls_frame.pack(side=tk.TOP, fill=tk.X)

        # Labels for crop values
        tk.Label(crop_controls_frame, text="2. 裁剪参数 (像素):").pack(side=tk.LEFT, padx=5)
        tk.Label(crop_controls_frame, text="上:").pack(side=tk.LEFT, padx=5)
        self.entry_top = tk.Entry(crop_controls_frame, textvariable=self.crop_top, width=6)
        self.entry_top.pack(side=tk.LEFT, padx=5)
        
        tk.Label(crop_controls_frame, text="下:").pack(side=tk.LEFT, padx=5)
        self.entry_bottom = tk.Entry(crop_controls_frame, textvariable=self.crop_bottom, width=6)
        self.entry_bottom.pack(side=tk.LEFT, padx=5)

        tk.Label(crop_controls_frame, text="左:").pack(side=tk.LEFT, padx=5)
        self.entry_left = tk.Entry(crop_controls_frame, textvariable=self.crop_left, width=6)
        self.entry_left.pack(side=tk.LEFT, padx=5)

        tk.Label(crop_controls_frame, text="右:").pack(side=tk.LEFT, padx=5)
        self.entry_right = tk.Entry(crop_controls_frame, textvariable=self.crop_right, width=6)
        self.entry_right.pack(side=tk.LEFT, padx=5)

        tk.Button(crop_controls_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=(20, 5))

        # Preview area
        preview_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=2)
        preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)

        # Progress bar area
        progress_frame = tk.Frame(self.root, padx=10, pady=10)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.progress_label = tk.Label(progress_frame, text="等待处理...")
        self.progress_label.pack(pady=5)

        # Bind variables to update preview
        self.crop_top.trace_add("write", lambda *args: self.update_preview())
        self.crop_bottom.trace_add("write", lambda *args: self.update_preview())
        self.crop_left.trace_add("write", lambda *args: self.update_preview())
        self.crop_right.trace_add("write", lambda *args: self.update_preview())
        
        self.dragging = None
        self.drag_start_y = None
        self.drag_start_x = None

    def select_folder(self):
        self.image_path = filedialog.askdirectory()
        if self.image_path:
            self.path_label.config(text=self.image_path)
            self.load_preview_image()

    def load_preview_image(self):
        self.image_files = [os.path.join(self.image_path, f) for f in os.listdir(self.image_path)
                            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        if not self.image_files:
            messagebox.showinfo("提示", "该文件夹中没有图片文件。")
            self.original_image = None
            self.canvas.delete("all")
            return

        self.preview_path = self.image_files[0]
        self.original_image = Image.open(self.preview_path).convert("RGB")
        self.display_image(self.original_image)
    
    def display_image(self, img):
        if not img:
            return

        self.canvas.delete("all")
        
        # Resize image to fit canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_width, img_height = img.size
        
        if img_width > canvas_width or img_height > canvas_height:
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            self.scaled_width = int(img_width * ratio)
            self.scaled_height = int(img_height * ratio)
            self.scaled_image = img.resize((self.scaled_width, self.scaled_height), Image.Resampling.LANCZOS)
        else:
            self.scaled_width = img_width
            self.scaled_height = img_height
            self.scaled_image = img
            
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        
        self.x_offset = (canvas_width - self.scaled_width) // 2
        self.y_offset = (canvas_height - self.scaled_height) // 2
        
        self.image_display = self.canvas.create_image(self.x_offset, self.y_offset, anchor=tk.NW, image=self.tk_image)
        self.update_preview()

    def update_preview(self, *args):
        if not self.original_image:
            return
        
        self.canvas.delete("lines")
        self.canvas.delete("overlay")

        try:
            crop_top_scaled = int(self.crop_top.get() * (self.scaled_height / self.original_image.height))
            crop_bottom_scaled = int(self.crop_bottom.get() * (self.scaled_height / self.original_image.height))
            crop_left_scaled = int(self.crop_left.get() * (self.scaled_width / self.original_image.width))
            crop_right_scaled = int(self.crop_right.get() * (self.scaled_width / self.original_image.width))
        except ValueError:
            return # Ignore if text entry is not a number

        # Draw red overlay
        self.draw_overlay(crop_top_scaled, crop_bottom_scaled, crop_left_scaled, crop_right_scaled)

        # Draw lines
        left_line = self.x_offset + crop_left_scaled
        right_line = self.x_offset + self.scaled_width - crop_right_scaled
        top_line = self.y_offset + crop_top_scaled
        bottom_line = self.y_offset + self.scaled_height - crop_bottom_scaled

        self.canvas.create_line(left_line, self.y_offset, left_line, self.y_offset + self.scaled_height, fill="blue", width=2, tags="lines")
        self.canvas.create_line(right_line, self.y_offset, right_line, self.y_offset + self.scaled_height, fill="blue", width=2, tags="lines")
        self.canvas.create_line(self.x_offset, top_line, self.x_offset + self.scaled_width, top_line, fill="blue", width=2, tags="lines")
        self.canvas.create_line(self.x_offset, bottom_line, self.x_offset + self.scaled_width, bottom_line, fill="blue", width=2, tags="lines")

    def draw_overlay(self, top, bottom, left, right):
        overlay = Image.new('RGBA', (self.scaled_width, self.scaled_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        red = (255, 0, 0, 100) # Red with transparency
        
        # Top
        draw.rectangle([0, 0, self.scaled_width, top], fill=red)
        # Bottom
        draw.rectangle([0, self.scaled_height - bottom, self.scaled_width, self.scaled_height], fill=red)
        # Left
        draw.rectangle([0, top, left, self.scaled_height - bottom], fill=red)
        # Right
        draw.rectangle([self.scaled_width - right, top, self.scaled_width, self.scaled_height - bottom], fill=red)
        
        self.tk_overlay = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(self.x_offset, self.y_offset, image=self.tk_overlay, anchor=tk.NW, tags="overlay")
        self.canvas.tag_lower("overlay", self.image_display)

    def start_drag(self, event):
        if not self.original_image:
            return
        
        x, y = event.x, event.y
        
        top_line = self.y_offset + self.crop_top.get() * (self.scaled_height / self.original_image.height)
        bottom_line = self.y_offset + self.scaled_height - self.crop_bottom.get() * (self.scaled_height / self.original_image.height)
        left_line = self.x_offset + self.crop_left.get() * (self.scaled_width / self.original_image.width)
        right_line = self.x_offset + self.scaled_width - self.crop_right.get() * (self.scaled_width / self.original_image.width)
        
        drag_threshold = 10
        
        if abs(y - top_line) < drag_threshold:
            self.dragging = "top"
            self.drag_start_y = y
        elif abs(y - bottom_line) < drag_threshold:
            self.dragging = "bottom"
            self.drag_start_y = y
        elif abs(x - left_line) < drag_threshold:
            self.dragging = "left"
            self.drag_start_x = x
        elif abs(x - right_line) < drag_threshold:
            self.dragging = "right"
            self.drag_start_x = x
        else:
            self.dragging = None
            
    def do_drag(self, event):
        if not self.dragging or not self.original_image:
            return
            
        original_width, original_height = self.original_image.size
        
        if self.dragging == "top":
            dy = event.y - self.drag_start_y
            new_crop = self.crop_top.get() - dy * (original_height / self.scaled_height)
            self.crop_top.set(max(0, new_crop))
            self.drag_start_y = event.y
        elif self.dragging == "bottom":
            dy = self.drag_start_y - event.y
            new_crop = self.crop_bottom.get() + dy * (original_height / self.scaled_height)
            self.crop_bottom.set(max(0, new_crop))
            self.drag_start_y = event.y
        elif self.dragging == "left":
            dx = event.x - self.drag_start_x
            new_crop = self.crop_left.get() - dx * (original_width / self.scaled_width)
            self.crop_left.set(max(0, new_crop))
            self.drag_start_x = event.x
        elif self.dragging == "right":
            dx = self.drag_start_x - event.x
            new_crop = self.crop_right.get() + dx * (original_width / self.scaled_width)
            self.crop_right.set(max(0, new_crop))
            self.drag_start_x = event.x
        self.update_preview()
            
    def stop_drag(self, event):
        self.dragging = None
    
    def start_processing(self):
        if not self.image_path or not self.image_files:
            messagebox.showwarning("警告", "请先选择一个包含图片的文件夹！")
            return

        try:
            crop_top = int(self.crop_top.get())
            crop_bottom = int(self.crop_bottom.get())
            crop_left = int(self.crop_left.get())
            crop_right = int(self.crop_right.get())
        except ValueError:
            messagebox.showerror("错误", "裁剪值必须是有效的整数。")
            return

        output_dir = os.path.join(self.image_path, "processed_images")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.progress_bar["maximum"] = len(self.image_files)
        self.progress_bar["value"] = 0
        self.progress_label.config(text="开始处理...")
        self.root.update_idletasks()
        
        for i, file_path in enumerate(self.image_files):
            try:
                img = Image.open(file_path)
                
                # Get dimensions
                width, height = img.size
                
                # Crop
                left = crop_left
                top = crop_top
                right = width - crop_right
                bottom = height - crop_bottom
                
                cropped_img = img.crop((left, top, right, bottom))
                
                # Resize (to a smaller size, e.g., 50% of the cropped image)
                new_width = int(cropped_img.width * 0.5)
                new_height = int(cropped_img.height * 0.5)
                resized_img = cropped_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save
                filename = os.path.basename(file_path)
                save_path = os.path.join(output_dir, filename)
                resized_img.save(save_path)
                
                self.progress_bar["value"] = i + 1
                self.progress_label.config(text=f"处理中... ({i+1}/{len(self.image_files)})")
                self.root.update_idletasks()
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
                
        messagebox.showinfo("完成", f"所有图片已处理完成，并保存在 '{output_dir}' 文件夹中。")
        self.progress_label.config(text="处理完成！")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()