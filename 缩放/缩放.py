import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量缩放工具 (联动锁定版)")
        self.root.geometry("500x450")

        # 变量存储
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.keep_aspect = tk.BooleanVar(value=True)
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()
        
        # 存储原始比例 (宽/高)
        self.aspect_ratio = 1.0
        self.is_updating = False # 防止死循环更新
        self.supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

        # 绑定监听事件：当字符改变时触发
        self.width_var.trace_add("write", lambda *args: self.on_width_change())
        self.height_var.trace_add("write", lambda *args: self.on_height_change())

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="1. 选择输入文件夹 (自动获取首图尺寸):", fg="blue").pack(pady=(15, 0))
        entry_frame1 = tk.Frame(self.root)
        entry_frame1.pack(fill='x', padx=20)
        tk.Entry(entry_frame1, textvariable=self.input_path).pack(side='left', fill='x', expand=True)
        tk.Button(entry_frame1, text="浏览", command=self.select_input).pack(side='right')

        tk.Label(self.root, text="2. 选择输出文件夹:").pack(pady=(10, 0))
        entry_frame2 = tk.Frame(self.root)
        entry_frame2.pack(fill='x', padx=20)
        tk.Entry(entry_frame2, textvariable=self.output_path).pack(side='left', fill='x', expand=True)
        tk.Button(entry_frame2, text="浏览", command=self.select_output).pack(side='right')

        settings_frame = tk.LabelFrame(self.root, text="尺寸与比例设置", padx=10, pady=10)
        settings_frame.pack(pady=20, padx=20, fill='x')

        tk.Label(settings_frame, text="宽度 (X):").grid(row=0, column=0)
        tk.Entry(settings_frame, textvariable=self.width_var, width=12).grid(row=0, column=1, padx=5)

        tk.Label(settings_frame, text="高度 (Y):").grid(row=0, column=2)
        tk.Entry(settings_frame, textvariable=self.height_var, width=12).grid(row=0, column=3, padx=5)

        tk.Checkbutton(settings_frame, text="锁定宽高比 (XY连锁)", variable=self.keep_aspect).grid(row=1, columnspan=4, pady=10)

        tk.Button(self.root, text="开始批量处理", bg="#2196F3", fg="white", font=('Arial', 12, 'bold'), command=self.process_images).pack(pady=10)

    def select_input(self):
        path = filedialog.askdirectory()
        if path:
            self.input_path.set(path)
            self.auto_fill_dimensions(path)

    def auto_fill_dimensions(self, path):
        try:
            files = sorted(os.listdir(path))
            for filename in files:
                if filename.lower().endswith(self.supported_formats):
                    img_path = os.path.join(path, filename)
                    with Image.open(img_path) as img:
                        w, h = img.size
                        self.aspect_ratio = w / h
                        # 暂时关闭监听避免联动错误
                        self.is_updating = True
                        self.width_var.set(str(w))
                        self.height_var.set(str(h))
                        self.is_updating = False
                    break
        except Exception as e:
            print(f"提取尺寸失败: {e}")

    def on_width_change(self):
        if self.keep_aspect.get() and not self.is_updating:
            try:
                self.is_updating = True
                new_w = float(self.width_var.get())
                new_h = int(new_w / self.aspect_ratio)
                self.height_var.set(str(new_h))
            except: pass
            finally: self.is_updating = False

    def on_height_change(self):
        if self.keep_aspect.get() and not self.is_updating:
            try:
                self.is_updating = True
                new_h = float(self.height_var.get())
                new_w = int(new_h * self.aspect_ratio)
                self.width_var.set(str(new_w))
            except: pass
            finally: self.is_updating = False

    def select_output(self):
        path = filedialog.askdirectory()
        if path: self.output_path.set(path)

    def process_images(self):
        # ... (此处逻辑与之前一致，按设置的 width/height 变量执行缩放)
        in_dir = self.input_path.get()
        out_dir = self.output_path.get()
        if not in_dir or not out_dir:
            messagebox.showerror("错误", "请选择文件夹")
            return

        try:
            tw, th = int(self.width_var.get()), int(self.height_var.get())
            for filename in os.listdir(in_dir):
                if filename.lower().endswith(self.supported_formats):
                    with Image.open(os.path.join(in_dir, filename)) as img:
                        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                        # 如果是锁定模式，我们用resize确保所有图都变成基准图一样的尺寸
                        # 如果不锁，也是resize到指定尺寸
                        res_img = img.resize((tw, th), Image.Resampling.LANCZOS)
                        res_img.save(os.path.join(out_dir, filename))
            messagebox.showinfo("成功", "批量缩放完成！")
        except Exception as e:
            messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()