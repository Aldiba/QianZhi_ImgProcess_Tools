# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
import os
import math
import numpy as np
import cv2
import threading
import queue

class DeskewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("图片自动扶正工具")
        self.geometry("500x350")
        self.resizable(False, False)

        # 确保支持中文路径
        self.input_dir = ""
        self.output_dir = ""
        self.process_queue = None
        self.processing_thread = None

        self.create_widgets()

    def create_widgets(self):
        """创建GUI界面的所有控件"""
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # 输入文件夹选择
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill="x", pady=10)
        tk.Label(input_frame, text="选择输入文件夹:").pack(side="left")
        self.input_path_label = tk.Label(input_frame, text="未选择", bg="white", relief="sunken", width=40, anchor="w")
        self.input_path_label.pack(side="left", padx=10)
        tk.Button(input_frame, text="浏览...", command=self.select_input_dir).pack(side="right")

        # 输出文件夹选择
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill="x", pady=10)
        tk.Label(output_frame, text="选择输出文件夹:").pack(side="left")
        self.output_path_label = tk.Label(output_frame, text="未选择", bg="white", relief="sunken", width=40, anchor="w")
        self.output_path_label.pack(side="left", padx=10)
        tk.Button(output_frame, text="浏览...", command=self.select_output_dir).pack(side="right")

        # 进度条
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=20)
        tk.Label(progress_frame, text="处理进度:").pack(side="left")
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side="left", padx=10)
        self.progress_label = tk.Label(progress_frame, text="0/0")
        self.progress_label.pack(side="left")

        # 状态信息
        self.status_label = tk.Label(main_frame, text="等待处理...")
        self.status_label.pack(pady=10)

        # 开始按钮
        self.start_button = tk.Button(main_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(pady=20, ipadx=20, ipady=5)

    def select_input_dir(self):
        """打开文件夹选择对话框以选择输入目录"""
        self.input_dir = filedialog.askdirectory(title="选择输入文件夹")
        if self.input_dir:
            self.input_path_label.config(text=self.input_dir)

    def select_output_dir(self):
        """打开文件夹选择对话框以选择输出目录"""
        self.output_dir = filedialog.askdirectory(title="选择输出文件夹")
        if self.output_dir:
            self.output_path_label.config(text=self.output_dir)

    def start_processing(self):
        """启动新线程进行图片处理"""
        if not self.input_dir or not self.output_dir:
            messagebox.showerror("错误", "请选择输入和输出文件夹！")
            return

        # 禁用按钮防止重复点击
        self.start_button.config(state="disabled")
        self.status_label.config(text="开始处理...")
        
        # 创建线程安全的队列
        self.process_queue = queue.Queue()
        
        # 创建并启动新线程，将队列和路径传递给它
        self.processing_thread = threading.Thread(target=self.process_images_thread,
                                                  args=(self.input_dir, self.output_dir, self.process_queue))
        self.processing_thread.start()
        
        # 启动队列轮询，每100毫秒检查一次
        self.after(100, self.poll_queue)

    def process_images_thread(self, input_dir, output_dir, q):
        """在新线程中执行图片处理，并将进度放入队列"""
        try:
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
            files = [f for f in os.listdir(input_dir) if f.lower().endswith(image_extensions)]
            total_files = len(files)
            
            if total_files == 0:
                q.put(("info", "输入文件夹中没有找到任何图片文件。"))
                return

            q.put(("total", total_files))
            
            for i, filename in enumerate(files):
                full_input_path = os.path.join(input_dir, filename)
                full_output_path = os.path.join(output_dir, filename)

                q.put(("status", f"正在处理: {filename}"))
                q.put(("progress", i + 1))

                try:
                    self.deskew_image(full_input_path, full_output_path)
                except Exception as e:
                    q.put(("error", f"处理文件 {filename} 时发生错误: {e}"))
            
            q.put(("done", "处理完毕"))

        except Exception as e:
            q.put(("error", f"处理过程中发生意外错误: {e}"))
        finally:
            q.put(("finished", "")) # 线程完成信号

    def poll_queue(self):
        """定期从队列中获取更新并刷新GUI"""
        try:
            while True:
                # 非阻塞地从队列中获取消息
                msg_type, msg_value = self.process_queue.get_nowait()
                
                if msg_type == "total":
                    self.progress["maximum"] = msg_value
                    self.progress_label.config(text=f"0/{msg_value}")
                elif msg_type == "status":
                    self.status_label.config(text=msg_value)
                elif msg_type == "progress":
                    current_value = msg_value
                    total_value = self.progress["maximum"]
                    self.progress["value"] = current_value
                    self.progress_label.config(text=f"{current_value}/{total_value}")
                elif msg_type == "info":
                    messagebox.showinfo("信息", msg_value)
                elif msg_type == "error":
                    messagebox.showerror("错误", msg_value)
                elif msg_type == "done":
                    messagebox.showinfo("完成", msg_value)
                elif msg_type == "finished":
                    self.reset_ui()
                    return # 线程完成，停止轮询

        except queue.Empty:
            # 队列为空，继续轮询
            self.after(100, self.poll_queue)

    def deskew_image(self, input_path, output_path):
        """
        核心去偏斜函数，在新线程中运行
        """
        try:
            img = Image.open(input_path).convert("RGB")
            img_np = np.array(img)
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            edges = cv2.Canny(binary, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 200, minLineLength=200, maxLineGap=20)
            
            if lines is not None:
                horizontal_lines = []
                vertical_lines = []
                
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                    
                    if abs(angle) < 10 or abs(angle - 180) < 10:
                        horizontal_lines.append((length, angle))
                    elif abs(angle - 90) < 10 or abs(angle + 90) < 10:
                        vertical_lines.append((length, angle))

                all_angles = []
                horizontal_lines.sort(key=lambda item: item[0], reverse=True)
                for length, angle in horizontal_lines[:2]:
                    all_angles.append(angle)
                
                vertical_lines.sort(key=lambda item: item[0], reverse=True)
                for length, angle in vertical_lines[:2]:
                    if angle > 0:
                        all_angles.append(angle - 90)
                    else:
                        all_angles.append(angle + 90)
                
                if all_angles:
                    avg_angle = np.mean(all_angles)
                    rotated_img = img.rotate(avg_angle, expand=False, fillcolor=(0, 0, 0))
                    rotated_img.save(output_path)
                    return True
                else:
                    img.save(output_path)
                    return False
            else:
                img.save(output_path)
                return False

        except Exception as e:
            raise e # 抛出异常，让线程中的try-except块捕获

    def reset_ui(self):
        """重置GUI到初始状态"""
        self.progress["value"] = 0
        self.progress_label.config(text="0/0")
        self.status_label.config(text="处理完成")
        self.start_button.config(state="normal")
        self.processing_thread = None

if __name__ == "__main__":
    app = DeskewApp()
    app.mainloop()
