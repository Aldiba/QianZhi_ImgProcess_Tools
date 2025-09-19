import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Progressbar
# from PIL import Image, ImageTk # Not strictly necessary for this version

def stitch_images(image_paths, direction="vertical"):
    """
    Stitches multiple images either vertically or horizontally.
    Adjusts dimensions to match for seamless stitching.
    Returns the stitched image as a NumPy array.

    Args:
        image_paths (list): A list of paths to the images to be stitched.
        direction (str): "vertical" for vertical stitching, "horizontal" for horizontal.
                         Defaults to "vertical".
    """
    if not image_paths:
        return None

    images = []
    for path in image_paths:
        # Robustly read image for non-ASCII paths
        img_bytes = np.fromfile(path, np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        if img is not None:
            images.append(img)
        else:
            print(f"Warning: Could not read image '{path}'. Skipping.")

    if not images:
        return None

    if direction == "vertical":
        # Find the maximum width among all images for vertical stacking
        max_dim = max(img.shape[1] for img in images) # Max width
        # Check if the combined height might exceed limits (rough estimate)
        total_height_estimate = sum(img.shape[0] * (max_dim / img.shape[1]) for img in images) if images else 0
        if total_height_estimate > 65000: # Slightly less than 65500 for safety margin
            print(f"Warning: Estimated total height {total_height_estimate} pixels exceeds typical max dimension for vertical stitch.")

    elif direction == "horizontal":
        # Find the maximum height among all images for horizontal stacking
        max_dim = max(img.shape[0] for img in images) # Max height
        # Check if the combined width might exceed limits (rough estimate)
        total_width_estimate = sum(img.shape[1] * (max_dim / img.shape[0]) for img in images) if images else 0
        if total_width_estimate > 65000: # Slightly less than 65500 for safety margin
            print(f"Warning: Estimated total width {total_width_estimate} pixels exceeds typical max dimension for horizontal stitch.")
    else:
        raise ValueError("Direction must be 'vertical' or 'horizontal'.")

    # Resize images to the max dimension along the non-stitching axis
    resized_images = []
    for img in images:
        if direction == "vertical":
            # Resize width to max_dim (max_width), maintaining aspect ratio
            if img.shape[1] != max_dim:
                new_height = int(img.shape[0] * (max_dim / img.shape[1]))
                resized_img = cv2.resize(img, (max_dim, new_height), interpolation=cv2.INTER_AREA)
                resized_images.append(resized_img)
            else:
                resized_images.append(img)
        elif direction == "horizontal":
            # Resize height to max_dim (max_height), maintaining aspect ratio
            if img.shape[0] != max_dim:
                new_width = int(img.shape[1] * (max_dim / img.shape[0]))
                resized_img = cv2.resize(img, (new_width, max_dim), interpolation=cv2.INTER_AREA)
                resized_images.append(resized_img)
            else:
                resized_images.append(img)

    # Stack the resized images
    if direction == "vertical":
        stitched_image = np.vstack(resized_images)
    elif direction == "horizontal":
        stitched_image = np.hstack(resized_images)

    return stitched_image

def image_stitcher_gui():
    """
    Creates the GUI for selecting folders, stitching images, and showing progress.
    """
    root = tk.Tk()
    root.title("图片拼接工具")
    root.geometry("680x550") # Adjust initial window size for new controls
    root.resizable(False, False) # Prevent resizing

    input_folder_path = tk.StringVar()
    output_file_path = tk.StringVar()
    stitch_direction = tk.StringVar(value="vertical") # Default to vertical stitching
    images_per_batch = tk.IntVar(value=0) # Default to 0, meaning all in one batch

    def select_input_folder():
        folder_selected = filedialog.askdirectory(title="选择图片源文件夹")
        if folder_selected:
            input_folder_path.set(folder_selected)

    def select_output_file():
        file_selected = filedialog.asksaveasfilename(
            title="保存拼接图片为",
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_selected:
            output_file_path.set(file_selected)

    def validate_batch_size():
        try:
            val = images_per_batch.get()
            if val < 0:
                messagebox.showwarning("无效输入", "每批图片数量不能为负数。设置为 0 则不分批。")
                images_per_batch.set(0)
            # If 0, it means all in one batch
        except tk.TclError: # Catches non-integer input
            messagebox.showwarning("无效输入", "每批图片数量必须是整数。设置为 0 则不分批。")
            images_per_batch.set(0) # Reset to default if invalid

    def start_stitching_process():
        input_folder = input_folder_path.get()
        output_base_file = output_file_path.get()
        direction = stitch_direction.get()
        batch_size = images_per_batch.get()

        if not input_folder:
            messagebox.showwarning("警告", "请选择图片源文件夹！")
            return
        if not output_base_file:
            messagebox.showwarning("警告", "请选择拼接图片保存路径和文件名！")
            return

        # Clear progress bar and status
        progress_bar['value'] = 0
        status_label.config(text="正在准备...")
        root.update_idletasks()

        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        all_image_paths = []
        for filename in sorted(os.listdir(input_folder)):
            full_path = os.path.join(input_folder, filename)
            if filename.lower().endswith(image_extensions) and os.path.isfile(full_path):
                all_image_paths.append(full_path)

        if not all_image_paths:
            messagebox.showwarning("警告", "源文件夹中未找到任何图片文件！")
            status_label.config(text="未找到图片。")
            return

        total_images = len(all_image_paths)
        if total_images == 0:
            messagebox.showinfo("完成", "没有图片可以拼接。")
            status_label.config(text="完成。")
            return

        # Determine batching strategy
        if batch_size <= 0 or batch_size >= total_images:
            # If batch_size is 0 or too large, process all in one go
            batches = [all_image_paths]
            num_batches = 1
            status_label.config(text=f"发现 {total_images} 张图片，将整体拼接 ({'垂直' if direction == 'vertical' else '水平'})...")
            # Warn if single batch might be too large (heuristic check)
            if total_images > 50 and (direction == "vertical" or direction == "horizontal"): # Arbitrary threshold
                response = messagebox.askyesno("警告", "您选择不分批处理所有图片。如果图片数量过多，拼接后尺寸可能超过系统限制导致保存失败。是否继续？")
                if not response:
                    status_label.config(text="操作已取消。")
                    return
        else:
            batches = [all_image_paths[i:i + batch_size] for i in range(0, total_images, batch_size)]
            num_batches = len(batches)
            status_label.config(text=f"发现 {total_images} 张图片，将分 {num_batches} 批次拼接 ({'垂直' if direction == 'vertical' else '水平'})...")
        
        root.update_idletasks()

        output_dir, output_name_ext = os.path.split(output_base_file)
        output_name, output_ext = os.path.splitext(output_name_ext)

        successful_saves = 0
        failed_saves = 0

        for i, batch_image_paths in enumerate(batches):
            current_batch_num = i + 1
            status_label.config(text=f"正在处理第 {current_batch_num}/{num_batches} 批次 ({len(batch_image_paths)} 张图片)...")
            root.update_idletasks()

            try:
                stitched_image = stitch_images(batch_image_paths, direction=direction)

                if stitched_image is None:
                    messagebox.showerror("错误", f"第 {current_batch_num} 批次拼接失败，可能没有可处理的图片。")
                    failed_saves += 1
                    continue

                # Generate output filename for current batch
                if num_batches > 1:
                    batch_output_file = os.path.join(output_dir, f"{output_name}_part{current_batch_num}{output_ext}")
                else: # Single batch, use the original chosen filename
                    batch_output_file = output_base_file

                # Save the stitched image (robustly for non-ASCII paths)
                encode_param = []
                if output_ext.lower() in ('.jpg', '.jpeg'):
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
                elif output_ext.lower() == '.png':
                    encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 9]

                is_success, buffer = cv2.imencode(output_ext, stitched_image, encode_param)
                if is_success:
                    buffer.tofile(batch_output_file)
                    successful_saves += 1
                    print(f"成功保存批次 {current_batch_num} 到: {batch_output_file}")
                else:
                    raise Exception("Failed to encode image for saving.")

            except Exception as e:
                # Catch the specific OpenCV dimension error more gracefully
                if "Maximum supported image dimension is 65500 pixels" in str(e):
                     messagebox.showerror("保存失败", f"第 {current_batch_num} 批次图片拼接后尺寸过大 ({stitched_image.shape[1]}x{stitched_image.shape[0]} 像素)，超出 OpenCV 限制 (通常为 65500 像素)。请尝试减少 '每批图片数量' 或缩小原图。")
                else:
                    messagebox.showerror("错误", f"处理第 {current_batch_num} 批次时发生错误: {e}")
                print(f"Error during stitching batch {current_batch_num}: {e}")
                failed_saves += 1

            # Update progress bar based on batch progress
            progress_bar['value'] = (current_batch_num / num_batches) * 100
            root.update_idletasks()

        progress_bar['value'] = 100
        final_message = f"所有批次处理完成！\n成功保存 {successful_saves} 张长图。\n失败 {failed_saves} 张长图。"
        messagebox.showinfo("完成", final_message)
        status_label.config(text="完成。")


    # --- GUI Layout using Grid ---
    root.grid_columnconfigure(0, weight=0) # Label column, fixed width
    root.grid_columnconfigure(1, weight=1) # Entry column, expands
    root.grid_columnconfigure(2, weight=0) # Button column, fixed width

    # Input Folder Section
    row_idx = 0
    tk.Label(root, text="图片源文件夹:").grid(row=row_idx, column=0, padx=10, pady=(20, 5), sticky="w")
    tk.Entry(root, textvariable=input_folder_path, width=50, state='readonly').grid(row=row_idx, column=1, padx=5, pady=(20, 5), sticky="ew")
    tk.Button(root, text="选择源文件夹", command=select_input_folder, width=15).grid(row=row_idx, column=2, padx=10, pady=(20, 5), sticky="e")

    # Output File Section
    row_idx += 1
    tk.Label(root, text="拼接保存路径:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
    tk.Entry(root, textvariable=output_file_path, width=50, state='readonly').grid(row=row_idx, column=1, padx=5, pady=5, sticky="ew")
    tk.Button(root, text="选择保存路径", command=select_output_file, width=15).grid(row=row_idx, column=2, padx=10, pady=5, sticky="e")

    # Stitching Direction Selection
    row_idx += 1
    tk.Label(root, text="拼接方向:").grid(row=row_idx, column=0, padx=10, pady=15, sticky="w")
    
    direction_frame = tk.Frame(root)
    direction_frame.grid(row=row_idx, column=1, columnspan=2, padx=5, pady=15, sticky="w")

    tk.Radiobutton(direction_frame, text="垂直拼接", variable=stitch_direction, value="vertical").pack(side=tk.LEFT, padx=10)
    tk.Radiobutton(direction_frame, text="水平拼接", variable=stitch_direction, value="horizontal").pack(side=tk.LEFT, padx=10)

    # Batch Size Input
    row_idx += 1
    tk.Label(root, text="每批图片数量:").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
    batch_entry = tk.Entry(root, textvariable=images_per_batch, width=10)
    batch_entry.grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")
    tk.Label(root, text="(0为不分批，即全部拼接)").grid(row=row_idx, column=1, padx=(100,0), pady=5, sticky="w")
    batch_entry.bind("<FocusOut>", lambda e: validate_batch_size()) # Validate on losing focus

    # Start Button
    row_idx += 1
    tk.Button(root, text="开始拼接", command=start_stitching_process, bg="#4CAF50", fg="white", width=20, height=2).grid(row=row_idx, column=0, columnspan=3, pady=30)

    # Progress Bar
    row_idx += 1
    progress_bar = Progressbar(root, orient="horizontal", length=400, mode="determinate")
    progress_bar.grid(row=row_idx, column=0, columnspan=3, pady=10)

    # Status Label
    row_idx += 1
    status_label = tk.Label(root, text="等待操作...", fg="blue")
    status_label.grid(row=row_idx, column=0, columnspan=3, pady=5)


    root.mainloop()

if __name__ == "__main__":
    image_stitcher_gui()