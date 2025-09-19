import os
from PIL import Image
from tkinter import filedialog
def convert_dds_to_jpg(source_folder, target_folder):
    """
    批量将 DDS 图片转换为 JPG 格式并保存到目标文件夹。

    :param source_folder: 包含 DDS 图片的源文件夹路径。
    :param target_folder: 保存 JPG 图片的目标文件夹路径。
    """
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 遍历源文件夹中的文件
    for file_name in os.listdir(source_folder):
        if file_name.lower().endswith('.dds'):
            source_path = os.path.join(source_folder, file_name)
            target_path = os.path.join(target_folder, file_name.rsplit('.', 1)[0] + '.jpg')

            try:
                # 打开 DDS 图片并转换为 RGB
                with Image.open(source_path) as img:
                    img = img.convert('RGB')
                    img.save(target_path, 'JPEG')
                    print(f"成功转换: {file_name} -> {target_path}")
            except Exception as e:
                print(f"转换失败: {file_name}, 错误: {e}")

# 示例使用
source_folder = filedialog.askdirectory(title="选择 DDS 图片文件夹")  # 替换为实际的 DDS 图片文件夹路径
target_folder = filedialog.askdirectory(title="选择 JPG 保存文件夹")  # 替换为实际的 JPG 保存文件夹路径

convert_dds_to_jpg(source_folder, target_folder)
