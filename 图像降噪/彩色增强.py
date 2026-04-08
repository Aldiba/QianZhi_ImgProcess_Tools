import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading

class ScanEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("彩色扫描件批量增强工具 v1.0")
        self.root.geometry("900x700")
        
        # 变量初始化
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.processing = False
        
        # 增强参数
        self.brightness = tk.DoubleVar(value=0)      # -100 到 100
        self.contrast = tk.DoubleVar(value=1.2)      # 0 到 3
        self.gamma = tk.DoubleVar(value=1.0)         # 0.1 到 3.0
        self.clahe_clip = tk.DoubleVar(value=2.0)    # CLAHE对比度限制
        self.clahe_grid = tk.IntVar(value=8)         # CLAHE网格大小
        
        self.setup_ui()
    
    def read_image_chinese_path(self, image_path):
        """
        支持中文路径的图像读取函数
        """
        try:
            # 方法1: 使用numpy从文件读取
            with open(image_path, 'rb') as f:
                img_array = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            # 方法1失败时尝试方法2
            if img is None:
                # 方法2: 使用PIL读取然后转换
                pil_img = Image.open(image_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            return img
        except Exception as e:
            print(f"读取图像失败 {image_path}: {e}")
            return None
    
    def save_image_chinese_path(self, image, save_path, quality=95):
        """
        支持中文路径的图像保存函数
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(save_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 获取文件扩展名
            ext = os.path.splitext(save_path)[1].lower()
            
            # 使用cv2.imencode编码保存
            if ext in ['.jpg', '.jpeg']:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                success, buffer = cv2.imencode(ext, image, encode_param)
            elif ext == '.png':
                encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                success, buffer = cv2.imencode(ext, image, encode_param)
            else:
                success, buffer = cv2.imencode(ext, image)
            
            if success:
                # 将编码后的图像写入文件
                with open(save_path, 'wb') as f:
                    f.write(buffer.tobytes())
                return True
            else:
                # 备选方案：使用PIL保存
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
                pil_image.save(save_path)
                return True
                
        except Exception as e:
            print(f"保存图像失败 {save_path}: {e}")
            return False
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 输入输出路径选择
        ttk.Label(main_frame, text="输入目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_dir, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.select_input_dir).grid(row=0, column=2)
        
        ttk.Label(main_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.select_output_dir).grid(row=1, column=2)
        
        # 参数控制区域
        params_frame = ttk.LabelFrame(main_frame, text="增强参数", padding="10")
        params_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 亮度调整
        ttk.Label(params_frame, text="亮度:").grid(row=0, column=0, sticky=tk.W)
        ttk.Scale(params_frame, from_=-100, to=100, variable=self.brightness, 
                  orient=tk.HORIZONTAL, length=200).grid(row=0, column=1, padx=5)
        ttk.Label(params_frame, textvariable=self.brightness).grid(row=0, column=2)
        
        # 对比度调整
        ttk.Label(params_frame, text="对比度:").grid(row=1, column=0, sticky=tk.W)
        ttk.Scale(params_frame, from_=0.1, to=3.0, variable=self.contrast,
                  orient=tk.HORIZONTAL, length=200).grid(row=1, column=1, padx=5)
        ttk.Label(params_frame, textvariable=self.contrast).grid(row=1, column=2)
        
        # 伽马校正
        ttk.Label(params_frame, text="伽马值:").grid(row=2, column=0, sticky=tk.W)
        ttk.Scale(params_frame, from_=0.1, to=3.0, variable=self.gamma,
                  orient=tk.HORIZONTAL, length=200).grid(row=2, column=1, padx=5)
        ttk.Label(params_frame, textvariable=self.gamma).grid(row=2, column=2)
        
        # CLAHE参数
        ttk.Label(params_frame, text="CLAHE对比度限制:").grid(row=3, column=0, sticky=tk.W)
        ttk.Scale(params_frame, from_=1.0, to=4.0, variable=self.clahe_clip,
                  orient=tk.HORIZONTAL, length=200).grid(row=3, column=1, padx=5)
        ttk.Label(params_frame, textvariable=self.clahe_clip).grid(row=3, column=2)
        
        ttk.Label(params_frame, text="CLAHE网格大小:").grid(row=4, column=0, sticky=tk.W)
        ttk.Scale(params_frame, from_=4, to=16, variable=self.clahe_grid,
                  orient=tk.HORIZONTAL, length=200).grid(row=4, column=1, padx=5)
        ttk.Label(params_frame, textvariable=self.clahe_grid).grid(row=4, column=2)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="效果预览", padding="10")
        preview_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.original_label = ttk.Label(preview_frame, text="原始图像")
        self.original_label.grid(row=0, column=0, padx=10)
        
        self.enhanced_label = ttk.Label(preview_frame, text="增强后图像")
        self.enhanced_label.grid(row=0, column=1, padx=10)
        
        # 控制按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text="预览效果", command=self.preview_enhancement).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="开始批量处理", command=self.start_batch_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="停止", command=self.stop_processing).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.grid(row=6, column=0, columnspan=3)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def select_input_dir(self):
        dir_path = filedialog.askdirectory(title="选择输入目录")
        if dir_path:
            self.input_dir.set(dir_path)
            # 自动加载第一张图片预览
            self.load_first_image_for_preview()
    
    def select_output_dir(self):
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir.set(dir_path)
    
    def load_first_image_for_preview(self):
        """加载第一张图片用于预览"""
        input_dir = self.input_dir.get()
        if not os.path.exists(input_dir):
            return
            
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        for file in os.listdir(input_dir):
            if file.lower().endswith(image_extensions):
                img_path = os.path.join(input_dir, file)
                self.preview_image_path = img_path
                break
    
    def preview_enhancement(self):
        """预览增强效果"""
        if not hasattr(self, 'preview_image_path'):
            messagebox.showwarning("警告", "请先选择输入目录")
            return
            
        # 使用支持中文路径的函数读取图像
        original_img = self.read_image_chinese_path(self.preview_image_path)
        if original_img is None:
            messagebox.showerror("错误", "无法读取图像文件")
            return
        
        # 应用增强
        enhanced_img = self.apply_enhancements(original_img)
        
        # 显示原始图像
        original_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        original_pil = Image.fromarray(original_rgb)
        original_pil.thumbnail((300, 300))
        original_photo = ImageTk.PhotoImage(original_pil)
        self.original_label.configure(image=original_photo)
        self.original_label.image = original_photo
        
        # 显示增强后图像
        enhanced_rgb = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB)
        enhanced_pil = Image.fromarray(enhanced_rgb)
        enhanced_pil.thumbnail((300, 300))
        enhanced_photo = ImageTk.PhotoImage(enhanced_pil)
        self.enhanced_label.configure(image=enhanced_photo)
        self.enhanced_label.image = enhanced_photo
    
    def apply_enhancements(self, image):
        """应用所有增强效果到单张图像"""
        enhanced = image.copy()
        
        # 1. 亮度/对比度调整
        brightness = self.brightness.get()
        contrast = self.contrast.get()
        enhanced = cv2.convertScaleAbs(enhanced, alpha=contrast, beta=brightness)
        
        # 2. 伽马校正
        gamma = self.gamma.get()
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                         for i in np.arange(0, 256)]).astype("uint8")
        enhanced = cv2.LUT(enhanced, table)
        
        # 3. CLAHE增强
        # 转换到LAB色彩空间，仅对L通道增强
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip.get(),
            tileGridSize=(self.clahe_grid.get(), self.clahe_grid.get())
        )
        l_clahe = clahe.apply(l)
        
        # 合并通道并转回BGR
        lab_clahe = cv2.merge((l_clahe, a, b))
        enhanced = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def start_batch_processing(self):
        """开始批量处理"""
        if not self.input_dir.get() or not self.output_dir.get():
            messagebox.showwarning("警告", "请先选择输入和输出目录")
            return
            
        if self.processing:
            messagebox.showinfo("信息", "处理正在进行中")
            return
            
        # 创建输出目录
        output_dir = self.output_dir.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 在后台线程中处理
        self.processing = True
        self.status_label.config(text="处理中...")
        
        thread = threading.Thread(target=self.batch_process_images)
        thread.daemon = True
        thread.start()
    
    def batch_process_images(self):
        """批量处理图像"""
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        
        # 支持的图像格式
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        
        # 获取所有图像文件
        image_files = []
        for file in os.listdir(input_dir):
            if file.lower().endswith(image_extensions):
                image_files.append(file)
        
        total_files = len(image_files)
        if total_files == 0:
            self.root.after(0, lambda: messagebox.showwarning("警告", "输入目录中没有图像文件"))
            self.processing = False
            return
        
        # 处理每个文件
        for i, filename in enumerate(image_files):
            if not self.processing:
                break
                
            input_path = os.path.join(input_dir, filename)
            
            # 保持原始文件名，如果包含中文则直接使用
            output_filename = f"enhanced_{filename}"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                # 读取图像
                img = self.read_image_chinese_path(input_path)
                if img is not None:
                    # 增强处理
                    enhanced_img = self.apply_enhancements(img)
                    
                    # 保存图像
                    success = self.save_image_chinese_path(enhanced_img, output_path)
                    if not success:
                        print(f"保存失败: {output_path}")
                
                # 更新进度
                progress_value = (i + 1) / total_files * 100
                self.root.after(0, self.update_progress, progress_value, i+1, total_files)
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
        
        # 处理完成
        self.root.after(0, self.processing_complete)
    
    def update_progress(self, value, current, total):
        """更新进度条和状态"""
        self.progress['value'] = value
        self.status_label.config(text=f"处理中: {current}/{total} 完成")
    
    def processing_complete(self):
        """处理完成回调"""
        self.processing = False
        self.progress['value'] = 0
        self.status_label.config(text="处理完成")
        messagebox.showinfo("完成", "批量处理完成！")
    
    def stop_processing(self):
        """停止处理"""
        self.processing = False
        self.status_label.config(text="已停止")

def main():
    root = tk.Tk()
    app = ScanEnhancerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()