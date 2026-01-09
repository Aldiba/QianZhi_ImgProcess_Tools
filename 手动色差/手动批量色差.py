import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

class ChromaticAberrationCorrector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("漫画扫描色差校正工具 (v2.1 - 性能优化版)")
        self.geometry("950x500")

        # --- 图像状态变量 ---
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.image_files = []
        self.original_pil_image = None
        self.corrected_pil_image = None
        self.display_photo = None

        # --- 缩放与平移 ---
        self.zoom_level = 1.0
        self.canvas_image_x = 0
        self.canvas_image_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0

        # --- 通道偏移量 ---
        self.offsets = {'r': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)},
                        'g': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)},
                        'b': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)}}
        self.active_channel = tk.StringVar(value='r')

        # --- 性能优化：用于更新节流(Debouncing) ---
        self.update_job_id = None

        self.create_widgets()

    def create_widgets(self):
        # --- 顶部IO路径选择区 ---
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(side="top", fill="x")

        ttk.Label(top_frame, text="输入文件夹:").pack(side="left", padx=(0, 5))
        ttk.Entry(top_frame, textvariable=self.input_folder, width=45).pack(side="left", expand=True, fill="x")
        ttk.Button(top_frame, text="选择...", command=self.select_input_folder).pack(side="left", padx=5)

        ttk.Label(top_frame, text="输出文件夹:").pack(side="left", padx=(10, 5))
        ttk.Entry(top_frame, textvariable=self.output_folder, width=45).pack(side="left", expand=True, fill="x")
        ttk.Button(top_frame, text="选择...", command=self.select_output_folder).pack(side="left", padx=5)

        # --- 底部进度与执行区 ---
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(side="bottom", fill="x")

        self.progress_bar = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.start_button = ttk.Button(bottom_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(side="right")

        # --- 主内容区 ---
        main_frame = ttk.Frame(self)
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # --- 右侧控制面板 ---
        control_panel = ttk.Frame(main_frame, padding="10", width=280)
        control_panel.pack(side="right", fill="y")
        control_panel.pack_propagate(False)

        ttk.Label(control_panel, text="参考图选择:", font=("-weight", "bold")).pack(anchor="w", pady=(0, 5))
        self.image_selector = ttk.Combobox(control_panel, state="readonly")
        self.image_selector.pack(fill="x", pady=(0, 10))
        self.image_selector.bind("<<ComboboxSelected>>", self.on_image_select)

        ttk.Separator(control_panel).pack(fill="x", pady=10)
        
        ttk.Label(control_panel, text="通道偏移控制:", font=("-weight", "bold")).pack(anchor="w")
        channel_frame = ttk.Frame(control_panel)
        channel_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(channel_frame, text="红 (R)", variable=self.active_channel, value='r', command=self.update_controls).pack(side="left", expand=True)
        ttk.Radiobutton(channel_frame, text="绿 (G)", variable=self.active_channel, value='g', command=self.update_controls).pack(side="left", expand=True)
        ttk.Radiobutton(channel_frame, text="蓝 (B)", variable=self.active_channel, value='b', command=self.update_controls).pack(side="left", expand=True)

        offset_frame = ttk.Frame(control_panel)
        offset_frame.pack(fill="x", pady=5)
        ttk.Label(offset_frame, text="X轴偏移:").grid(row=0, column=0, sticky="w", padx=5)
        self.x_offset_entry = ttk.Entry(offset_frame, textvariable=self.offsets['r']['x'], width=8)
        self.x_offset_entry.grid(row=0, column=1)
        self.x_offset_entry.bind("<KeyRelease>", self.schedule_update)

        ttk.Label(offset_frame, text="Y轴偏移:").grid(row=1, column=0, sticky="w", padx=5)
        self.y_offset_entry = ttk.Entry(offset_frame, textvariable=self.offsets['r']['y'], width=8)
        self.y_offset_entry.grid(row=1, column=1, pady=5)
        self.y_offset_entry.bind("<KeyRelease>", self.schedule_update)

        ttk.Separator(control_panel).pack(fill="x", pady=15)
        
        tips_frame = ttk.LabelFrame(control_panel, text="操作提示", padding=10)
        tips_frame.pack(fill="x")
        tips_text = "· 缩放: Ctrl + 鼠标滚轮\n· 平移: 按住鼠标左键拖动"
        ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT).pack(anchor="w")

        # --- 操作台 (图片预览区 + 滑块) ---
        workbench_frame = ttk.Frame(main_frame)
        workbench_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.y_slider = ttk.Scale(workbench_frame, from_=-20, to=20, orient="vertical", command=self.update_from_slider)
        self.y_slider.pack(side="right", fill="y")

        self.x_slider = ttk.Scale(workbench_frame, from_=-20, to=20, orient="horizontal", command=self.update_from_slider)
        self.x_slider.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(workbench_frame, bg="#505050", cursor="arrow")
        self.canvas.pack(fill="both", expand=True)

        # --- 绑定事件 ---
        self.canvas.bind("<Control-MouseWheel>", self.zoom_image)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-1>", self.end_pan)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.update_controls()

    # --- 文件与加载 ---
    def select_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path: self.input_folder.set(folder_path); self.load_image_list()

    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path: self.output_folder.set(folder_path)

    def load_image_list(self):
        folder = self.input_folder.get()
        self.image_files, self.image_selector['values'] = [], []
        self.canvas.delete("all"); self.original_pil_image = None
        if not folder: return
        try:
            self.image_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])
            self.image_selector['values'] = self.image_files
            if self.image_files: self.image_selector.current(0); self.on_image_select()
            else: messagebox.showinfo("提示", "未在所选文件夹中找到支持的图片格式。")
        except Exception as e: messagebox.showerror("错误", f"加载图片列表失败: {e}")

    def on_image_select(self, event=None):
        selected_file = self.image_selector.get()
        if not selected_file: return
        image_path = os.path.join(self.input_folder.get(), selected_file)
        try:
            self.original_pil_image = Image.open(image_path)
            self.reset_view()
            self.apply_offsets_and_redraw()
        except Exception as e:
            messagebox.showerror("错误", f"打开图片失败: {e}")
            self.original_pil_image = None
    
    def on_canvas_resize(self, event=None):
        self.schedule_update(delay=100) # 窗口大小变化时也延迟更新，防止卡顿

    # --- UI更新与控制 ---
    def update_controls(self):
        channel = self.active_channel.get()
        self.x_slider.set(self.offsets[channel]['x'].get())
        self.y_slider.set(self.offsets[channel]['y'].get())
        self.x_offset_entry.config(textvariable=self.offsets[channel]['x'])
        self.y_offset_entry.config(textvariable=self.offsets[channel]['y'])

    def update_from_slider(self, event=None):
        channel = self.active_channel.get()
        self.offsets[channel]['x'].set(int(float(self.x_slider.get())))
        self.offsets[channel]['y'].set(int(float(self.y_slider.get())))
        self.schedule_update()

    # --- 性能优化核心：更新节流 ---
    def schedule_update(self, event=None, delay=25):
        """取消任何待定的更新，并安排一个新的更新。这是避免卡顿的关键。"""
        if self.update_job_id:
            self.after_cancel(self.update_job_id)
        self.update_job_id = self.after(delay, self.apply_offsets_and_redraw)

    # --- 图像处理与显示核心 ---
    def apply_offsets_and_redraw(self):
        if not self.original_pil_image: return
        img = self.original_pil_image
        if img.mode != 'RGB': img = img.convert('RGB')
        r, g, b = img.split()
        r = self._shift_channel(r, self.offsets['r']['x'].get(), self.offsets['r']['y'].get())
        g = self._shift_channel(g, self.offsets['g']['x'].get(), self.offsets['g']['y'].get())
        b = self._shift_channel(b, self.offsets['b']['x'].get(), self.offsets['b']['y'].get())
        self.corrected_pil_image = Image.merge('RGB', (r, g, b))
        self.redraw_canvas()

    def _shift_channel(self, channel, dx, dy):
        if dx == 0 and dy == 0: return channel
        shifted = Image.new('L', channel.size, 0)
        shifted.paste(channel, (dx, dy))
        return shifted

    def redraw_canvas(self):
        if not self.corrected_pil_image: return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1: return

        new_w, new_h = int(self.corrected_pil_image.width * self.zoom_level), int(self.corrected_pil_image.height * self.zoom_level)
        if new_w < 1 or new_h < 1: return

        # 性能优化：使用速度更快的BILINEAR算法进行实时预览，效果几乎无差别，但流畅度大大提升
        display_img = self.corrected_pil_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        
        self.display_photo = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all")
        self.canvas.create_image(self.canvas_image_x, self.canvas_image_y, anchor="nw", image=self.display_photo)

    def reset_view(self):
        if not self.original_pil_image: return
        self.zoom_level = 1.0
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        iw, ih = self.original_pil_image.size
        if iw > 0 and ih > 0: self.zoom_level = min(cw / iw, ch / ih, 1.0) # 初始缩放不超过100%
        zoomed_w, zoomed_h = int(iw * self.zoom_level), int(ih * self.zoom_level)
        self.canvas_image_x = (cw - zoomed_w) // 2
        self.canvas_image_y = (ch - zoomed_h) // 2

    # --- 缩放与平移事件处理 ---
    def zoom_image(self, event):
        if not self.corrected_pil_image: return
        zoom_factor = 1.1 if event.delta > 0 else 1 / 1.1
        img_coord_x = event.x - self.canvas_image_x
        img_coord_y = event.y - self.canvas_image_y
        self.canvas_image_x = event.x - img_coord_x * zoom_factor
        self.canvas_image_y = event.y - img_coord_y * zoom_factor
        self.zoom_level *= zoom_factor
        self.redraw_canvas()

    def start_pan(self, event): self.pan_start_x, self.pan_start_y = event.x, event.y; self.canvas.config(cursor="fleur")
    def do_pan(self, event):
        dx, dy = event.x - self.pan_start_x, event.y - self.pan_start_y
        self.canvas_image_x += dx; self.canvas_image_y += dy
        self.pan_start_x, self.pan_start_y = event.x, event.y
        self.redraw_canvas()
    def end_pan(self, event): self.canvas.config(cursor="arrow")

    # --- 批量处理 ---
    def start_processing(self):
        if not (self.input_folder.get() and self.output_folder.get()):
            messagebox.showwarning("警告", "请先选择输入和输出文件夹。")
            return
        if not self.image_files: messagebox.showwarning("警告", "输入文件夹中没有找到图片。"); return
        self.start_button.config(state="disabled")
        self.progress_bar.config(value=0, maximum=len(self.image_files))
        threading.Thread(target=self._batch_process_thread, daemon=True).start()

    def _batch_process_thread(self):
        input_dir, output_dir = self.input_folder.get(), self.output_folder.get()
        offsets = {ch: (val['x'].get(), val['y'].get()) for ch, val in self.offsets.items()}
        for i, filename in enumerate(self.image_files):
            try:
                with Image.open(os.path.join(input_dir, filename)) as img:
                    if img.mode != 'RGB': img = img.convert('RGB')
                    r, g, b = img.split()
                    r = self._shift_channel(r, offsets['r'][0], offsets['r'][1])
                    g = self._shift_channel(g, offsets['g'][0], offsets['g'][1])
                    b = self._shift_channel(b, offsets['b'][0], offsets['b'][1])
                    corrected_img = Image.merge('RGB', (r, g, b))
                    corrected_img.save(os.path.join(output_dir, filename))
            except Exception as e: print(f"处理文件 {filename} 时出错: {e}")
            self.after(0, self.progress_bar.config, {'value': i + 1})
        self.after(0, self.on_processing_done)
        
    def on_processing_done(self):
        self.start_button.config(state="normal")
        messagebox.showinfo("完成", "所有图片已处理完毕！")

if __name__ == "__main__":
    app = ChromaticAberrationCorrector()
    app.mainloop()