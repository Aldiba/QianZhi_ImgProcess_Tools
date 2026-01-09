import os
import cv2
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from ttkthemes import ThemedTk
import threading

def straighten_and_crop(image_path, output_path):
    """
    处理单个图像：使用最大轮廓和最小面积矩形方法来检测倾斜、旋转和裁剪。
    """
    try:
        # 使用Pillow读取图像，以更好地支持中文路径
        img_pil = Image.open(image_path)
        # 确保图像是RGB格式
        if img_pil.mode != 'RGB':
            img_pil = img_pil.convert('RGB')
        
        # 将Pillow图像转换为OpenCV格式 (RGB -> BGR)
        open_cv_image = np.array(img_pil)[:, :, ::-1]

        # 转换为灰度图
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        
        # 对灰度图进行二值化处理
        # 大于50的像素变为255（白色），小于等于50的变为0（黑色）
        # 这个阈值可以根据实际扫描情况微调
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        
        # 查找轮廓
        # cv2.RETR_EXTERNAL表示只检测最外层的轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            # 如果没有找到任何轮廓，直接保存原图
            img_pil.save(output_path)
            print(f"在 {os.path.basename(image_path)} 中未找到轮廓。")
            return

        # 找到面积最大的轮廓
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 计算能包围此轮廓的最小面积矩形
        # rect是一个元组: ((center_x, center_y), (width, height), angle)
        rect = cv2.minAreaRect(largest_contour)
        
        angle = rect[2]
        
        # 得到的角度范围是[-90, 0)。我们需要调整它
        # 当矩形是“高”>“宽”时，角度是正确的倾斜角
        # 当矩形是“宽”>“高”时，角度需要+90度来得到相对于垂直线的倾斜角
        width, height = rect[1]
        if width < height:
            angle = angle
        else:
            angle = angle + 90
        
        if angle==180:
            angle = 0
            
        # 如果角度非常接近0或90，可能本身就是正的，无需旋转
        if abs(angle) < 0.1 or abs(angle - 90) < 0.1:
            # 即使不旋转，也进行裁剪
            x, y, w_crop, h_crop = cv2.boundingRect(largest_contour)
            cropped = open_cv_image[y:y+h_crop, x:x+w_crop]
            final_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            img_to_save = Image.fromarray(final_image)
            img_to_save.save(output_path)
            return

        

        # 获取图像尺寸并进行旋转
        (h, w) = open_cv_image.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 执行旋转，并用黑色填充背景
        rotated = cv2.warpAffine(open_cv_image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        
        print(f"文件: {os.path.basename(image_path)}, 检测到的倾斜角: {angle:.2f} 度")

        # --- 自动裁剪旋转后的图像 ---
        # 对旋转后的图像再次进行二值化和轮廓检测，以精确定位内容区域
        rotated_gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        _, rotated_thresh = cv2.threshold(rotated_gray, 1, 255, cv2.THRESH_BINARY)
        
        contours_rotated, _ = cv2.findContours(rotated_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours_rotated:
            cnt_rot = max(contours_rotated, key=cv2.contourArea)
            x, y, w_crop, h_crop = cv2.boundingRect(cnt_rot)
            cropped = rotated[y:y+h_crop, x:x+w_crop]
            
            final_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            img_to_save = Image.fromarray(final_image)
            img_to_save.save(output_path)
        else:
            # 如果裁剪失败，则保存仅旋转过的图像
            final_image = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
            img_to_save = Image.fromarray(final_image)
            img_to_save.save(output_path)

    except Exception as e:
        print(f"处理文件 {os.path.basename(image_path)} 时出错: {e}")

# --- GUI部分的代码与之前版本完全相同，此处省略以保持简洁 ---
# --- 您可以直接复制下面的完整代码运行 ---

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片自动转正与裁剪工具")
        self.root.geometry("500x200")

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()

        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="输入文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.input_entry = ttk.Entry(frame, textvariable=self.input_folder, width=40)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_input_btn = ttk.Button(frame, text="浏览...", command=self.browse_input)
        self.browse_input_btn.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame, text="输出文件夹:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.output_entry = ttk.Entry(frame, textvariable=self.output_folder, width=40)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.browse_output_btn = ttk.Button(frame, text="浏览...", command=self.browse_output)
        self.browse_output_btn.grid(row=1, column=2, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=3, padx=5, pady=15, sticky="ew")

        self.start_button = ttk.Button(frame, text="开始处理", command=self.start_processing)
        self.start_button.grid(row=3, column=1, padx=5, pady=5)
        
    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder: self.input_folder.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder: self.output_folder.set(folder)

    def start_processing(self):
        input_dir, output_dir = self.input_folder.get(), self.output_folder.get()
        if not input_dir or not output_dir:
            messagebox.showerror("错误", "请选择输入和输出文件夹。")
            return
        if not os.path.exists(output_dir): os.makedirs(output_dir)

        self.start_button.config(state=tk.DISABLED)
        self.browse_input_btn.config(state=tk.DISABLED)
        self.browse_output_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)

        threading.Thread(target=self.run_processing, args=(input_dir, output_dir)).start()

    def run_processing(self, input_folder, output_folder):
        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        files_to_process = [f for f in os.listdir(input_folder) if f.lower().endswith(supported_formats)]
        total_files = len(files_to_process)
        
        if total_files == 0:
            messagebox.showinfo("提示", "输入文件夹中没有找到支持的图片文件。")
            self.root.after(0, self.processing_done)
            return

        for i, filename in enumerate(files_to_process):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            straighten_and_crop(input_path, output_path)
            self.root.after(0, self.update_progress, (i + 1) * 100 / total_files)

        messagebox.showinfo("完成", "处理完毕")
        self.root.after(0, self.processing_done)
    
    def update_progress(self, value):
        self.progress_var.set(value)

    def processing_done(self):
        self.start_button.config(state=tk.NORMAL)
        self.browse_input_btn.config(state=tk.NORMAL)
        self.browse_output_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = ImageProcessorApp(root)
    root.mainloop()
