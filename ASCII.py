# -*- coding: utf-8 -*-
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import math
import traceback 
import time 
import numpy as np

# --- 配置 ---
ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
OUTPUT_WIDTH_CHARS = 2048 # ASCII 表示的宽度（以字符为单位）

FONT_FILENAME = "Consolas.ttf" #从程序同目录加载指定字体文件名
FONT_SIZE = 15
RESIZE_OUTPUT = True # 设置为 True 以将输出 PNG 调整为原始宽高比

# 定义支持的图片文件扩展名（不区分大小写）
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

# --- 颜色主题配置 ---
COLOR_THEMES = {
    "dark":           {"background": "black", "foreground": "white"},#黑底白字
    "green_term":     {"background": "black", "foreground": "lime"},#黑底绿字
    # --- 修改后的 ---
    "light":          {"background": "#f0f0f0", "foreground": "black"}, #灰底黑字
    "amber_term":     {"background": "#1c1c1c", "foreground": "#FFBF00"},#黑底黄字
    "original":       {"background": "black", "foreground": None}, #黑底彩色
    # --- 修改后的 ---
    "original_light_bg": {"background": "#f0f0f0", "foreground": None}, # 灰底彩色
}

# --- 选择要生成的主题 ---
THEMES_TO_GENERATE = [
    #"dark",
    #"green_term",
    #"original",
    "original_light_bg",
    #"light",
    #"amber_term",
]


def image_to_ascii(color_image, width_chars, active_theme_name, needs_color_map=False):
    """
    使用 NumPy 将 PIL 彩色图像根据亮度转换为 ASCII 字符串列表。
    如果 needs_color_map 为 True，则可选地返回调整大小后的颜色映射图像。
    """
    try:
        image_rgb = color_image.convert('RGB')
        image_gray = image_rgb.convert('L')

        original_width, original_height = image_rgb.size
        aspect_ratio = original_height / float(original_width) if original_width > 0 else 1

        # 调整字符宽高比
        char_aspect_ratio_correction = 0.5
        new_height_chars = int(width_chars * aspect_ratio * char_aspect_ratio_correction)
        new_height_chars = max(1, new_height_chars) # 确保至少有一行

        # 调整灰度图像的大小以进行亮度映射
        resized_gray = image_gray.resize((width_chars, new_height_chars), Image.Resampling.NEAREST)

        # 将调整大小后的灰度图像转换为 NumPy 数组
        gray_pixels_np = np.array(resized_gray, dtype=np.uint8) # 确保为 uint8 类型

        color_map_image = None
        if needs_color_map:
            # 调整原始彩色图像的大小以进行逐像素颜色采样
            color_map_image = image_rgb.resize((width_chars, new_height_chars), Image.Resampling.NEAREST)

        num_chars = len(ASCII_CHARS)
        # 创建一个 NumPy ASCII 字符数组以实现快速映射
        ascii_map = np.array(list(ASCII_CHARS))

        # 判断背景是浅色还是深色
        theme_bg = COLOR_THEMES.get(active_theme_name, {}).get("background", "black").lower()
        # 确保检查包含可能修改过的浅色背景色
        is_light_bg = theme_bg in ["white", "#ffffff", "lightgrey", "#d3d3d3", "#fff", "ivory", "#f0f0f0"]

        # --- 字符索引的向量化计算 ---
        if is_light_bg:
            # 浅色背景：较亮的像素 -> 较密的字符（较低索引）
            char_indices = np.floor((255.0 - gray_pixels_np) * (num_chars / 256.0)).astype(int)
        else:
            # 深色背景：较亮的像素 -> 较浅的字符（较高索引）
            char_indices = np.floor(gray_pixels_np * (num_chars / 256.0)).astype(int)

        # 裁剪索引以确保它们在有效范围 [0, num_chars - 1] 内
        char_indices = np.clip(char_indices, 0, num_chars - 1)
        # --- 向量化计算结束 ---

        # 使用索引从字符映射数组中获取字符
        ascii_grid = ascii_map[char_indices]
        # 将二维字符数组转换为字符串列表（每行一个字符串）
        ascii_str_list = ["".join(row) for row in ascii_grid]

        return ascii_str_list, color_map_image

    except Exception as e:
        print(f"在主题 '{active_theme_name}' 的 ASCII 转换（NumPy）过程中出错: {e}")
        traceback.print_exc()
        return None, None



def create_ascii_png(ascii_lines,
                      color_map_image,
                      theme_name,
                      output_path,
                      font,
                      background_color,
                      foreground_color, # 用于非原始颜色主题
                      original_image_size=None):
    """
    根据 ASCII 字符串行创建 PNG 图像。如果 theme_name 表示原始颜色主题，
    则使用 color_map_image 中的颜色，否则使用 foreground_color。
    可选地调整输出 PNG 的大小。
    """
    if not ascii_lines or not ascii_lines[0]:
        print("错误：没有 ASCII 数据或空行来创建 PNG。")
        return False # 表示失败

    is_original_color_theme = theme_name in ["original", "original_light_bg"]

    try:
        # --- 精确确定文本渲染尺寸 ---
        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        try:
            # 使用包含升部和降部的字符来获取行高
            bbox = draw.textbbox((0, 0), '|M_g(`', font=font)
            line_height = bbox[3] - bbox[1]
            # 使用第一行实际文本获取宽度
            bbox_width = draw.textbbox((0, 0), ascii_lines[0], font=font)
            text_width = bbox_width[2] - bbox_width[0]
        except AttributeError:
            # 对旧版 Pillow 使用 textsize/textlength 的后备方案
            print("警告：正在使用较旧的 Pillow 文本测量方法（textsize/textlength）。尺寸可能不太准确。")
            try:
                (_, h) = draw.textsize('|M_g(`', font=font)
                line_height = h
                (w, _) = draw.textsize(ascii_lines[0], font=font)
                text_width = w
            except AttributeError: # 如果 textsize 对复杂字符串失败，使用更旧的后备方案
                (_, h) = draw.textsize('M', font=font)
                line_height = int(h * 1.2) # 近似值
                (w, _) = draw.textsize('M'*len(ascii_lines[0]), font=font)
                text_width = w # 粗略估计

        line_spacing = line_height + 2 # 在行之间添加少量间距
        if line_spacing <=0 : line_spacing = font.size + 2
        if text_width <= 0: text_width = font.size * len(ascii_lines[0]) # 如果计算失败则估算

        img_width = max(1, text_width)
        img_height = max(1, line_spacing * len(ascii_lines))

        # --- 创建图像并绘制文本 ---
        output_image = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(output_image)

        y_text = 0
        if is_original_color_theme and color_map_image:
            # --- 使用颜色映射逐字符绘制 ---
            # 使用 .load() 以可能更快地在循环中访问像素
            color_pixels = color_map_image.load()
            # 估算平均字符宽度以定位，更精确的方法是测量每个字符，但较慢。
            avg_char_width = text_width / len(ascii_lines[0]) if ascii_lines[0] else font.size
            for y, line in enumerate(ascii_lines):
                x_pos = 0
                for x, char in enumerate(line):
                    try:
                        # 使用已加载的像素对象
                        char_color = color_pixels[x, y]

                        # 可选：为浅色背景加深颜色，当为灰色背景时
                        if theme_name == "original_light_bg":
                            darken_factor = 0.75
                            r, g, b = char_color
                            new_r = max(0, min(255, int(r * darken_factor)))
                            new_g = max(0, min(255, int(g * darken_factor)))
                            new_b = max(0, min(255, int(b * darken_factor)))
                            char_color = (new_r, new_g, new_b)

                        # 绘制单个字符
                        draw.text((math.floor(x_pos), y_text), char, font=font, fill=char_color)
                        # 前进 x 位置 - 使用平均宽度是速度和精度的折中
                        x_pos += avg_char_width
                    except IndexError:
                        print(f"警告：坐标 ({x},{y}) 超出 color_map_image 的边界。使用后备颜色。")
                        draw.text((math.floor(x_pos), y_text), char, font=font, fill="red") # 后备颜色
                        x_pos += avg_char_width
                    except Exception as char_err:
                        print(f"警告：在文本位置 ({x_pos:.0f},{y_text}) 绘制字符 '{char}' 时出错: {char_err}")
                        x_pos += avg_char_width # 仍然前进位置
                y_text += line_spacing
        else:
            # --- 使用固定的前景色逐行绘制 ---
            # 非彩色主题逐行绘制（已经很高效）
            if foreground_color is None:
                print(f"错误：非原始颜色主题 '{theme_name}' 缺少前景色。使用白色。")
                effective_fg_color = "white"
            else:
                effective_fg_color = foreground_color
            for line in ascii_lines:
                draw.text((0, y_text), line, font=font, fill=effective_fg_color)
                y_text += line_spacing

        # --- 可选的尺寸调整 ---
        if RESIZE_OUTPUT and original_image_size:
            original_width, original_height = original_image_size
            if original_width > 0 and original_height > 0:
                # 根据文本宽度计算目标高度以保持宽高比
                original_aspect = original_height / float(original_width)
                target_height = int(img_width * original_aspect)
                target_height = max(1, target_height) # 确保高度至少为 1
                try:
                    # 如果可用，使用 LANCZOS 进行高质量缩放
                    output_image = output_image.resize((img_width, target_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    # 对旧版 Pillow 的后备方案
                    try:
                        output_image = output_image.resize((img_width, target_height), Image.LANCZOS)
                    except AttributeError:
                        print("警告：正在使用较旧的 Pillow 缩放滤镜 (BILINEAR)。")
                        output_image = output_image.resize((img_width, target_height), Image.BILINEAR)
            else:
                print("警告：无法调整大小，原始图像尺寸无效。")
        elif RESIZE_OUTPUT:
             print(f"警告：请求调整大小但未提供原始图像尺寸。")

        # --- 保存最终图像 ---
        output_image.save(output_path)
        return True # 表示成功

    except Exception as e:
        print(f"在路径 '{output_path}' 为主题 '{theme_name}' 创建或保存 PNG 时出错: {e}")
        traceback.print_exc()
        return False # 表示失败

# --- 核心处理函数 ---
def process_image_to_ascii_themes(image_path, font, themes_config, output_dir):
    """
    处理单个图像文件：加载它，为多个主题生成 ASCII 艺术，
    并将它们作为 PNG 保存在指定的输出目录中。
    """
    print(f"\n正在处理图像: {image_path}")
    results = {'success': 0, 'failed': 0}
    original_img = None
    original_dimensions = (0, 0)

    # --- 加载图像 ---
    try:
        with Image.open(image_path) as img_opened:
            original_img = img_opened.convert('RGB') # 确保是 RGB 格式
            original_dimensions = original_img.size
        if not original_img:
             raise ValueError("无法加载或转换图像。")
        print(f"  图像已加载 ({original_dimensions[0]}x{original_dimensions[1]})") # 保留简单的加载完成消息
    except FileNotFoundError:
        print(f"  错误：在 '{image_path}' 未找到图像文件。跳过。")
        results['failed'] = len(THEMES_TO_GENERATE) # 将此图像所有潜在主题计为失败
        return results
    except Exception as e:
        print(f"  打开或转换图像文件 '{os.path.basename(image_path)}' 时出错: {e}")
        traceback.print_exc()
        results['failed'] = len(THEMES_TO_GENERATE) # 将所有潜在主题计为失败
        return results

    # --- 确保输出目录存在 ---
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"  错误：无法创建输出目录 '{output_dir}': {e}。跳过图像。")
        results['failed'] = len(THEMES_TO_GENERATE)
        return results

    # --- 处理每个主题 ---
    base_name = os.path.basename(image_path)
    file_name_no_ext, _ = os.path.splitext(base_name)

    for theme_name in THEMES_TO_GENERATE:
        theme_start_time = time.perf_counter() # 保留主题计时
        print(f"  - 正在处理主题: '{theme_name}'...")

        theme_details = themes_config.get(theme_name)
        if not theme_details:
            print(f"    警告：在配置中未找到主题 '{theme_name}'。跳过。")
            results['failed'] += 1
            continue

        bg_color = theme_details["background"]
        fg_color = theme_details.get("foreground") # 可以是 None
        is_original = theme_name in ["original", "original_light_bg"]

        # 1. 转换为 ASCII（现在使用 NumPy 优化版本）
        ascii_conv_start = time.perf_counter() # 保留转换计时
        ascii_data, color_map = image_to_ascii(
            color_image=original_img,
            width_chars=OUTPUT_WIDTH_CHARS,
            active_theme_name=theme_name,
            needs_color_map=is_original
        )
        ascii_conv_end = time.perf_counter()

        if not ascii_data:
            print(f"    错误：为主题 '{theme_name}' 生成 ASCII 数据失败。跳过 PNG 创建。")
            results['failed'] += 1
            continue
        # ... （其余检查保持不变） ...
        if is_original and not color_map:
            print(f"    错误：为原始主题 '{theme_name}' 生成所需的颜色映射失败。跳过 PNG 创建。")
            results['failed'] += 1
            continue
        if not is_original and fg_color is None:
             print(f"    错误：主题 '{theme_name}' 需要 'foreground' 颜色。跳过 PNG 创建。")
             results['failed'] += 1
             continue

        print(f"      ASCII 转换耗时: {ascii_conv_end - ascii_conv_start:.4f}s") # 保留此打印语句

        # 2. 创建 PNG
        resize_suffix = "_resized" if RESIZE_OUTPUT else ""
        output_filename = f"{file_name_no_ext}_ascii_{theme_name}{resize_suffix}.png"
        output_filepath = os.path.join(output_dir, output_filename)

        png_create_start = time.perf_counter() # 保留 PNG 创建计时
        png_success = create_ascii_png(
            ascii_lines=ascii_data,
            color_map_image=color_map,
            theme_name=theme_name,
            output_path=output_filepath,
            font=font, # 传递加载的字体对象
            background_color=bg_color,
            foreground_color=fg_color,
            original_image_size=original_dimensions
        )
        png_create_end = time.perf_counter()

        if png_success:
            results['success'] += 1
            print(f"      PNG 创建耗时: {png_create_end - png_create_start:.4f}s") # 保留此打印语句
            print(f"      输出已保存: {output_filename}")
        else:
            results['failed'] += 1
            print(f"      错误：为主题 '{theme_name}' 创建 PNG 失败。")

        theme_end_time = time.perf_counter() # 保留主题计时结束点
        print(f"    主题 '{theme_name}' 处理耗时: {theme_end_time - theme_start_time:.4f}s") # 保留此打印语句

    return results

def process_directory(dir_path, font, themes_config):
    """
    扫描目录，使用 process_image_to_ascii_themes 处理所有支持的图像，
    并汇总结果。
    """
    print(f"\n正在处理目录: {dir_path}")
    overall_results = {'processed_files': 0, 'total_success': 0, 'total_failed': 0, 'output_location': None}

    dir_name = os.path.basename(os.path.abspath(dir_path))
    parent_dir = os.path.dirname(os.path.abspath(dir_path))
    main_output_dir = os.path.join(parent_dir, f"{dir_name}_ascii_art")
    overall_results['output_location'] = main_output_dir

    try:
        os.makedirs(main_output_dir, exist_ok=True)
        print(f"输出将保存在: {main_output_dir}")
    except OSError as e:
        print(f"错误：无法创建主输出目录 '{main_output_dir}': {e}。中止。")
        overall_results['total_failed'] = 1 # 表示目录级别失败
        return overall_results

    print("正在扫描支持的图像文件...")
    found_files = []
    try:
        for entry in os.scandir(dir_path):
            if entry.is_file() and entry.name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                found_files.append(entry.path)
    except FileNotFoundError:
        print(f"错误：扫描期间未找到输入目录 '{dir_path}'。")
        overall_results['total_failed'] = 1
        return overall_results
    except Exception as e:
        print(f"扫描目录 '{dir_path}' 时出错: {e}")
        overall_results['total_failed'] = 1
        return overall_results

    if not found_files:
        print("在目录中未找到支持的图像文件。")
        return overall_results

    print(f"找到 {len(found_files)} 个潜在的图像文件。开始处理...")
    overall_results['processed_files'] = len(found_files)

    for image_file_path in found_files:
        # 处理每个图像，将结果保存到单个 main_output_dir 中
        image_results = process_image_to_ascii_themes(
            image_path=image_file_path,
            font=font, # 传递加载的字体对象
            themes_config=themes_config,
            output_dir=main_output_dir # 所有输出都到这里
        )
        overall_results['total_success'] += image_results['success']
        overall_results['total_failed'] += image_results['failed']

    return overall_results


def get_input_path():
    """获取用户的输入路径（文件或目录）。"""
    input_path = ""
    while not input_path:
        try:
            input_path = input("输入图像文件或目录的路径: ").strip().strip("'\"")
            if not input_path:
                print("输入不能为空。")
            elif not os.path.exists(input_path):
                 print(f"错误：路径不存在: '{input_path}'")
                 input_path = "" # 再次询问
        except KeyboardInterrupt:
            print("\n操作被用户取消。")
            return None
    return input_path

# --- 修改后的函数签名 ---
def print_summary(results, duration):
    """打印最终的处理摘要。"""
    print("\n===================================")
    print("        处理摘要")
    print("===================================")

    input_type = results.get('input_type', 'unknown')
    output_location = results.get('output_location')

    if input_type == 'invalid':
        print("状态：失败（无效的输入路径）")
    elif input_type == 'font_error':
        print("状态：失败（无法加载所需字体）")
    elif input_type == 'file':
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：单个文件")
        print(f"已处理的主题数：{success_count + fail_count}")
        print(f"  - 成功的 PNG 数量：{success_count}")
        print(f"  - 失败/跳过的主题数量：{fail_count}")
        if success_count > 0 and output_location:
            print(f"输出位置：{output_location}")
    elif input_type == 'directory':
        processed_files = results.get('processed_files', 0)
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：目录")
        print(f"找到/尝试处理的图像文件数：{processed_files}")
        print(f"成功生成的 PNG 总数：{success_count}")
        print(f"失败/跳过的主题尝试总数：{fail_count}")
        if output_location:
             print(f"输出位置：{output_location}")

    print("-----------------------------------")
    print("执行时间:")
    print(f"  - 总处理时间：{duration:.4f} 秒") # 保留总处理时间
    print("===================================")



def main():
    """主执行函数。"""
    print("--- ASCII 艺术生成器 ---")

    # --- 直接从脚本目录加载字体 ---
    print("正在加载字体...")
    try:
        # 获取脚本所在的目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建字体文件的完整路径
        font_path = os.path.join(script_dir, FONT_FILENAME)
        print(f"尝试从以下路径加载字体: {font_path}")
        # 尝试加载指定的字体文件
        font = ImageFont.truetype(font_path, FONT_SIZE)
        print("字体加载成功。")
    except IOError:
        print(f"致命错误：无法从脚本目录加载字体文件 '{FONT_FILENAME}'。")
        print(f"请确保 '{FONT_FILENAME}' 与脚本在同一目录中 ({script_dir})。")
        results = {'input_type': 'font_error'}
        print_summary(results, 0) # 传递 0 作为持续时间，因为它提前失败了
        sys.exit(1)
    except Exception as e:
        print(f"致命错误：加载字体 '{font_path}' 时发生意外错误: {e}")
        results = {'input_type': 'font_error'}
        print_summary(results, 0) # 传递 0 作为持续时间，因为它提前失败了
        sys.exit(1)
    # --- 字体加载部分结束 ---

    # --- 获取输入路径 ---
    input_path = get_input_path()
    if input_path is None:
        sys.exit(0) # 用户取消

    # --- 开始处理计时器 ---
    processing_start_time = time.perf_counter() # 保留总处理计时器
    results = {} # 初始化结果字典

    # --- 判断路径类型并处理 ---
    if os.path.isfile(input_path):
        results['input_type'] = 'file'
        # 定义相对于输入文件位置的输出目录
        file_dir = os.path.dirname(os.path.abspath(input_path))
        file_name_no_ext, _ = os.path.splitext(os.path.basename(input_path))
        output_dir = os.path.join(file_dir, f"{file_name_no_ext}_ascii_art")
        results['output_location'] = output_dir
        # 处理单个图像
        # 传递加载的字体对象
        img_results = process_image_to_ascii_themes(input_path, font, COLOR_THEMES, output_dir)
        results['total_success'] = img_results['success']
        results['total_failed'] = img_results['failed']

    elif os.path.isdir(input_path):
        results['input_type'] = 'directory'
        # 处理目录
        # 传递加载的字体对象
        dir_results = process_directory(input_path, font, COLOR_THEMES)
        results.update(dir_results) # 合并来自 process_directory 的结果

    else:
        # 应该在 get_input_path 中被捕获，但作为后备
        print(f"错误：输入路径 '{input_path}' 不是有效的文件或目录。")
        results['input_type'] = 'invalid'

    # --- 停止处理计时器 ---
    processing_end_time = time.perf_counter() # 保留总处理计时器结束点
    total_processing_duration = processing_end_time - processing_start_time # 保留持续时间计算

    # --- 打印摘要 ---
    print_summary(results, total_processing_duration)


if __name__ == "__main__":
    main()
