import os
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
from PIL import Image
import cv2
import numpy as np

class ImageBinarizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片二值化工具 (统一输出PNG灰度)")
        self.root.geometry("600x280")

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.threshold_val = tk.StringVar(value='-1')

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="源文件夹:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_source_dir).grid(row=0, column=2, padx=5)

        tk.Label(main_frame, text="目标文件夹:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.dest_dir, width=60).grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_dest_dir).grid(row=1, column=2, padx=5)

        tk.Label(main_frame, text="阈值 (-1 为 Otsu 自动阈值):").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.threshold_val, width=10).grid(row=2, column=1, sticky="w", padx=5)

        process_button = tk.Button(main_frame, text="开始处理", command=self.process_images, bg="#4CAF50", fg="white")
        process_button.grid(row=3, column=1, pady=15, sticky="ew")

        self.progress_frame = tk.Frame(main_frame)
        self.progress_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

        self.progress_label = tk.Label(self.progress_frame, text="处理进度: 0%")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progressbar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_label = tk.Label(self.root, text="请选择路径，输出将统一为PNG灰度图", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="选择图片源文件夹")
        if path:
            self.source_dir.set(path)
            self.progressbar["value"] = 0
            self.progress_label.config(text="处理进度: 0%")

    def select_dest_dir(self):
        path = filedialog.askdirectory(title="选择保存处理后图片的文件夹")
        if path:
            self.dest_dir.set(path)

    def process_images(self):
        source = self.source_dir.get()
        dest = self.dest_dir.get()

        if not source or not dest:
            messagebox.showerror("错误", "请确保已选择源文件夹和目标文件夹！")
            return

        try:
            threshold = int(self.threshold_val.get())
            if threshold != -1 and not 0 <= threshold <= 255:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "阈值必须是 -1 或 0 到 255 之间的整数！")
            return

        if not os.path.exists(dest):
            os.makedirs(dest)
        
        image_files = [f for f in os.listdir(source) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
        total_images = len(image_files)

        if total_images == 0:
            messagebox.showinfo("信息", "没有找到支持的图片文件。")
            return

        self.progressbar["maximum"] = total_images
        processed_count = 0
        skipped_count = 0

        for i, filename in enumerate(image_files):
            try:
                source_path = os.path.join(source, filename)
                # --- 修改点1：强制输出文件名为 .png ---
                base_name = os.path.splitext(filename)[0]
                dest_path = os.path.join(dest, base_name + ".png")

                if threshold == -1:
                    # OpenCV 处理
                    with open(source_path, 'rb') as f:
                        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                    img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
                    
                    if img_cv is None:
                        skipped_count += 1
                        continue
                    
                    _, binarized_img = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                    # --- 修改点2：OpenCV 编码为 .png ---
                    is_success, im_buf_arr = cv2.imencode(".png", binarized_img)
                    if is_success:
                        with open(dest_path, "wb") as f:
                            f.write(im_buf_arr.tobytes())
                else:
                    # Pillow 处理
                    with Image.open(source_path) as img:
                        grayscale_img = img.convert('L')
                        # 得到二值图 (模式 '1')
                        binarized_img = grayscale_img.point(lambda p: 255 if p > threshold else 0, '1')
                        # --- 修改点3：转回 'L' 模式以确保保存为 8位灰度 PNG ---
                        final_img = binarized_img.convert('L')
                        final_img.save(dest_path, "PNG")

                processed_count += 1
            except Exception as e:
                print(f"处理 {filename} 出错: {e}")
                skipped_count += 1
            
            # 更新进度
            self.progressbar["value"] = i + 1
            self.progress_label.config(text=f"处理进度: {int(((i+1)/total_images)*100)}% ({i+1}/{total_images})")
            self.root.update_idletasks()

        messagebox.showinfo("完成", f"成功处理 {processed_count} 个文件，全部保存为 PNG 灰度图。")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBinarizerApp(root)
    root.mainloop()