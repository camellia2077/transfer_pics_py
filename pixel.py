from PIL import Image
import os
import sys
import time # <<< Import time module
import traceback # Import traceback for better error reporting

# --- 常量定义 ---
SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')

def pixelate_image(input_path, output_path, pixel_size):
    """
    将输入图片转换为像素风格，并记录各步骤耗时。
    (此函数保持不变)
    Args:
        input_path (str): 输入图片的文件路径。
        output_path (str): 保存像素化图片的路径。
        pixel_size (int): 定义每个“大像素”块的边长。

    Returns:
        bool: True 如果成功, False 如果失败。
    """
    # --- Timing variables for steps inside the function ---
    t_open_start, t_open_end = 0, 0
    t_resize_down_start, t_resize_down_end = 0, 0
    t_resize_up_start, t_resize_up_end = 0, 0
    t_save_start, t_save_end = 0, 0
    func_total_start = 0 # Initialize here

    # --- 基本检查放在前面 ---
    if not os.path.exists(input_path):
        print(f"错误：找不到输入文件 '{input_path}'")
        return False
    if not os.path.isfile(input_path): # 确保是文件
         print(f"错误：输入路径 '{input_path}' 不是一个有效的文件。")
         return False
    if not isinstance(pixel_size, int) or pixel_size <= 0:
        print(f"错误：像素大小 ({pixel_size}) 必须是一个正整数。")
        return False

    print(f"\n--- 开始处理: {os.path.basename(input_path)} ---")
    func_total_start = time.perf_counter() # Start timer for the whole function's work

    try:
        # === Step 1: 打开并准备图片 ===
        t_open_start = time.perf_counter()
        img = Image.open(input_path)
        img = img.convert("RGB") # 转换为RGB以处理透明度等问题，并确保一致性
        original_width, original_height = img.size
        t_open_end = time.perf_counter()
        print(f"  原始图片尺寸: {original_width}x{original_height}")

        # === Step 2: 缩小图片 ===
        # 确保缩小后的尺寸至少为 1x1 像素
        small_width = max(1, original_width // pixel_size)
        small_height = max(1, original_height // pixel_size)
        print(f"  缩小后尺寸: {small_width}x{small_height}")

        t_resize_down_start = time.perf_counter()
        # 优先使用 Resampling.NEAREST (Pillow >= 9.0.0)
        try:
            small_img = img.resize((small_width, small_height), Image.Resampling.NEAREST)
        except AttributeError:
            # 兼容旧版 Pillow
            print("  警告：检测到旧版 Pillow (< 9.0.0)，使用 Image.NEAREST。建议更新 Pillow。")
            small_img = img.resize((small_width, small_height), Image.NEAREST)
        t_resize_down_end = time.perf_counter()

        # === Step 3: 放大图片 ===
        print(f"  放大回原始尺寸: {original_width}x{original_height}")
        t_resize_up_start = time.perf_counter()
        try:
            pixelated_img = small_img.resize((original_width, original_height), Image.Resampling.NEAREST)
        except AttributeError:
            pixelated_img = small_img.resize((original_width, original_height), Image.NEAREST)
        t_resize_up_end = time.perf_counter()

        # === Step 4: 保存结果 ===
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
             try:
                 os.makedirs(output_dir)
                 print(f"  已创建输出目录: {output_dir}")
             except OSError as e:
                 print(f"  错误：无法创建输出目录 '{output_dir}': {e}")
                 return False # 无法创建目录则无法保存

        t_save_start = time.perf_counter()
        # 保存时也指定格式，避免依赖扩展名（尤其对于非标准扩展名）
        save_format = os.path.splitext(output_path)[1].lower().strip('.')
        if save_format == 'jpg': save_format = 'jpeg' # Pillow 使用 'jpeg'
        if not save_format or f".{save_format}" not in SUPPORTED_EXTENSIONS:
            print(f"  警告：输出扩展名 '{save_format}' 未知或不支持，将尝试以 PNG 格式保存。")
            output_path = os.path.splitext(output_path)[0] + '.png'
            save_format = 'png'

        pixelated_img.save(output_path, format=save_format.upper()) # 指定格式
        t_save_end = time.perf_counter()
        print(f"  像素化图片成功保存到: {output_path}")

        # --- 打印内部步骤耗时 ---
        print("  --- 详细耗时 ---")
        print(f"     - 图片打开与转换: {t_open_end - t_open_start:.4f} 秒")
        print(f"     - 图片缩小:       {t_resize_down_end - t_resize_down_start:.4f} 秒")
        print(f"     - 图片放大:       {t_resize_up_end - t_resize_up_start:.4f} 秒")
        print(f"     - 图片保存:       {t_save_end - t_save_start:.4f} 秒")
        print("  ------------------")

        return True

    except FileNotFoundError:
        # 这个错误理论上在函数开始时已被捕获，但保留以防万一
        print(f"错误：找不到输入文件 '{input_path}'")
        return False
    except Exception as e:
        print(f"处理图片 '{os.path.basename(input_path)}' 时发生错误: {e}")
        traceback.print_exc() # 打印详细的错误堆栈信息
        return False
    finally:
        # Ensure total function time is recorded even on error (if func_total_start was set)
        if func_total_start > 0:
            func_total_end = time.perf_counter()
            print(f"--- 处理结束: {os.path.basename(input_path)} | 函数总耗时: {func_total_end - func_total_start:.4f} 秒 ---")

# --- 新函数：获取用户输入 ---
def get_user_inputs():
    """
    获取用户输入的源路径和像素大小。

    Returns:
        tuple: 包含 input_path (str) 和 pixel_block_size (int) 的元组。
               如果用户取消操作，则返回 (None, None)。
    """
    input_path = ""
    while not input_path:
        try:
            input_path = input("请输入源图片文件 或 包含图片的文件夹 的完整路径: ").strip().strip("'\"")
            if not input_path:
                print("输入不能为空，请重新输入。")
        except KeyboardInterrupt:
             print("\n操作已取消。")
             return None, None # 返回 None 表示取消

    pixel_block_size = 0
    while True:
        try:
            pixel_block_size_str = input("请输入所需的像素块大小 (整数, e.g., 8, 16): ")
            pixel_block_size = int(pixel_block_size_str)
            if pixel_block_size > 0:
                break
            else:
                print("像素块大小必须是正整数。")
        except ValueError:
            print("无效输入，请输入一个整数。")
        except KeyboardInterrupt:
            print("\n操作已取消。")
            return None, None # 返回 None 表示取消

    return input_path, pixel_block_size

# --- 新函数：处理单个文件 ---
def process_single_file(input_path, pixel_size):
    """
    处理单个图片文件。

    Args:
        input_path (str): 输入图片文件路径。
        pixel_size (int): 像素块大小。

    Returns:
        dict: 包含处理结果的字典:
              {'processed': int, 'success': int, 'failed': int, 'output_location': str or None}
    """
    print(f"\n检测到输入为单个文件: {input_path}")
    print("开始处理...")
    stats = {'processed': 0, 'success': 0, 'failed': 0, 'output_location': None}

    # 生成默认输出路径
    base, ext = os.path.splitext(input_path)
    output_image_path = f"{base}_pixelated{ext}"
    # 如果原扩展名不受支持，提示并改为 .png
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        print(f"警告：文件扩展名 '{ext}' 可能不受支持，将尝试处理并以 .png 格式保存。")
        output_image_path = f"{base}_pixelated.png"

    if pixelate_image(input_path, output_image_path, pixel_size):
        stats['success'] = 1
        stats['output_location'] = output_image_path
    else:
        stats['failed'] = 1
    stats['processed'] = 1
    return stats

# --- 新函数：处理文件夹 ---
def process_directory(input_path, pixel_size):
    """
    处理文件夹中的所有支持的图片文件。

    Args:
        input_path (str): 输入文件夹路径。
        pixel_size (int): 像素块大小。

    Returns:
        dict: 包含处理结果的字典:
              {'processed': int, 'success': int, 'failed': int, 'output_location': str or None}
              'output_location' 是输出文件夹的路径。
    """
    print(f"\n检测到输入为文件夹: {input_path}")
    print("开始批量处理...")
    stats = {'processed': 0, 'success': 0, 'failed': 0, 'output_location': None}

    # 创建输出文件夹
    input_folder_name = os.path.basename(os.path.abspath(input_path))
    # 将输出文件夹创建在与输入文件夹同级的目录下
    parent_dir = os.path.dirname(os.path.abspath(input_path))
    output_dir = os.path.join(parent_dir, f"{input_folder_name}_pixelated")

    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"结果将保存到文件夹: {output_dir}")
        stats['output_location'] = output_dir
    except OSError as e:
        print(f"错误：无法创建输出目录 '{output_dir}': {e}")
        print("处理中止。")
        stats['failed'] = 1 # 标记为失败，因为无法创建目录
        return stats # 提前返回

    # 遍历文件夹
    print("开始扫描文件夹...")
    image_files_found = 0
    try:
        items_in_dir = list(os.scandir(input_path)) # 获取列表以计算总数
        total_items = len(items_in_dir)

        for i, entry in enumerate(items_in_dir):
            current_file_number = i + 1
            print(f"\n[{current_file_number}/{total_items}] 检查: {entry.name}")
            if entry.is_file():
                file_ext = os.path.splitext(entry.name)[1].lower()
                if file_ext in SUPPORTED_EXTENSIONS:
                    image_files_found += 1
                    stats['processed'] += 1
                    current_input_path = entry.path
                    base, ext = os.path.splitext(entry.name)
                    current_output_path = os.path.join(output_dir, f"{base}_pixelated{ext}")

                    # 处理单个图片
                    if pixelate_image(current_input_path, current_output_path, pixel_size):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                else:
                    print(f"  跳过: '{entry.name}' (非支持的图片格式)")
            else:
                 print(f"  跳过: '{entry.name}' (不是文件)")

        if image_files_found == 0:
             print("\n在指定文件夹中未找到支持的图片文件。")

    except FileNotFoundError:
         print(f"错误：扫描时找不到文件夹 '{input_path}'。")
         stats['failed'] = 1 # 标记为失败
    except Exception as e:
         print(f"扫描或处理文件夹 '{input_path}' 时发生意外错误: {e}")
         traceback.print_exc()
         stats['failed'] = max(1, stats['failed']) # 确保至少标记为1个失败

    return stats


# --- 新函数：打印最终总结 ---
def print_summary(results, duration):
    """
    打印处理结果的最终总结。

    Args:
        results (dict): process_path 返回的结果字典。
        duration (float): 总处理耗时。
    """
    print("\n===================================")
    print("           处理结果总结")
    print("===================================")

    total_files_processed = results.get('processed', 0)
    success_count = results.get('success', 0)
    fail_count = results.get('failed', 0)
    output_location = results.get('output_location')
    input_type = results.get('input_type', 'unknown') # 'file', 'directory', 'invalid', 'unknown'

    if input_type == 'invalid':
         print("处理失败，输入的路径无效。")
    elif total_files_processed > 0:
        print(f"总共尝试处理图片文件数量: {total_files_processed}")
        print(f"  - 成功: {success_count}")
        print(f"  - 失败: {fail_count}")
        if success_count > 0 and output_location:
             if input_type == 'directory':
                 print(f"\n成功处理的文件已保存至文件夹: {output_location}")
             elif input_type == 'file':
                 print(f"\n成功处理的文件已保存为: {output_location}")
    elif input_type == 'directory' and total_files_processed == 0 :
         print("在指定文件夹中未找到可处理的图片文件。")
    elif fail_count > 0 and input_type != 'invalid': # Handle directory creation failure etc.
         print(f"处理过程中遇到错误 ({fail_count} 个失败)。")
    else:
        print("没有文件被处理。")

    print(f"\n总处理耗时 (包含文件扫描): {duration:.4f} 秒")
    print("===================================")

# --- 主程序入口 ---
def main():
    """主执行函数"""
    print("--- 图片像素化工具 ---")
    print(f"支持的图片格式: {', '.join(SUPPORTED_EXTENSIONS)}")

    # === 获取输入 ===
    input_path, pixel_block_size = get_user_inputs()

    # 如果用户取消输入，则退出
    if input_path is None or pixel_block_size is None:
        sys.exit(0) # 正常退出

    # <<< 开始总计时 >>>
    processing_start_time = time.perf_counter()
    results = {'processed': 0, 'success': 0, 'failed': 0, 'output_location': None, 'input_type': 'unknown'}

    # === 判断路径类型并处理 ===
    if os.path.isfile(input_path):
        results = process_single_file(input_path, pixel_block_size)
        results['input_type'] = 'file'
    elif os.path.isdir(input_path):
        results = process_directory(input_path, pixel_block_size)
        results['input_type'] = 'directory'
    else:
        print(f"\n错误：输入的路径 '{input_path}' 不是一个有效的文件或文件夹。")
        results['failed'] = 1 # 标记为失败
        results['input_type'] = 'invalid'

    # <<< 结束总计时 >>>
    processing_end_time = time.perf_counter()
    total_processing_duration = processing_end_time - processing_start_time

    # === 输出总结 ===
    print_summary(results, total_processing_duration)

if __name__ == "__main__":
    main()