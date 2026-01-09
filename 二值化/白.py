import os
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
from PIL import Image
import cv2
import numpy as np

class ImageThresholdWhitenerApp:
    """
    一个通过Tkinter GUI对图片进行阈值白化处理的应用程序。
    高于设定阈值的像素将变为纯白色，其余像素保持不变。
    支持手动阈值和Otsu's自动阈值，并修复了中文路径问题。
    """
    def __init__(self, root):
        self.root = root
        # --- [修改] 更改窗口标题以反映新功能 ---
        self.root.title("图片去浅色工具")
        self.root.geometry("600x280")

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.threshold_val = tk.StringVar(value='240') # --- [修改] 将默认值设为240，这是一个常用的去背景/水印的阈值

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

        # --- [修改] 更新标签文本以更好地描述功能 ---
        tk.Label(main_frame, text="阈值 (高于此值的像素变白):").grid(row=2, column=0, sticky="w", pady=5)
        tk.Label(main_frame, text="输入 -1 使用 Otsu 自动阈值").grid(row=2, column=2, sticky="w", pady=5, padx=5)
        tk.Entry(main_frame, textvariable=self.threshold_val, width=10).grid(row=2, column=1, sticky="w", padx=5)


        process_button = tk.Button(main_frame, text="开始处理", command=self.process_images, bg="#4CAF50", fg="white")
        process_button.grid(row=3, column=1, pady=15, sticky="ew")

        self.progress_frame = tk.Frame(main_frame)
        self.progress_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

        self.progress_label = tk.Label(self.progress_frame, text="处理进度: 0%")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progressbar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progressbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_label = tk.Label(self.root, text="请选择路径，并设置一个阈值（例如 240）", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        main_frame.grid_columnconfigure(1, weight=1)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="选择图片源文件夹")
        if path:
            self.source_dir.set(path)
            self.status_label.config(text=f"源文件夹已选择: {path}")
            self.progressbar["value"] = 0
            self.progress_label.config(text="处理进度: 0%")

    def select_dest_dir(self):
        path = filedialog.askdirectory(title="选择保存处理后图片的文件夹")
        if path:
            self.dest_dir.set(path)
            self.status_label.config(text=f"目标文件夹已选择: {path}")

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
            try:
                os.makedirs(dest)
            except OSError as e:
                messagebox.showerror("错误", f"创建目标文件夹失败: {e}")
                return
        
        mode_text = "Otsu 自动阈值" if threshold == -1 else f"手动阈值 ({threshold})"
        self.status_label.config(text=f"正在使用 {mode_text} 模式处理中...")
        self.root.update_idletasks()

        processed_count = 0
        skipped_count = 0
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

        image_files = [f for f in os.listdir(source) if f.lower().endswith(valid_extensions)]
        total_images = len(image_files)

        if total_images == 0:
            messagebox.showinfo("信息", "源文件夹中没有找到支持的图片文件。")
            self.status_label.config(text="请选择路径，并设置一个阈值（例如 240）")
            self.progressbar["value"] = 0
            self.progress_label.config(text="处理进度: 0%")
            return

        self.progressbar["maximum"] = total_images
        self.progressbar["value"] = 0
        self.progress_label.config(text="处理进度: 0%")
        self.root.update_idletasks()

        try:
            for i, filename in enumerate(image_files):
                try:
                    source_path = os.path.join(source, filename)
                    dest_path = os.path.join(dest, filename)

                    if threshold == -1:
                        # --- Otsu's 自动阈值处理 (OpenCV) ---
                        with open(source_path, 'rb') as f:
                            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                        
                        img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
                        
                        if img_cv is None:
                            print(f"无法解码文件: {filename}，跳过。")
                            skipped_count += 1
                            continue
                        
                        # --- [核心修改] ---
                        # 1. 先用Otsu方法获取最佳阈值，但不使用它返回的二值化图像
                        otsu_threshold_val, _ = cv2.threshold(
                            img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                        )
                        
                        # 2. 创建一个原始图像的副本进行操作
                        processed_img = img_cv.copy()
                        
                        # 3. 使用Numpy的布尔索引，高效地将所有高于阈值的像素设置为255
                        #   这会保留所有低于或等于阈值的像素的原始值
                        processed_img[img_cv > otsu_threshold_val] = 255
                        # --- 修改结束 ---

                        is_success, im_buf_arr = cv2.imencode(os.path.splitext(dest_path)[1], processed_img) # 保存处理后的图像
                        if is_success:
                            with open(dest_path, "wb") as f:
                                f.write(im_buf_arr.tobytes())
                        else:
                            print(f"无法编码文件: {filename}，跳过。")
                            skipped_count += 1
                            continue

                    else:
                        # --- 手动阈值处理 (Pillow) ---
                        with Image.open(source_path) as img:
                            grayscale_img = img.convert('L')
                            # --- [核心修改] ---
                            # 使用 lambda 函数：如果像素值 p > threshold，则变为 255 (白色)
                            # 否则 (p <= threshold)，保持其原始值 p
                            # 注意：不再指定输出模式为 '1' (1-bit)，因为结果是灰度图
                            processed_img = grayscale_img.point(lambda p: 255 if p > threshold else p)
                            # --- 修改结束 ---
                            processed_img.save(dest_path)
                    
                    processed_count += 1
                except Exception as e:
                    print(f"处理文件 {filename} 时出错: {e}")
                    skipped_count += 1
                
                current_progress = i + 1
                self.progressbar["value"] = current_progress
                percentage = int((current_progress / total_images) * 100)
                self.progress_label.config(text=f"处理进度: {percentage}% ({current_progress}/{total_images})")
                self.root.update_idletasks()

            final_message = f"处理完成！成功处理 {processed_count} 个图片，跳过 {skipped_count} 个文件。"
            self.status_label.config(text=final_message)
            messagebox.showinfo("完成", final_message)

        except Exception as e:
            error_message = f"处理过程中发生未知错误: {e}"
            self.status_label.config(text="处理失败！")
            messagebox.showerror("错误", error_message)
        finally:
            self.progressbar["value"] = 0
            self.progress_label.config(text="处理进度: 0%")
            self.status_label.config(text="请选择路径，并设置一个阈值（例如 240）")
            self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageThresholdWhitenerApp(root)
    root.mainloop()