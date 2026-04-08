import os
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
from PIL import Image
import cv2
import numpy as np

class ImageLevelsApp:
    """
    批量色阶调整工具
    功能：将图像中低于'黑场'的像素设为0，高于'白场'的设为255，中间部分拉伸。
    """
    def __init__(self, root):
        self.root = root
        self.root.title("批量色阶调整工具")
        self.root.geometry("600x320")

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        # 默认色阶参数：黑场 0，白场 255 (即不改变)
        self.black_point = tk.StringVar(value='50')
        self.white_point = tk.StringVar(value='220')

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 路径选择
        tk.Label(main_frame, text="源文件夹:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_source_dir).grid(row=0, column=2, padx=5)

        tk.Label(main_frame, text="目标文件夹:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.dest_dir, width=60).grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_dest_dir).grid(row=1, column=2, padx=5)

        # 色阶参数
        params_frame = tk.LabelFrame(main_frame, text="色阶参数 (0-255)", padx=10, pady=10)
        params_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

        tk.Label(params_frame, text="黑场 (暗部加深):").pack(side=tk.LEFT)
        tk.Entry(params_frame, textvariable=self.black_point, width=8).pack(side=tk.LEFT, padx=5)
        
        tk.Label(params_frame, text="白场 (亮部提亮):").pack(side=tk.LEFT, padx=(20, 0))
        tk.Entry(params_frame, textvariable=self.white_point, width=8).pack(side=tk.LEFT, padx=5)

        # 开始按钮
        process_button = tk.Button(main_frame, text="开始批量处理", command=self.process_images, bg="#2196F3", fg="white")
        process_button.grid(row=3, column=1, pady=10, sticky="ew")

        # 进度条
        self.progress_frame = tk.Frame(main_frame)
        self.progress_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.progress_label = tk.Label(self.progress_frame, text="准备就绪")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        self.progressbar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        main_frame.grid_columnconfigure(1, weight=1)

    def select_source_dir(self):
        path = filedialog.askdirectory()
        if path: self.source_dir.set(path)

    def select_dest_dir(self):
        path = filedialog.askdirectory()
        if path: self.dest_dir.set(path)

    def apply_levels(self, image_np, black, white):
        """核心算法：仿照PS色阶输入"""
        # 线性拉伸公式：output = (input - black) * 255 / (white - black)
        if white <= black: white = black + 1
        
        # 使用 numpy 的 clip 和简化的线性映射
        res = (image_np.astype(float) - black) * (255.0 / (white - black))
        res = np.clip(res, 0, 255).astype(np.uint8)
        return res

    def process_images(self):
        source = self.source_dir.get()
        dest = self.dest_dir.get()
        
        try:
            bp = int(self.black_point.get())
            wp = int(self.white_point.get())
        except:
            messagebox.showerror("错误", "请输入有效的整数参数")
            return

        if not source or not dest:
            messagebox.showerror("错误", "请选择文件夹")
            return

        if not os.path.exists(dest): os.makedirs(dest)

        image_files = [f for f in os.listdir(source) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        if not image_files: return

        self.progressbar["maximum"] = len(image_files)
        
        for i, filename in enumerate(image_files):
            try:
                src_path = os.path.join(source, filename)
                dst_path = os.path.join(dest, os.path.splitext(filename)[0] + ".png")

                # 处理中文路径的读取
                with open(src_path, 'rb') as f:
                    file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)

                if img is not None:
                    # 应用色阶调整
                    processed = self.apply_levels(img, bp, wp)
                    
                    # 保存为PNG
                    is_success, im_buf = cv2.imencode(".png", processed)
                    if is_success:
                        with open(dst_path, "wb") as f:
                            f.write(im_buf.tobytes())

                self.progressbar["value"] = i + 1
                self.progress_label.config(text=f"进度: {i+1}/{len(image_files)}")
                self.root.update_idletasks()
            except Exception as e:
                print(f"Error {filename}: {e}")

        messagebox.showinfo("完成", f"已完成 {len(image_files)} 张图片的色阶处理！")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageLevelsApp(root)
    root.mainloop()