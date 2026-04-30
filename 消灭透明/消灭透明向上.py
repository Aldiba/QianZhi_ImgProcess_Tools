import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

def select_folder():
    """选择文件夹并更新路径显示"""
    folder = filedialog.askdirectory()
    if folder:
        path_var.set(folder)

def process_images():
    """处理选定文件夹中的所有 PNG 图片"""
    folder = path_var.get()
    if not folder:
        messagebox.showwarning("警告", "请先选择文件夹！")
        return

    # 支持的图片扩展名（仅处理带透明通道的 PNG）
    extensions = ('.png', '.PNG')
    processed = 0
    skipped = 0

    for filename in os.listdir(folder):
        if not filename.endswith(extensions):
            continue

        filepath = os.path.join(folder, filename)
        try:
            with Image.open(filepath) as img:
                # 转换为 RGBA 模式，确保有 Alpha 通道
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                # 分离通道
                r, g, b, a = img.split()
                # 将 Alpha > 250 的像素设为 255
                a = a.point(lambda x: 255 if x > 250 else x)
                # 合并通道
                new_img = Image.merge('RGBA', (r, g, b, a))

                # 覆盖保存（如需备份请自行修改）
                new_img.save(filepath, format='PNG')
                processed += 1
                log_msg(f"已处理：{filename}")
        except Exception as e:
            log_msg(f"处理失败 {filename}: {e}")
            skipped += 1

    messagebox.showinfo("完成", f"处理完成！\n成功处理：{processed} 个文件\n跳过/失败：{skipped} 个")
    log_text.insert(tk.END, "所有任务处理完毕。\n")

def log_msg(msg):
    """向文本框追加日志"""
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    root.update_idletasks()

# 创建主窗口
root = tk.Tk()
root.title("图片透明通道处理")
root.geometry("500x400")

path_var = tk.StringVar()

# 选择文件夹区域
frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="目标文件夹：").pack(side=tk.LEFT)
tk.Entry(frame_top, textvariable=path_var, width=40).pack(side=tk.LEFT, padx=5)
tk.Button(frame_top, text="浏览...", command=select_folder).pack(side=tk.LEFT)

# 处理按钮
tk.Button(root, text="开始处理 (Alpha > 250 → 255)", command=process_images, bg="lightblue").pack(pady=10)

# 日志区域
tk.Label(root, text="处理日志：").pack(anchor=tk.W, padx=10)
log_text = tk.Text(root, height=15, width=60)
log_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

# 说明标签
tk.Label(root, text="说明：仅处理文件夹根目录下的 PNG 图片，将 Alpha 通道中 >250 的像素设为 255（完全不透明）。\n直接覆盖原文件，如有重要数据请提前备份。",
         fg="gray", font=("Arial", 9)).pack(pady=5)

root.mainloop()