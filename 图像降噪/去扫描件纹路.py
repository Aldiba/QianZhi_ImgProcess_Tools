import cv2
import numpy as np
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# --- 核心处理逻辑 ---

def clean_manga_scan(image_path, output_path, denoise_strength=10, white_threshold_percentile=90, log_callback=None):
    """
    去除扫描漫画的纸纹和噪点。
    """
    try:
        # 1. 读取图片
        # 尝试处理中文路径问题 (OpenCV直接读取中文路径在某些系统会失败，用imdecode代替)
        try:
            img_data = np.fromfile(image_path, dtype=np.uint8)
            img = cv2.imdecode(img_data, cv2.IMREAD_GRAYSCALE)
        except Exception:
            # 回退到普通读取
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            if log_callback: log_callback(f"错误: 无法读取图片 {os.path.basename(image_path)}")
            return False

        # 2. 降噪 (Denoising)
        # h: 决定过滤器强度的参数。
        denoised = cv2.fastNlMeansDenoising(img, None, h=denoise_strength, templateWindowSize=7, searchWindowSize=21)

        # 3. 自动色阶 / 漂白纸纹
        # 计算像素亮度的直方图百分位
        black_point = np.percentile(denoised, 5)   
        white_point = np.percentile(denoised, white_threshold_percentile)

        # 防止除以零或阈值倒挂
        if white_point <= black_point:
            white_point = 255
            black_point = 0

        # 限制范围并拉伸对比度
        clipped = np.clip(denoised, black_point, white_point)
        
        # 归一化到 0-255
        # 注意: 使用 float 运算防止溢出，最后转回 uint8
        normalized = ((clipped - black_point) / (white_point - black_point) * 255).astype(np.uint8)

        # 4. (可选) 锐化线条
        kernel = np.array([[-1,-1,-1], 
                           [-1, 9,-1], 
                           [-1,-1,-1]])
        sharpened = cv2.filter2D(normalized, -1, kernel)
        final_img = cv2.addWeighted(normalized, 0.7, sharpened, 0.3, 0)

        # 5. 保存结果
        # 处理中文路径保存问题
        is_success, im_buf = cv2.imencode(os.path.splitext(output_path)[1], final_img)
        if is_success:
            im_buf.tofile(output_path)
            if log_callback: log_callback(f"成功: {os.path.basename(output_path)}")
            return True
        else:
            if log_callback: log_callback(f"保存失败: {os.path.basename(output_path)}")
            return False

    except Exception as e:
        if log_callback: log_callback(f"处理异常 {os.path.basename(image_path)}: {str(e)}")
        return False

# --- GUI 界面类 ---

class MangaCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("漫画扫描图去噪工具 (Manga Cleaner)")
        self.root.geometry("650x600")
        
        # 样式设置
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=5)

        # 变量
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.denoise_val = tk.IntVar(value=10)
        self.white_threshold_val = tk.IntVar(value=85)
        self.is_processing = False

        self._init_ui()

    def _init_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 文件夹选择区域
        folder_frame = ttk.LabelFrame(main_frame, text="文件夹设置", padding="10")
        folder_frame.pack(fill=tk.X, pady=5)

        # 输入文件夹
        ttk.Label(folder_frame, text="输入文件夹:").grid(row=0, column=0, sticky="w")
        ttk.Entry(folder_frame, textvariable=self.input_dir, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(folder_frame, text="浏览...", command=self.select_input_dir).grid(row=0, column=2)

        # 输出文件夹
        ttk.Label(folder_frame, text="输出文件夹:").grid(row=1, column=0, sticky="w")
        ttk.Entry(folder_frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(folder_frame, text="浏览...", command=self.select_output_dir).grid(row=1, column=2)

        # 2. 参数设置区域
        param_frame = ttk.LabelFrame(main_frame, text="参数调整", padding="10")
        param_frame.pack(fill=tk.X, pady=10)

        # 降噪强度滑块
        ttk.Label(param_frame, text="降噪强度 (Denoise):").grid(row=0, column=0, sticky="w")
        self.denoise_scale = ttk.Scale(param_frame, from_=0, to=30, orient=tk.HORIZONTAL, variable=self.denoise_val, command=lambda v: self.denoise_label.config(text=f"{int(float(v))}"))
        self.denoise_scale.grid(row=0, column=1, sticky="ew", padx=10)
        self.denoise_label = ttk.Label(param_frame, text=str(self.denoise_val.get()), width=4)
        self.denoise_label.grid(row=0, column=2)
        ttk.Label(param_frame, text="(越大越平滑，但也可能糊掉细节。推荐 5-15)", foreground="gray", font=("", 8)).grid(row=1, column=1, sticky="w", padx=10)

        # 白点阈值滑块
        ttk.Label(param_frame, text="白点阈值 (Threshold):").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.white_scale = ttk.Scale(param_frame, from_=50, to=99, orient=tk.HORIZONTAL, variable=self.white_threshold_val, command=lambda v: self.white_label.config(text=f"{int(float(v))}%"))
        self.white_scale.grid(row=2, column=1, sticky="ew", padx=10, pady=(10, 0))
        self.white_label = ttk.Label(param_frame, text=str(self.white_threshold_val.get())+"%", width=4)
        self.white_label.grid(row=2, column=2, pady=(10, 0))
        ttk.Label(param_frame, text="(百分比越小画面越亮/白。推荐 80-95%)", foreground="gray", font=("", 8)).grid(row=3, column=1, sticky="w", padx=10)

        # 3. 进度和日志
        progress_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.log_text = scrolledtext.ScrolledText(progress_frame, height=10, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 4. 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="开始处理", command=self.start_processing_thread)
        self.start_btn.pack(side=tk.RIGHT, padx=5)
        
        # 链接Grid列权重
        folder_frame.columnconfigure(1, weight=1)
        param_frame.columnconfigure(1, weight=1)

    def select_input_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)
            # 自动设置输出目录为 输入目录_clean
            if not self.output_dir.get():
                self.output_dir.set(path + "_clean")

    def select_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_processing_thread(self):
        if self.is_processing:
            return
        
        input_path = self.input_dir.get()
        output_path = self.output_dir.get()

        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("错误", "请选择有效的输入文件夹")
            return
        
        if not output_path:
            messagebox.showerror("错误", "请设置输出文件夹")
            return

        self.is_processing = True
        self.start_btn.config(state='disabled')
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
        # 在新线程中运行，防止界面卡死
        threading.Thread(target=self.run_processing, args=(input_path, output_path), daemon=True).start()

    def run_processing(self, input_path, output_path):
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                self.root.after(0, self.log, f"创建输出目录: {output_path}")

            # 支持的图片格式
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
            files = [f for f in os.listdir(input_path) if os.path.splitext(f.lower())[1] in valid_extensions]
            
            total_files = len(files)
            if total_files == 0:
                self.root.after(0, self.log, "错误: 输入文件夹中没有找到支持的图片文件。")
                self.root.after(0, self.finish_processing)
                return

            self.root.after(0, self.log, f"找到 {total_files} 个文件，准备开始...")
            
            denoise = self.denoise_val.get()
            white_thresh = self.white_threshold_val.get()

            for i, filename in enumerate(files):
                in_file = os.path.join(input_path, filename)
                out_file = os.path.join(output_path, filename)
                
                # 调用处理函数
                clean_manga_scan(
                    in_file, 
                    out_file, 
                    denoise_strength=denoise, 
                    white_threshold_percentile=white_thresh,
                    log_callback=lambda msg: self.root.after(0, self.log, msg)
                )
                
                # 更新进度条
                progress = (i + 1) / total_files * 100
                self.root.after(0, self.update_progress, progress)

            self.root.after(0, self.log, "--- 全部处理完成! ---")
            self.root.after(0, lambda: messagebox.showinfo("完成", f"处理完成！\n共处理 {total_files} 张图片。"))

        except Exception as e:
            self.root.after(0, self.log, f"发生未知错误: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        
        finally:
            self.root.after(0, self.finish_processing)

    def update_progress(self, val):
        self.progress_bar['value'] = val

    def finish_processing(self):
        self.is_processing = False
        self.start_btn.config(state='normal')


if __name__ == "__main__":
    root = tk.Tk()
    # 尝试设置Windows高分屏支持，防止界面模糊
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = MangaCleanerApp(root)
    root.mainloop()