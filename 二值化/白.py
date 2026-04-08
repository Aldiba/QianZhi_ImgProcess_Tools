import os
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
from PIL import Image
import cv2
import numpy as np

class ImageThresholdWhitenerApp:
    """
    一个通过Tkinter GUI对图片进行双向阈值处理的应用程序。
    - 白阈值：高于设定值的像素变为纯白（去底色）。
    - 黑阈值：低于设定值的像素变为纯黑（加深文字）。
    支持手动阈值和Otsu's自动阈值。
    """
    def __init__(self, root):
        self.root = root
        self.root.title("图片去底色 & 文字加深工具") # --- [修改] 标题更新
        self.root.geometry("600x320") # --- [修改] 增加高度以容纳新选项

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        
        # --- [修改] 初始化两个阈值变量 ---
        self.white_threshold_val = tk.StringVar(value='240') # 默认去底色阈值
        self.black_threshold_val = tk.StringVar(value='30')  # 默认加深文字阈值 (建议值 10-50)

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 第一行：源文件夹
        tk.Label(main_frame, text="源文件夹:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.source_dir, width=55).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_source_dir).grid(row=0, column=2, padx=5)

        # 第二行：目标文件夹
        tk.Label(main_frame, text="目标文件夹:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.dest_dir, width=55).grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(main_frame, text="选择...", command=self.select_dest_dir).grid(row=1, column=2, padx=5)

        # --- [修改] 第三行：白阈值设置 ---
        tk.Label(main_frame, text="白阈值 (高于此值变白):").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.white_threshold_val, width=10).grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(main_frame, text="(-1 为 Otsu 自动，建议 230-250)").grid(row=2, column=1, sticky="e", padx=50) # 说明文字

        # --- [新增] 第四行：黑阈值设置 ---
        tk.Label(main_frame, text="黑阈值 (低于此值变黑):").grid(row=3, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.black_threshold_val, width=10).grid(row=3, column=1, sticky="w", padx=5)
        tk.Label(main_frame, text="(0 为不处理，建议 10-50)").grid(row=3, column=1, sticky="e", padx=50)

        # 第五行：按钮
        process_button = tk.Button(main_frame, text="开始处理", command=self.process_images, bg="#4CAF50", fg="white")
        process_button.grid(row=4, column=1, pady=15, sticky="ew")

        # 进度条区域
        self.progress_frame = tk.Frame(main_frame)
        self.progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)

        self.progress_label = tk.Label(self.progress_frame, text="处理进度: 0%")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progressbar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_label = tk.Label(self.root, text="设置：白阈值去底色，黑阈值加深文字", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="选择图片源文件夹")
        if path:
            self.source_dir.set(path)
            self.status_label.config(text=f"源文件夹已选择: {path}")

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

        # --- [修改] 获取并校验两个阈值 ---
        try:
            w_thresh = int(self.white_threshold_val.get())
            b_thresh = int(self.black_threshold_val.get())
            
            if (w_thresh != -1 and not 0 <= w_thresh <= 255) or not 0 <= b_thresh <= 255:
                raise ValueError
            
            if w_thresh != -1 and b_thresh >= w_thresh:
                 messagebox.showwarning("警告", "黑阈值必须小于白阈值，否则图像可能全黑或全白！")
                 return

        except ValueError:
            messagebox.showerror("错误", "阈值必须是整数！\n白阈值: -1 或 0-255\n黑阈值: 0-255")
            return

        if not os.path.exists(dest):
            try:
                os.makedirs(dest)
            except OSError as e:
                messagebox.showerror("错误", f"创建目标文件夹失败: {e}")
                return
        
        mode_text = "Otsu 自动白阈值" if w_thresh == -1 else f"手动白阈值 ({w_thresh})"
        self.status_label.config(text=f"模式: {mode_text} + 黑阈值 ({b_thresh})...")
        self.root.update_idletasks()

        processed_count = 0
        skipped_count = 0
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
        image_files = [f for f in os.listdir(source) if f.lower().endswith(valid_extensions)]
        total_images = len(image_files)

        if total_images == 0:
            messagebox.showinfo("信息", "源文件夹中没有找到图片。")
            return

        self.progressbar["maximum"] = total_images
        self.progressbar["value"] = 0

        try:
            for i, filename in enumerate(image_files):
                try:
                    source_path = os.path.join(source, filename)
                    dest_path = os.path.join(dest, filename)

                    # 逻辑分支：Otsu 模式使用 OpenCV，手动模式使用 Pillow
                    if w_thresh == -1:
                        # --- OpenCV 处理 (Otsu + 手动黑阈值) ---
                        with open(source_path, 'rb') as f:
                            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                        img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
                        
                        if img_cv is None: 
                            raise Exception("解码失败")

                        # 1. 计算 Otsu 白阈值
                        otsu_val, _ = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                        processed_img = img_cv.copy()
                        
                        # 2. 应用白阈值 (高于 Otsu 值的变 255)
                        processed_img[img_cv > otsu_val] = 255
                        
                        # 3. [新增] 应用黑阈值 (低于 b_thresh 的变 0)
                        if b_thresh > 0:
                            processed_img[img_cv < b_thresh] = 0

                        is_success, im_buf_arr = cv2.imencode(os.path.splitext(dest_path)[1], processed_img)
                        if is_success:
                            with open(dest_path, "wb") as f:
                                f.write(im_buf_arr.tobytes())

                    else:
                        # --- Pillow 处理 (手动白阈值 + 手动黑阈值) ---
                        with Image.open(source_path) as img:
                            grayscale_img = img.convert('L')
                            
                            # --- [新增] 双向归一化 Lambda 函数 ---
                            # 逻辑：如果 p > 白阈值 -> 255
                            #       否则如果 p < 黑阈值 -> 0
                            #       否则 -> 保持 p
                            processed_img = grayscale_img.point(
                                lambda p: 255 if p > w_thresh else (0 if p < b_thresh else p)
                            )
                            processed_img.save(dest_path)
                    
                    processed_count += 1
                except Exception as e:
                    print(f"Error {filename}: {e}")
                    skipped_count += 1
                
                # 更新进度
                current_progress = i + 1
                self.progressbar["value"] = current_progress
                percentage = int((current_progress / total_images) * 100)
                self.progress_label.config(text=f"处理进度: {percentage}%")
                self.root.update_idletasks()

            messagebox.showinfo("完成", f"成功: {processed_count}，跳过: {skipped_count}")

        except Exception as e:
            messagebox.showerror("错误", f"发生错误: {e}")
        finally:
            self.progressbar["value"] = 0
            self.progress_label.config(text="处理进度: 0%")
            self.status_label.config(text="就绪")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageThresholdWhitenerApp(root)
    root.mainloop()