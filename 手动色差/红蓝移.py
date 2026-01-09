import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import cv2
import numpy as np
import threading
import queue

class ChromaticAberrationFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("漫画扫描色差校正工具")
        self.root.geometry("600x550")

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.log_queue = queue.Queue()

        # --- UI 布局 ---
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 文件夹选择
        dir_frame = tk.LabelFrame(main_frame, text="1. 选择文件夹", padx=10, pady=10)
        dir_frame.pack(fill=tk.X, pady=5)

        tk.Button(dir_frame, text="选择输入文件夹", command=self.select_input_dir).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.input_label = tk.Label(dir_frame, text="未选择", bg="white", anchor="w", relief="sunken")
        self.input_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Button(dir_frame, text="选择输出文件夹", command=self.select_output_dir).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.output_label = tk.Label(dir_frame, text="未选择", bg="white", anchor="w", relief="sunken")
        self.output_label.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        dir_frame.grid_columnconfigure(1, weight=1)

        # 参数调整
        param_frame = tk.LabelFrame(main_frame, text="2. 调整校正参数", padx=10, pady=10)
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text="红通道缩放:").grid(row=0, column=0, sticky="w")
        self.r_scale = tk.Scale(param_frame, from_=0.998, to=1.002, resolution=0.0001, orient=tk.HORIZONTAL)
        self.r_scale.set(0.9995)
        self.r_scale.grid(row=0, column=1, sticky="ew")

        tk.Label(param_frame, text="蓝通道缩放:").grid(row=1, column=0, sticky="w")
        self.b_scale = tk.Scale(param_frame, from_=0.998, to=1.002, resolution=0.0001, orient=tk.HORIZONTAL)
        self.b_scale.set(1.0005)
        self.b_scale.grid(row=1, column=1, sticky="ew")
        
        param_frame.grid_columnconfigure(1, weight=1)

        # 开始处理
        action_frame = tk.LabelFrame(main_frame, text="3. 开始处理", padx=10, pady=10)
        action_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = tk.Button(action_frame, text="开始处理", command=self.start_processing_thread, font=("Helvetica", 12, "bold"))
        self.start_button.pack(fill=tk.X, ipady=5)

        # 日志输出
        log_frame = tk.LabelFrame(main_frame, text="处理日志", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')
        
        self.root.after(100, self.process_log_queue)

    def select_input_dir(self):
        path = filedialog.askdirectory(title="选择包含图片的文件夹")
        if path:
            self.input_dir.set(path)
            self.input_label.config(text=path)

    def select_output_dir(self):
        path = filedialog.askdirectory(title="选择保存结果的文件夹")
        if path:
            self.output_dir.set(path)
            self.output_label.config(text=path)
            
    def log(self, message):
        """将日志消息放入队列"""
        self.log_queue.put(message)

    def process_log_queue(self):
        """从队列中处理并显示日志消息"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.see(tk.END) # 自动滚动到底部
                self.log_text.configure(state='disabled')
        except queue.Empty:
            self.root.after(100, self.process_log_queue)


    def start_processing_thread(self):
        input_path = self.input_dir.get()
        output_path = self.output_dir.get()

        if not input_path or not output_path:
            messagebox.showerror("错误", "请先选择输入和输出文件夹！")
            return
        if input_path == output_path:
            messagebox.showwarning("警告", "输入和输出文件夹不能是同一个，请重新选择输出文件夹。")
            return

        self.start_button.config(state="disabled", text="正在处理中...")
        
        # 创建并启动处理线程
        processing_thread = threading.Thread(
            target=self.process_images, 
            args=(input_path, output_path, self.r_scale.get(), self.b_scale.get()),
            daemon=True
        )
        processing_thread.start()

    def process_images(self, input_dir, output_dir, r_scale, b_scale):
        self.log("="*20)
        self.log(f"开始处理任务...")
        self.log(f"输入文件夹: {input_dir}")
        self.log(f"输出文件夹: {output_dir}")
        self.log(f"红通道缩放: {r_scale}, 蓝通道缩放: {b_scale}")
        self.log("="*20)

        os.makedirs(output_dir, exist_ok=True)
        
        image_count = 0
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')

        for root, _, files in os.walk(input_dir):
            for filename in files:
                if filename.lower().endswith(supported_formats):
                    image_count += 1
                    input_image_path = os.path.join(root, filename)
                    
                    # 创建与输入目录结构相同的子目录
                    relative_path = os.path.relpath(root, input_dir)
                    output_sub_dir = os.path.join(output_dir, relative_path)
                    os.makedirs(output_sub_dir, exist_ok=True)
                    output_image_path = os.path.join(output_sub_dir, filename)

                    self.log(f"处理中: {filename}")
                    try:
                        self.correct_aberration(input_image_path, output_image_path, r_scale, b_scale)
                    except Exception as e:
                        self.log(f"  [错误] 处理 {filename} 失败: {e}")

        self.log("="*20)
        self.log(f"处理完成！共处理了 {image_count} 张图片。")
        self.log("="*20)
        
        # 在主线程中更新UI
        self.root.after(0, self.on_processing_done)

    def on_processing_done(self):
        messagebox.showinfo("完成", "所有图片已处理完毕！")
        self.start_button.config(state="normal", text="开始处理")

    def scale_channel(self, channel, scale_factor):
        """按中心缩放单个颜色通道"""
        height, width = channel.shape[:2]
        
        # 计算新的尺寸
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # 缩放
        scaled = cv2.resize(channel, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

        # 从中心裁剪回原始尺寸
        x_start = (new_width - width) // 2
        y_start = (new_height - height) // 2
        
        return scaled[y_start:y_start+height, x_start:x_start+width]

    def correct_aberration(self, input_path, output_path, r_scale, b_scale):
        # 使用 numpy.fromfile 和 cv2.imdecode 来读取包含非ASCII字符（如中文）的路径
        img_np = np.fromfile(input_path, dtype=np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if img is None:
            raise IOError("无法读取图像文件，请检查文件是否损坏或路径是否正确。")

        # OpenCV默认通道顺序是 B, G, R
        b_channel, g_channel, r_channel = cv2.split(img)

        # 以G通道为基准，缩放R和B通道
        corrected_r = self.scale_channel(r_channel, r_scale)
        corrected_b = self.scale_channel(b_channel, b_scale)

        # 合并通道
        corrected_img = cv2.merge([corrected_b, g_channel, corrected_r])

        # 使用 cv2.imencode 和 tofile 来保存到包含非ASCII字符的路径
        is_success, buffer = cv2.imencode(os.path.splitext(output_path)[1], corrected_img)
        if is_success:
            with open(output_path, 'wb') as f:
                f.write(buffer)
        else:
            raise IOError(f"无法编码图像到路径: {output_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChromaticAberrationFixerApp(root)
    root.mainloop()