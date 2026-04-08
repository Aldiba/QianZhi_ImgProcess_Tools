import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

class TransparentTool:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG 像素透明度批量处理器")
        self.root.geometry("500x300")

        # 变量存储
        self.folder_path = tk.StringVar()
        self.threshold = tk.IntVar(value=128)  # 默认阈值设为一半

        self.setup_ui()

    def setup_ui(self):
        # 文件夹选择
        tk.Label(self.root, text="选择包含 PNG 的文件夹:").pack(pady=10)
        frame_path = tk.Frame(self.root)
        frame_path.pack(fill="x", padx=20)
        
        tk.Entry(frame_path, textvariable=self.folder_path).pack(side="left", expand=True, fill="x")
        tk.Button(frame_path, text="浏览", command=self.select_folder).pack(side="right", padx=5)

        # 阈值设置
        tk.Label(self.root, text="透明度阈值 (0-255):").pack(pady=10)
        tk.Scale(self.root, from_=0, to=255, orient="horizontal", variable=self.threshold).pack(fill="x", padx=40)
        tk.Label(self.root, text="注：Alpha 值低于此值的像素将变为全透明 (0)", fg="gray").pack()

        # 执行按钮
        tk.Button(self.root, text="开始处理", command=self.process_images, 
                  bg="#4CAF50", fg="white", height=2, width=20).pack(pady=20)

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)

    def process_images(self):
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("错误", "请先选择有效的文件夹！")
            return

        threshold_val = self.threshold.get()
        output_folder = os.path.join(folder, "processed_transparent")
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        count = 0
        try:
            for filename in os.listdir(folder):
                if filename.lower().endswith('.png'):
                    img_path = os.path.join(folder, filename)
                    img = Image.open(img_path).convert("RGBA")
                    datas = img.getdata()

                    new_data = []
                    for item in datas:
                        # item 是 (R, G, B, A)
                        if item[3] < threshold_val:
                            # 将 Alpha 设为 0
                            new_data.append((item[0], item[1], item[2], 0))
                        else:
                            new_data.append(item)

                    img.putdata(new_data)
                    img.save(os.path.join(output_folder, filename), "PNG")
                    count += 1
            
            messagebox.showinfo("完成", f"处理完成！\n共处理图片: {count} 张\n保存位置: {output_folder}")
        except Exception as e:
            messagebox.showerror("出错", f"处理过程中发生错误: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TransparentTool(root)
    root.mainloop()