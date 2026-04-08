import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from PIL import Image

class ImageEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量HSV调整工具 (高精度版)")
        self.root.geometry("520x600")
        self.root.resizable(False, False)

        # 变量初始化
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        
        # 核心参数变量 (使用 DoubleVar 以支持高精度)
        # 色相: -180 ~ 180
        self.hue_val = tk.DoubleVar(value=0)       
        # 饱和度: 0.00 ~ 3.00
        self.sat_val = tk.DoubleVar(value=1.00)  
        # 明度: 0.00 ~ 3.00
        self.val_val = tk.DoubleVar(value=1.00)  

        self.setup_ui()

    def setup_ui(self):
        # --- 1. 目录选择区域 ---
        frame_dir = tk.LabelFrame(self.root, text="目录设置", padx=10, pady=10)
        frame_dir.pack(fill="x", padx=10, pady=5)

        # 输入目录
        tk.Label(frame_dir, text="输入目录:").grid(row=0, column=0, sticky="w")
        tk.Entry(frame_dir, textvariable=self.input_dir, width=45).grid(row=0, column=1, padx=5)
        tk.Button(frame_dir, text="选择", command=self.select_input).grid(row=0, column=2)

        # 输出目录
        tk.Label(frame_dir, text="输出目录:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(frame_dir, textvariable=self.output_dir, width=45).grid(row=1, column=1, padx=5)
        tk.Button(frame_dir, text="选择", command=self.select_output).grid(row=1, column=2)

        # --- 2. 参数调整区域 ---
        frame_param = tk.LabelFrame(self.root, text="参数调整 (支持键盘输入)", padx=10, pady=10)
        frame_param.pack(fill="x", padx=10, pady=5)

        # 使用帮助函数创建滑块组
        self.create_slider_group(frame_param, "色相偏移 (Hue)", self.hue_val, -180, 180, 1)
        self.create_slider_group(frame_param, "饱和度倍率 (Saturation)", self.sat_val, 0.0, 3.0, 0.01)
        self.create_slider_group(frame_param, "明度倍率 (Value)", self.val_val, 0.0, 3.0, 0.01)
        
        # 重置按钮
        tk.Button(frame_param, text="重置参数", command=self.reset_params).pack(pady=10)

        # --- 3. 操作区域 ---
        frame_action = tk.Frame(self.root, padx=10, pady=5)
        frame_action.pack(fill="x", padx=10)

        self.btn_run = tk.Button(frame_action, text="开始批量处理", command=self.start_processing_thread, 
                                 bg="#007ACC", fg="white", font=("Microsoft YaHei", 12, "bold"), height=2)
        self.btn_run.pack(fill="x")

        # 进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=100, mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=10)

        # 状态栏
        self.status_label = tk.Label(self.root, text="准备就绪", bd=1, relief="sunken", anchor="w")
        self.status_label.pack(side="bottom", fill="x")

    def create_slider_group(self, parent, text, variable, min_val, max_val, resolution):
        """
        创建一个包含 标签 + 滑块 + 输入框 的组合
        """
        container = tk.Frame(parent)
        container.pack(fill="x", pady=5)

        # 标题
        tk.Label(container, text=text, width=20, anchor="w").pack(side="left")

        # 滑块 (Scale)
        # command=lambda... 是为了拖动时强制刷新Spinbox的显示，虽然绑定了变量，
        # 但有时候直接拖动Scale不会触发Spinbox的即时重绘，加上这个更流畅。
        scale = tk.Scale(container, from_=min_val, to=max_val, orient="horizontal", 
                         variable=variable, resolution=resolution, showvalue=False)
        scale.pack(side="left", fill="x", expand=True, padx=5)

        # 输入框 (Spinbox) - 允许键盘输入和微调
        # command 用来处理点击上下小箭头的逻辑
        spin = tk.Spinbox(container, from_=min_val, to=max_val, increment=resolution,
                          textvariable=variable, width=8, format="%.2f")
        spin.pack(side="right")
        
        # 绑定回车键，确保输入后变量能被正确捕获（虽然textvariable通常会自动同步，但为了用户体验防止焦点未移开）
        spin.bind('<Return>', lambda e: parent.focus_set())

    def select_input(self):
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)
            if not self.output_dir.get():
                self.output_dir.set(os.path.join(path, "output"))

    def select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def reset_params(self):
        self.hue_val.set(0.0)
        self.sat_val.set(1.00)
        self.val_val.set(1.00)

    def log(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def process_image(self, img_path, save_path, hue_shift, sat_factor, val_factor):
        try:
            with Image.open(img_path) as img:
                img = img.convert("RGBA")
                
                # --- 1. 处理色相 (Hue) ---
                shift_amount = int((hue_shift / 360.0) * 255)
                hsv_img = img.convert("HSV")
                h, s, v = hsv_img.split()
                
                def hue_transform(x):
                    return (x + shift_amount) % 255
                h = h.point(hue_transform)
                
                # --- 2. 处理饱和度 (Saturation) - 使用 float 计算 ---
                # 使用 lambda 能够更精确地处理浮点数运算后再转回 int
                s = s.point(lambda x: min(255, max(0, int(x * sat_factor))))

                # --- 3. 处理明度 (Value) - 使用 float 计算 ---
                v = v.point(lambda x: min(255, max(0, int(x * val_factor))))

                hsv_final = Image.merge("HSV", (h, s, v))
                final_img = hsv_final.convert("RGB")

                if img.mode == "RGBA":
                    r, g, b = final_img.split()
                    a = img.split()[3]
                    final_img = Image.merge("RGBA", (r, g, b, a))
                    if not save_path.lower().endswith(('.png', '.webp')):
                         final_img = final_img.convert("RGB")

                final_img.save(save_path, quality=95)
                return True
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            return False

    def start_processing_thread(self):
        in_path = self.input_dir.get()
        out_path = self.output_dir.get()

        if not in_path or not os.path.isdir(in_path):
            messagebox.showerror("错误", "输入目录无效！")
            return
        
        if not out_path:
            messagebox.showerror("错误", "请设置输出目录！")
            return

        # 校验输入数值是否合法 (防止用户手动输入字母等非法字符)
        try:
            h = self.hue_val.get()
            s = self.sat_val.get()
            v = self.val_val.get()
        except tk.TclError:
            messagebox.showerror("参数错误", "请确保色相、饱和度、明度输入的是有效的数字！")
            return

        self.btn_run.config(state="disabled")
        t = threading.Thread(target=self.run_processing, args=(in_path, out_path, h, s, v))
        t.start()

    def run_processing(self, in_dir, out_dir, hue, sat, val):
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"无法创建输出目录: {e}"))
                self.root.after(0, lambda: self.btn_run.config(state="normal"))
                return

        valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff')
        files = [f for f in os.listdir(in_dir) if f.lower().endswith(valid_exts)]
        total = len(files)

        if total == 0:
            self.root.after(0, lambda: messagebox.showinfo("提示", "输入目录中没有找到支持的图片文件。"))
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            return

        self.root.after(0, lambda: self.progress.config(maximum=total, value=0))
        
        count = 0
        for i, filename in enumerate(files):
            full_in_path = os.path.join(in_dir, filename)
            full_out_path = os.path.join(out_dir, filename)
            
            self.root.after(0, lambda msg=f"正在处理 ({i+1}/{total}): {filename}": self.log(msg))
            
            # 使用传入的 h, s, v 参数，而不是实时获取 UI 参数，保证批处理一致性
            success = self.process_image(full_in_path, full_out_path, hue, sat, val)
            
            if success:
                count += 1
            
            self.root.after(0, lambda val=i+1: self.progress.config(value=val))

        self.root.after(0, lambda: self.log(f"处理完成！成功: {count}/{total}"))
        self.root.after(0, lambda: messagebox.showinfo("完成", f"处理完成！\n共处理 {count} 张图片。"))
        self.root.after(0, lambda: self.btn_run.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageEditorApp(root)
    root.mainloop()