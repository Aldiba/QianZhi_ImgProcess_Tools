import os
from PIL import Image
from tkinter import filedialog, messagebox

def convert_jpg_to_png(source_folder, target_folder):
    """
    批量将 JPG 图片转换为 PNG 格式。
    """
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 获取所有 jpg/jpeg 文件
    valid_extensions = ('.jpg', '.jpeg')
    files = [f for f in os.listdir(source_folder) if f.lower().endswith(valid_extensions)]

    if not files:
        print("未在源文件夹中找到 JPG 图片。")
        return

    success_count = 0
    fail_count = 0

    for file_name in files:
        source_path = os.path.join(source_folder, file_name)
        # 获取不带后缀的文件名，并拼接新的后缀
        base_name = os.path.splitext(file_name)[0]
        target_path = os.path.join(target_folder, base_name + '.png')

        try:
            with Image.open(source_path) as img:
                # JPG 不支持透明度，直接保存为 PNG 即可
                # 如果原图是 CMYK 模式，建议转一下 RGB 保证兼容性
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img.save(target_path, 'PNG')
                print(f"成功: {file_name} -> {base_name}.png")
                success_count += 1
        except Exception as e:
            print(f"失败: {file_name}, 错误: {e}")
            fail_count += 1

    print(f"\n任务完成！成功: {success_count}, 失败: {fail_count}")
    messagebox.showinfo("完成", f"转换结束！\n成功: {success_count}\n失败: {fail_count}")

# 交互选择文件夹
source = filedialog.askdirectory(title="选择包含 JPG 的源文件夹")
if source:
    target = filedialog.askdirectory(title="选择输出 PNG 的目标文件夹")
    if target:
        convert_jpg_to_png(source, target)