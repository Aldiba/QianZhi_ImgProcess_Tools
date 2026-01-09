import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

class ChromaticAberrationCorrector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("扫描色差手动批量校正")
        self.geometry("1200x600")
        
        # --- 样式配置 ---
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use('clam')
        style.configure(
            'custom.Horizontal.TScale', troughcolor='#d3d3d3', background='#4285F4', bordercolor='#3367d6'
        )
        style.configure(
            'custom.Vertical.TScale', troughcolor='#d3d3d3', background='#4285F4', bordercolor='#3367d6'
        )

        # --- 初始化核心变量 ---
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.image_files = []
        self.original_pil_image = None
        self.corrected_pil_image = None
        self.display_photo = None

        self.offsets = {'r': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)},
                        'g': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)},
                        'b': {'x': tk.IntVar(value=0), 'y': tk.IntVar(value=0)}}
        self.active_channel = tk.StringVar(value='r')
        
        self.zoom_level = 1.0
        self.view_x = 0
        self.view_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0

        # *** BUG修复关键 ***: 增加一个状态锁，防止切换通道时触发不必要的更新
        self._is_switching_channel = False

        self.create_widgets()
        self.canvas.bind("<Configure>", lambda event: self.redraw_canvas())

    def create_widgets(self):
        # ... [界面布局代码与之前版本相同，为了简洁此处省略] ...
        # (请从下方完整代码块中复制)
        main_paned_window = ttk.PanedWindow(self, orient='horizontal')
        main_paned_window.pack(fill='both', expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(left_frame, weight=4)

        top_frame = ttk.Frame(left_frame, padding=(0, 0, 0, 10))
        top_frame.pack(side="top", fill="x")

        ttk.Label(top_frame, text="输入文件夹:").pack(side="left", padx=(0, 5))
        ttk.Entry(top_frame, textvariable=self.input_folder, width=40).pack(side="left", expand=True, fill="x")
        ttk.Button(top_frame, text="...", command=self.select_input_folder, width=4).pack(side="left", padx=5)
        ttk.Label(top_frame, text="输出文件夹:").pack(side="left", padx=(10, 5))
        ttk.Entry(top_frame, textvariable=self.output_folder, width=40).pack(side="left", expand=True, fill="x")
        ttk.Button(top_frame, text="...", command=self.select_output_folder, width=4).pack(side="left", padx=5)

        workbench_frame = ttk.Frame(left_frame)
        workbench_frame.pack(side="top", fill="both", expand=True)
        
        self.y_slider = ttk.Scale(workbench_frame, from_=-50, to=50, orient="vertical", command=self.update_from_slider, style='custom.Vertical.TScale')
        self.y_slider.pack(side="right", fill="y")
        self.x_slider = ttk.Scale(workbench_frame, from_=-50, to=50, orient="horizontal", command=self.update_from_slider, style='custom.Horizontal.TScale')
        self.x_slider.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(workbench_frame, bg="#505050", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Control-MouseWheel>", self.zoom_handler)
        self.canvas.bind("<MouseWheel>", self.zoom_handler)
        self.canvas.bind("<ButtonPress-1>", self.pan_start)
        self.canvas.bind("<B1-Motion>", self.pan_move)
        self.canvas.bind("<ButtonRelease-1>", self.pan_end)

        control_panel = ttk.Frame(main_paned_window, padding="10", width=280)
        main_paned_window.add(control_panel, weight=1)
        control_panel.pack_propagate(False)

        ttk.Label(control_panel, text="参考图选择:", font=("-weight", "bold")).pack(anchor="w", pady=(0, 5))
        self.image_selector = ttk.Combobox(control_panel, state="readonly")
        self.image_selector.pack(fill="x", pady=(0, 15))
        self.image_selector.bind("<<ComboboxSelected>>", self.load_selected_image)

        ttk.Separator(control_panel).pack(fill="x", pady=10)
        
        ttk.Label(control_panel, text="通道偏移控制:", font=("-weight", "bold")).pack(anchor="w")
        channel_frame = ttk.Frame(control_panel)
        channel_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(channel_frame, text="红(R)", variable=self.active_channel, value='r', command=self.switch_active_channel).pack(side="left", expand=True)
        ttk.Radiobutton(channel_frame, text="绿(G)", variable=self.active_channel, value='g', command=self.switch_active_channel).pack(side="left", expand=True)
        ttk.Radiobutton(channel_frame, text="蓝(B)", variable=self.active_channel, value='b', command=self.switch_active_channel).pack(side="left", expand=True)

        offset_grid = ttk.Frame(control_panel)
        offset_grid.pack(fill="x", pady=5)
        ttk.Label(offset_grid, text="X轴偏移:").grid(row=0, column=0, sticky="w", pady=2)
        self.x_offset_entry = ttk.Spinbox(offset_grid, from_=-50, to=50, textvariable=self.offsets['r']['x'], width=8, command=self.update_from_spinbox)
        self.x_offset_entry.grid(row=0, column=1, padx=5)
        self.x_offset_entry.bind("<Return>", self.update_from_spinbox)
        
        ttk.Label(offset_grid, text="Y轴偏移:").grid(row=1, column=0, sticky="w", pady=2)
        self.y_offset_entry = ttk.Spinbox(offset_grid, from_=-50, to=50, textvariable=self.offsets['r']['y'], width=8, command=self.update_from_spinbox)
        self.y_offset_entry.grid(row=1, column=1, padx=5)
        self.y_offset_entry.bind("<Return>", self.update_from_spinbox)

        ttk.Separator(control_panel).pack(fill="x", pady=15)

        tips_frame = ttk.LabelFrame(control_panel, text="操作提示")
        tips_frame.pack(fill='x', pady=10)
        tips_text = "• 滚轮 (或 Ctrl+滚轮): 缩放\n• 鼠标左键拖动: 平移图像"
        ttk.Label(tips_frame, text=tips_text, justify="left").pack(anchor="w", padx=10, pady=5)

        bottom_frame = ttk.Frame(self, padding="5")
        bottom_frame.pack(side="bottom", fill="x")
        self.progress_bar = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(5, 10))
        self.start_button = ttk.Button(bottom_frame, text="开始批量处理", command=self.start_processing)
        self.start_button.pack(side="right", padx=(0, 5))
        
    def select_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_folder.set(folder_path)
            self.load_image_list()

    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder.set(folder_path)

    def load_image_list(self):
        folder = self.input_folder.get()
        if not folder: return
        try:
            self.image_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'))])
            self.image_selector['values'] = self.image_files
            if self.image_files:
                self.image_selector.current(0)
                self.load_selected_image()
            else:
                self.canvas.delete("all")
                self.original_pil_image = None
                messagebox.showinfo("提示", "未在所选文件夹中找到支持的图片格式。")
        except Exception as e:
            messagebox.showerror("错误", f"加载图片列表失败: {e}")

    def load_selected_image(self, event=None):
        selected_file = self.image_selector.get()
        if not selected_file: return
        self.current_image_path = os.path.join(self.input_folder.get(), selected_file)
        try:
            self.original_pil_image = Image.open(self.current_image_path)
            self.zoom_level, self.view_x, self.view_y = 1.0, 0, 0
            self.process_and_redraw()
        except Exception as e:
            self.original_pil_image = None
            messagebox.showerror("错误", f"打开图片失败: {e}")

    def switch_active_channel(self):
        """当点击Radiobutton时调用，只负责更新UI控件的状态"""
        self._is_switching_channel = True  # 上锁
        channel = self.active_channel.get()
        # 更新Spinbox绑定的变量
        self.x_offset_entry.config(textvariable=self.offsets[channel]['x'])
        self.y_offset_entry.config(textvariable=self.offsets[channel]['y'])
        # 更新Slider的位置以匹配新通道的值
        self.x_slider.set(self.offsets[channel]['x'].get())
        self.y_slider.set(self.offsets[channel]['y'].get())
        self._is_switching_channel = False # 解锁

    def update_from_spinbox(self, event=None):
        """当Spinbox值改变时调用，负责同步Slider并触发更新"""
        if self._is_switching_channel: return
        channel = self.active_channel.get()
        # 同步滑块
        self.x_slider.set(self.offsets[channel]['x'].get())
        self.y_slider.set(self.offsets[channel]['y'].get())
        # 滑块的.set()会自动触发update_from_slider，所以这里不需要再调用
        # process_and_redraw()，避免重复计算

    def update_from_slider(self, event=None):
        """当Slider被拖动时调用，负责更新IntVar并触发重绘"""
        if self._is_switching_channel: return # 如果正在切换通道，则忽略此事件

        channel = self.active_channel.get()
        self.offsets[channel]['x'].set(int(float(self.x_slider.get())))
        self.offsets[channel]['y'].set(int(float(self.y_slider.get())))
        self.process_and_redraw()

    def process_and_redraw(self):
        """核心函数：应用色彩偏移并重绘Canvas"""
        if not self.original_pil_image: return
        self.corrected_pil_image = self.apply_channel_shift(self.original_pil_image)
        self.redraw_canvas()

    def redraw_canvas(self):
        if not self.corrected_pil_image: return
        canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1: return

        crop_width = canvas_width / self.zoom_level
        crop_height = canvas_height / self.zoom_level
        
        img_w, img_h = self.corrected_pil_image.size
        self.view_x = max(0, min(self.view_x, img_w - crop_width))
        self.view_y = max(0, min(self.view_y, img_h - crop_height))

        box = (self.view_x, self.view_y, self.view_x + crop_width, self.view_y + crop_height)
        
        try:
            cropped_img = self.corrected_pil_image.crop(box)
            resized_img = cropped_img.resize((canvas_width, canvas_height), Image.Resampling.NEAREST)
            self.display_photo = ImageTk.PhotoImage(resized_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.display_photo)
        except ValueError: pass # 忽略因快速缩放导致的无效box尺寸

    def apply_channel_shift(self, pil_image):
        img_to_process = pil_image.convert('RGB') if pil_image.mode != 'RGB' else pil_image
        r, g, b = img_to_process.split()
        r = self._shift_channel(r, self.offsets['r']['x'].get(), self.offsets['r']['y'].get())
        g = self._shift_channel(g, self.offsets['g']['x'].get(), self.offsets['g']['y'].get())
        b = self._shift_channel(b, self.offsets['b']['x'].get(), self.offsets['b']['y'].get())
        return Image.merge('RGB', (r, g, b))

    def _shift_channel(self, channel, dx, dy):
        if dx == 0 and dy == 0: return channel
        return channel.transform(channel.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy))

    def zoom_handler(self, event):
        if not self.corrected_pil_image: return
        zoom_factor = 1.1 if (event.delta > 0 or event.num == 4) else 0.9
        mouse_x = self.view_x + (event.x / self.zoom_level)
        mouse_y = self.view_y + (event.y / self.zoom_level)
        self.zoom_level = max(0.05, min(self.zoom_level * zoom_factor, 50.0))
        self.view_x = mouse_x - (event.x / self.zoom_level)
        self.view_y = mouse_y - (event.y / self.zoom_level)
        self.redraw_canvas()

    def pan_start(self, event): self.pan_start_x, self.pan_start_y = event.x, event.y; self.canvas.config(cursor="fleur")
    def pan_move(self, event):
        if not self.corrected_pil_image: return
        dx = (event.x - self.pan_start_x) / self.zoom_level
        dy = (event.y - self.pan_start_y) / self.zoom_level
        self.view_x -= dx; self.view_y -= dy
        self.pan_start_x, self.pan_start_y = event.x, event.y
        self.redraw_canvas()
    def pan_end(self, event): self.canvas.config(cursor="arrow")

    def start_processing(self):
        if not (self.input_folder.get() and self.output_folder.get()):
            messagebox.showwarning("警告", "请先选择输入和输出文件夹。")
            return
        if not self.image_files:
            messagebox.showwarning("警告", "输入文件夹中没有找到图片。")
            return
        self.start_button.config(state="disabled", text="正在处理...")
        self.progress_bar.config(value=0, maximum=len(self.image_files))
        threading.Thread(target=self.batch_process, daemon=True).start()

    def batch_process(self):
        input_dir, output_dir = self.input_folder.get(), self.output_folder.get()
        offsets = {ch: (val['x'].get(), val['y'].get()) for ch, val in self.offsets.items()}
        for i, filename in enumerate(self.image_files):
            try:
                with Image.open(os.path.join(input_dir, filename)) as img:
                    corrected_img = self.apply_channel_shift_for_batch(img, offsets)
                    corrected_img.save(os.path.join(output_dir, filename), quality=95)
            except Exception as e: print(f"处理文件 {filename} 时出错: {e}")
            self.after(0, self.progress_bar.config, {'value': i + 1})
        self.after(0, self.processing_done)
        
    def apply_channel_shift_for_batch(self, pil_image, offsets):
        img_to_process = pil_image.convert('RGB') if pil_image.mode != 'RGB' else pil_image
        r, g, b = img_to_process.split()
        r = self._shift_channel(r, offsets['r'][0], offsets['r'][1])
        g = self._shift_channel(g, offsets['g'][0], offsets['g'][1])
        b = self._shift_channel(b, offsets['b'][0], offsets['b'][1])
        return Image.merge('RGB', (r, g, b))

    def processing_done(self):
        self.start_button.config(state="normal", text="开始批量处理")
        messagebox.showinfo("完成", "所有图片已处理完毕！")

if __name__ == "__main__":
    app = ChromaticAberrationCorrector()
    app.mainloop()