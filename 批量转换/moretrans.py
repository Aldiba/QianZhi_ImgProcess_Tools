import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

def get_image_formats(folder):
    """
    获取文件夹中所有图片的格式（不重复）
    """
    formats = set()
    if not os.path.exists(folder):
        return []
    
    for filename in os.listdir(folder):
        try:
            with Image.open(os.path.join(folder, filename)) as img:
                formats.add(img.format.upper())
        except (IOError, ValueError):
            continue
    return sorted(list(formats))

def convert_images_task(input_folder, output_folder, from_format, to_format, progress_bar, status_label, start_button):
    """
    实际执行图片转换任务的函数，在新线程中运行
    """
    start_button.config(state=tk.DISABLED) # 转换开始，禁用按钮

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    files_to_convert = [f for f in os.listdir(input_folder) if f.lower().endswith(from_format.lower())]
    total_files = len(files_to_convert)

    if total_files == 0:
        messagebox.showinfo("提示", f"输入文件夹中没有找到 {from_format} 格式的图片。")
        progress_bar['value'] = 0
        status_label.config(text="")
        start_button.config(state=tk.NORMAL)
        return

    count_success = 0
    progress_bar['value'] = 0
    progress_bar['maximum'] = total_files

    for i, filename in enumerate(files_to_convert):
        input_path = os.path.join(input_folder, filename)
        base_name = os.path.splitext(filename)[0]
        if to_format.upper() == 'JPEG':
            output_filename = f"{base_name}.jpg"
        else:
            output_filename = f"{base_name}.{to_format.lower()}"
        output_path = os.path.join(output_folder, output_filename)

        try:
            img = Image.open(input_path)
            # 转换模式以避免JPG保存问题（如RGBA模式）
            if img.mode == 'RGBA' and to_format.upper() == 'JPEG':
                img = img.convert('RGB')
            img.save(output_path, to_format.upper())
            count_success += 1
            status_label.config(text=f"正在转换：{filename}")
        except Exception as e:
            status_label.config(text=f"转换失败：{filename} - {e}")
        
        # 更新进度条
        progress_bar['value'] = i + 1
        root.update_idletasks() # 强制更新UI

    messagebox.showinfo("完成", f"转换完成！\n成功: {count_success} 张\n失败: {total_files - count_success} 张")
    progress_bar['value'] = 0
    status_label.config(text="")
    start_button.config(state=tk.NORMAL) # 转换结束，启用按钮

def start_conversion_thread():
    """
    启动新线程来执行转换任务，防止UI卡顿
    """
    input_folder = input_entry.get()
    output_folder = output_entry.get()
    from_format = from_format_var.get()
    to_format = to_format_var.get()

    if not input_folder or not output_folder:
        messagebox.showerror("错误", "请选择输入和输出文件夹！")
        return

    if not from_format or not to_format:
        messagebox.showerror("错误", "请选择源格式和目标格式！")
        return

    # 创建并启动一个新线程
    thread = threading.Thread(
        target=convert_images_task,
        args=(input_folder, output_folder, from_format, to_format, progress_bar, status_label, start_button)
    )
    thread.start()

def select_input_folder():
    """
    选择输入文件夹并更新格式列表
    """
    folder = filedialog.askdirectory(title="选择 来源 图片文件夹")
    if folder:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, folder)
        
        # 获取并更新格式列表
        image_formats = get_image_formats(folder)
        from_format_var.set('') # 清空当前选择
        from_format_menu['menu'].delete(0, 'end') # 清空菜单
        for f in image_formats:
            from_format_menu['menu'].add_command(label=f, command=tk._setit(from_format_var, f))
        
        # 自动选择第一个格式（如果存在）
        if image_formats:
            from_format_var.set(image_formats[0])

# --- UI 界面 ---
root = tk.Tk()
root.title("图片格式批量转换工具")
root.geometry("500x350")

# 输入文件夹
input_frame = tk.Frame(root, padx=10, pady=5)
input_frame.pack(fill=tk.X)
tk.Label(input_frame, text="输入文件夹:", width=10).pack(side=tk.LEFT)
input_entry = tk.Entry(input_frame)
input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
tk.Button(input_frame, text="选择...", command=select_input_folder).pack(side=tk.LEFT)

# 输出文件夹
output_frame = tk.Frame(root, padx=10, pady=5)
output_frame.pack(fill=tk.X)
tk.Label(output_frame, text="输出文件夹:", width=10).pack(side=tk.LEFT)
output_entry = tk.Entry(output_frame)
output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
tk.Button(output_frame, text="选择...", command=lambda: output_entry.insert(0, filedialog.askdirectory(title="选择 保存 图片文件夹"))).pack(side=tk.LEFT)

# 格式选择
format_frame = tk.Frame(root, padx=10, pady=5)
format_frame.pack(fill=tk.X)
tk.Label(format_frame, text="从格式:").pack(side=tk.LEFT)
from_format_var = tk.StringVar(root)
from_format_menu = tk.OptionMenu(format_frame, from_format_var, '') # 初始为空
from_format_menu.pack(side=tk.LEFT, padx=(0, 20))

tk.Label(format_frame, text="到格式:").pack(side=tk.LEFT)
to_format_var = tk.StringVar(root)
all_formats = ["PNG", "JPEG", "BMP", "DDS", "TGA", "GIF", "TIFF"]
to_format_var.set(all_formats[1])
tk.OptionMenu(format_frame, to_format_var, *all_formats).pack(side=tk.LEFT)

# 进度条
progress_frame = tk.Frame(root, padx=10, pady=10)
progress_frame.pack(fill=tk.X)
status_label = tk.Label(progress_frame, text="", fg="blue")
status_label.pack(side=tk.TOP, pady=5)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", length=450)
progress_bar.pack(fill=tk.X)

# 转换按钮
start_button = tk.Button(root, text="开始转换", command=start_conversion_thread, font=("Helvetica", 12), padx=20, pady=10)
start_button.pack(pady=20)

root.mainloop()