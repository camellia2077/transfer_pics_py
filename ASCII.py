# -*- coding: utf-8 -*-
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import math
import traceback
import time
import numpy as np
import configparser # 导入配置解析器

# --- 默认配置 (如果 config.txt 不存在或无效则使用) ---
DEFAULT_OUTPUT_WIDTH_CHARS = 2048 # 默认 ASCII 表示宽度
DEFAULT_FONT_FILENAME = "Consolas.ttf" # 默认字体文件名
DEFAULT_FONT_SIZE = 12 # 默认字体大小

# --- 其他常量 ---
ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
RESIZE_OUTPUT = True # 设置为 True 以将输出 PNG 调整为原始宽高比
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

# --- 颜色主题配置 ---
COLOR_THEMES = {
    "dark":           {"background": "black", "foreground": "white"},#黑底白字
    "green_term":     {"background": "black", "foreground": "lime"},#黑底绿字
    "light":          {"background": "#f0f0f0", "foreground": "black"}, #灰底黑字
    "amber_term":     {"background": "#1c1c1c", "foreground": "#FFBF00"},#黑底黄字
    "original":       {"background": "black", "foreground": None}, #黑底彩色
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

# --- 配置加载函数 ---
def load_config(config_filepath):
    """
    从指定的路径加载配置。
    如果文件不存在、键缺失或值无效，则使用默认值。
    返回包含配置值的字典。
    """
    config_values = {
        "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
        "font_filename": DEFAULT_FONT_FILENAME,
        "font_size": DEFAULT_FONT_SIZE,
    }
    print(f"尝试从以下路径加载配置文件: {config_filepath}")
    if not os.path.exists(config_filepath):
        print("未找到 config.txt。将使用默认设置。")
        print(f"  默认 OUTPUT_WIDTH_CHARS = {DEFAULT_OUTPUT_WIDTH_CHARS}")
        print(f"  默认 FONT_FILENAME = {DEFAULT_FONT_FILENAME}")
        print(f"  默认 FONT_SIZE = {DEFAULT_FONT_SIZE}")
        return config_values

    parser = configparser.ConfigParser(allow_no_value=True) # 允许没有值的键（虽然我们这里不用）
    try:
        # 使用 utf-8 读取文件，兼容中文注释等
        parser.read(config_filepath, encoding='utf-8')
        print("已找到 config.txt。正在加载设置...")

        if 'Settings' in parser:
            settings_section = parser['Settings']

            # 加载 OUTPUT_WIDTH_CHARS
            try:
                # 使用 getint 读取整数，如果失败或不存在，使用 fallback
                loaded_width = settings_section.getint('OUTPUT_WIDTH_CHARS', fallback=DEFAULT_OUTPUT_WIDTH_CHARS)
                if loaded_width > 0: # 确保宽度是正数
                    config_values["output_width_chars"] = loaded_width
                    print(f"  已加载 OUTPUT_WIDTH_CHARS = {config_values['output_width_chars']}")
                else:
                    print(f"  警告: config.txt 中的 OUTPUT_WIDTH_CHARS 值 ({loaded_width}) 无效 (必须 > 0)。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                    config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS
            except ValueError:
                print(f"  警告: config.txt 中的 OUTPUT_WIDTH_CHARS 值不是有效的整数。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS
            except KeyError:
                 print(f"  信息: config.txt 中未找到 OUTPUT_WIDTH_CHARS。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                 config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS


            # 加载 FONT_FILENAME (字符串)
            try:
                loaded_filename = settings_section.get('FONT_FILENAME', fallback=DEFAULT_FONT_FILENAME).strip()
                if loaded_filename: # 确保文件名不是空的
                     config_values["font_filename"] = loaded_filename
                     print(f"  已加载 FONT_FILENAME = {config_values['font_filename']}")
                else:
                    print(f"  警告: config.txt 中的 FONT_FILENAME 为空。使用默认值 {DEFAULT_FONT_FILENAME}。")
                    config_values["font_filename"] = DEFAULT_FONT_FILENAME
            except KeyError:
                print(f"  信息: config.txt 中未找到 FONT_FILENAME。使用默认值 {DEFAULT_FONT_FILENAME}。")
                config_values["font_filename"] = DEFAULT_FONT_FILENAME


            # 加载 FONT_SIZE
            try:
                loaded_size = settings_section.getint('FONT_SIZE', fallback=DEFAULT_FONT_SIZE)
                if loaded_size > 0: # 确保字体大小是正数
                    config_values["font_size"] = loaded_size
                    print(f"  已加载 FONT_SIZE = {config_values['font_size']}")
                else:
                    print(f"  警告: config.txt 中的 FONT_SIZE 值 ({loaded_size}) 无效 (必须 > 0)。使用默认值 {DEFAULT_FONT_SIZE}。")
                    config_values["font_size"] = DEFAULT_FONT_SIZE
            except ValueError:
                print(f"  警告: config.txt 中的 FONT_SIZE 值不是有效的整数。使用默认值 {DEFAULT_FONT_SIZE}。")
                config_values["font_size"] = DEFAULT_FONT_SIZE
            except KeyError:
                print(f"  信息: config.txt 中未找到 FONT_SIZE。使用默认值 {DEFAULT_FONT_SIZE}。")
                config_values["font_size"] = DEFAULT_FONT_SIZE

        else:
            print("警告: 在 config.txt 中未找到 [Settings] 部分。将使用所有默认设置。")
            # 确保返回的是默认值
            config_values = {
                "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
                "font_filename": DEFAULT_FONT_FILENAME,
                "font_size": DEFAULT_FONT_SIZE,
            }

    except configparser.Error as e:
        print(f"错误: 读取 config.txt 时出错: {e}。将使用所有默认设置。")
        config_values = {
            "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
            "font_filename": DEFAULT_FONT_FILENAME,
            "font_size": DEFAULT_FONT_SIZE,
        }
    except Exception as e:
         print(f"错误: 处理 config.txt 时发生意外错误: {e}。将使用所有默认设置。")
         config_values = {
             "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
             "font_filename": DEFAULT_FONT_FILENAME,
             "font_size": DEFAULT_FONT_SIZE,
         }

    print("配置加载完成。\n")
    return config_values


# --- 图像处理函数 ---
# image_to_ascii 函数已经接受 width_chars 参数，无需修改其内部逻辑
# 只需确保调用时传递正确的值
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
        # 确保 width_chars 至少为 1
        width_chars = max(1, int(width_chars))
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
        is_light_bg = theme_bg in ["white", "#ffffff", "lightgrey", "#d3d3d3", "#fff", "ivory", "#f0f0f0"]

        # --- 字符索引的向量化计算 ---
        if is_light_bg:
            char_indices = np.floor((255.0 - gray_pixels_np) * (num_chars / 256.0)).astype(int)
        else:
            char_indices = np.floor(gray_pixels_np * (num_chars / 256.0)).astype(int)

        char_indices = np.clip(char_indices, 0, num_chars - 1)
        # --- 向量化计算结束 ---

        ascii_grid = ascii_map[char_indices]
        ascii_str_list = ["".join(row) for row in ascii_grid]

        return ascii_str_list, color_map_image

    except Exception as e:
        print(f"在主题 '{active_theme_name}' 的 ASCII 转换（NumPy）过程中出错: {e}")
        traceback.print_exc()
        return None, None

# create_ascii_png 函数接收已加载的 font 对象，无需修改
def create_ascii_png(ascii_lines,
                     color_map_image,
                     theme_name,
                     output_path,
                     font, # 接收已加载字体
                     background_color,
                     foreground_color,
                     original_image_size=None):
    """
    根据 ASCII 字符串行创建 PNG 图像。
    """
    if not ascii_lines or not ascii_lines[0]:
        print("错误：没有 ASCII 数据或空行来创建 PNG。")
        return False

    is_original_color_theme = theme_name in ["original", "original_light_bg"]
    font_size_val = 10 # 后备字体大小

    try:
        # 尝试获取字体大小，用于后备计算
        if hasattr(font, 'size'):
            font_size_val = font.size
        else: # Pillow < 8.0.0 可能没有 .size
             try:
                 # 尝试从字体路径中提取大小（不推荐，但作为最后的手段）
                 if font.path and font.path.endswith('.ttf'):
                     # 简单的基于文件名的猜测（非常不可靠）
                     parts = os.path.basename(font.path).split('-')
                     for part in parts:
                         if part.isdigit():
                             font_size_val = int(part)
                             break
             except:
                 pass # 忽略错误，使用默认后备值

        # --- 精确确定文本渲染尺寸 ---
        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        try:
            bbox = draw.textbbox((0, 0), '|M_g(`', font=font)
            line_height = bbox[3] - bbox[1]
            bbox_width = draw.textbbox((0, 0), ascii_lines[0], font=font)
            text_width = bbox_width[2] - bbox_width[0]
        except AttributeError:
            print("警告：正在使用较旧的 Pillow 文本测量方法（textsize）。尺寸可能不太准确。")
            try:
                (_, h) = draw.textsize('|M_g(`', font=font)
                line_height = h
                (w, _) = draw.textsize(ascii_lines[0], font=font)
                text_width = w
            except AttributeError:
                (_, h) = draw.textsize('M', font=font)
                line_height = int(h * 1.2)
                (w, _) = draw.textsize('M' * len(ascii_lines[0]), font=font)
                text_width = w

        line_spacing = line_height + 2
        if line_spacing <= 0: line_spacing = font_size_val + 2
        if text_width <= 0: text_width = font_size_val * len(ascii_lines[0])

        img_width = max(1, text_width)
        img_height = max(1, line_spacing * len(ascii_lines))

        # --- 创建图像并绘制文本 ---
        output_image = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(output_image)
        y_text = 0

        if is_original_color_theme and color_map_image:
            color_pixels = color_map_image.load()
            map_width, map_height = color_map_image.size
            avg_char_width = text_width / len(ascii_lines[0]) if ascii_lines[0] else font_size_val

            for y, line in enumerate(ascii_lines):
                if y >= map_height: # 检查 Y 坐标
                    print(f"警告：行索引 {y} 超出颜色映射高度 {map_height}。")
                    continue
                x_pos = 0
                for x, char in enumerate(line):
                    if x >= map_width: # 检查 X 坐标
                        print(f"警告：字符索引 {x} 超出颜色映射宽度 {map_width} (行 {y})。")
                        continue # 跳过这个字符的绘制
                    try:
                        char_color = color_pixels[x, y]
                        if theme_name == "original_light_bg":
                            darken_factor = 0.75
                            r, g, b = char_color
                            new_r = max(0, min(255, int(r * darken_factor)))
                            new_g = max(0, min(255, int(g * darken_factor)))
                            new_b = max(0, min(255, int(b * darken_factor)))
                            char_color = (new_r, new_g, new_b)

                        draw.text((math.floor(x_pos), y_text), char, font=font, fill=char_color)
                        x_pos += avg_char_width
                    # IndexError 不应再发生，因为我们上面检查了 x, y
                    except Exception as char_err:
                        print(f"警告：在文本位置 ({x_pos:.0f},{y_text}) 绘制字符 '{char}' 时出错: {char_err}")
                        x_pos += avg_char_width
                y_text += line_spacing
        else:
            effective_fg_color = foreground_color if foreground_color is not None else "white"
            if foreground_color is None and not is_original_color_theme:
                 print(f"错误：非原始颜色主题 '{theme_name}' 缺少前景色。使用白色。")

            for line in ascii_lines:
                draw.text((0, y_text), line, font=font, fill=effective_fg_color)
                y_text += line_spacing

        # --- 可选的尺寸调整 ---
        if RESIZE_OUTPUT and original_image_size:
            original_width, original_height = original_image_size
            if original_width > 0 and original_height > 0:
                original_aspect = original_height / float(original_width)
                target_height = max(1, int(img_width * original_aspect))
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.LANCZOS # Pillow < 9.1.0
                try:
                     output_image = output_image.resize((img_width, target_height), resample_filter)
                except Exception as resize_err:
                     print(f"警告: 调整大小失败: {resize_err}. 使用原始渲染大小。")
            else:
                print("警告：无法调整大小，原始图像尺寸无效。")
        elif RESIZE_OUTPUT:
            print("警告：请求调整大小但未提供原始图像尺寸。")

        # --- 保存最终图像 ---
        output_image.save(output_path)
        return True

    except Exception as e:
        print(f"在路径 '{output_path}' 为主题 '{theme_name}' 创建或保存 PNG 时出错: {e}")
        traceback.print_exc()
        return False


# --- 核心处理函数 ---
# 修改 process_image_to_ascii_themes 签名以接受 output_width_chars
def process_image_to_ascii_themes(image_path, font, themes_config, output_dir, output_width_chars):
    """
    处理单个图像文件，使用指定的 output_width_chars。
    """
    print(f"\n正在处理图像: {image_path}")
    results = {'success': 0, 'failed': 0}
    original_img = None
    original_dimensions = (0, 0)

    # --- 加载图像 ---
    try:
        with Image.open(image_path) as img_opened:
            original_img = img_opened.convert('RGB')
            original_dimensions = original_img.size
        if not original_img:
             raise ValueError("无法加载或转换图像。")
        print(f"  图像已加载 ({original_dimensions[0]}x{original_dimensions[1]})")
    except FileNotFoundError:
        print(f"  错误：在 '{image_path}' 未找到图像文件。跳过。")
        results['failed'] = len(THEMES_TO_GENERATE)
        return results
    except Exception as e:
        print(f"  打开或转换图像文件 '{os.path.basename(image_path)}' 时出错: {e}")
        traceback.print_exc()
        results['failed'] = len(THEMES_TO_GENERATE)
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
        theme_start_time = time.perf_counter()
        print(f"  - 正在处理主题: '{theme_name}'...")

        theme_details = themes_config.get(theme_name)
        if not theme_details:
            print(f"    警告：在配置中未找到主题 '{theme_name}'。跳过。")
            results['failed'] += 1
            continue

        bg_color = theme_details["background"]
        fg_color = theme_details.get("foreground")
        is_original = theme_name in ["original", "original_light_bg"]

        # 1. 转换为 ASCII (传递从配置加载的 output_width_chars)
        ascii_conv_start = time.perf_counter()
        ascii_data, color_map = image_to_ascii(
            color_image=original_img,
            width_chars=output_width_chars, # <-- 使用传入的参数
            active_theme_name=theme_name,
            needs_color_map=is_original
        )
        ascii_conv_end = time.perf_counter()

        if not ascii_data:
            print(f"    错误：为主题 '{theme_name}' 生成 ASCII 数据失败。跳过 PNG 创建。")
            results['failed'] += 1
            continue
        if is_original and not color_map:
            print(f"    错误：为原始主题 '{theme_name}' 生成所需的颜色映射失败。跳过 PNG 创建。")
            results['failed'] += 1
            continue
        # 注意：非原始主题的 foreground 颜色检查已移至 create_ascii_png 内

        print(f"      ASCII 转换耗时: {ascii_conv_end - ascii_conv_start:.4f}s")

        # 2. 创建 PNG
        resize_suffix = "_resized" if RESIZE_OUTPUT else ""
        output_filename = f"{file_name_no_ext}_ascii_{theme_name}{resize_suffix}.png"
        output_filepath = os.path.join(output_dir, output_filename)

        png_create_start = time.perf_counter()
        png_success = create_ascii_png(
            ascii_lines=ascii_data,
            color_map_image=color_map,
            theme_name=theme_name,
            output_path=output_filepath,
            font=font, # 传递加载的字体对象
            background_color=bg_color,
            foreground_color=fg_color, # 可以是 None
            original_image_size=original_dimensions
        )
        png_create_end = time.perf_counter()

        if png_success:
            results['success'] += 1
            print(f"      PNG 创建耗时: {png_create_end - png_create_start:.4f}s")
            print(f"      输出已保存: {output_filename}")
        else:
            results['failed'] += 1
            # 错误信息已在 create_ascii_png 中打印
            print(f"      错误：为主题 '{theme_name}' 创建 PNG 失败。")

        theme_end_time = time.perf_counter()
        print(f"    主题 '{theme_name}' 处理耗时: {theme_end_time - theme_start_time:.4f}s")

    return results

# 修改 process_directory 签名以接受 output_width_chars
def process_directory(dir_path, font, themes_config, output_width_chars):
    """
    扫描目录，处理所有支持的图像，并汇总结果。
    """
    print(f"\n正在处理目录: {dir_path}")
    overall_results = {'processed_files': 0, 'total_success': 0, 'total_failed': 0, 'output_location': None}

    # 创建输出目录 (基于输入目录名)
    dir_name = os.path.basename(os.path.normpath(dir_path)) # 处理末尾斜杠
    parent_dir = os.path.dirname(os.path.abspath(dir_path))
    main_output_dir = os.path.join(parent_dir, f"{dir_name}_ascii_art")
    overall_results['output_location'] = main_output_dir

    try:
        os.makedirs(main_output_dir, exist_ok=True)
        print(f"输出将保存在: {main_output_dir}")
    except OSError as e:
        print(f"错误：无法创建主输出目录 '{main_output_dir}': {e}。中止。")
        overall_results['total_failed'] = 1
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
        # 处理每个图像 (传递 output_width_chars)
        image_results = process_image_to_ascii_themes(
            image_path=image_file_path,
            font=font,
            themes_config=themes_config,
            output_dir=main_output_dir,
            output_width_chars=output_width_chars # <-- 传递参数
        )
        overall_results['total_success'] += image_results['success']
        overall_results['total_failed'] += image_results['failed']

    return overall_results

# --- 输入和摘要函数 (无需修改) ---
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
        except EOFError: # 处理管道输入结束的情况
             print("\n接收到输入结束信号。")
             return None
    return input_path

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
        font_name = results.get('font_name', '未知')
        font_path_tried = results.get('font_path_tried', '未知')
        print(f"  尝试加载字体: '{font_name}'")
        print(f"  尝试路径: {font_path_tried}")
    elif input_type == 'file':
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：单个文件")
        print(f"已处理的主题数：{success_count + fail_count}")
        print(f"  - 成功的 PNG 数量：{success_count}")
        print(f"  - 失败/跳过的主题数量：{fail_count}")
        if (success_count > 0 or fail_count > 0) and output_location:
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
    else:
        print(f"状态：未知 ({input_type})")

    print("-----------------------------------")
    print("执行时间:")
    print(f"  - 总处理时间：{duration:.4f} 秒")
    print("===================================")

# --- 主执行函数 ---
def main():
    """主执行函数。"""
    print("--- ASCII 艺术生成器 ---")
    results = {} # 初始化结果字典
    start_time = time.perf_counter() # 总计时开始

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filepath = os.path.join(script_dir, "config.txt")

        # --- 加载配置 ---
        config = load_config(config_filepath)
        output_width_chars = config["output_width_chars"]
        font_filename = config["font_filename"]
        font_size = config["font_size"]

        # --- 加载字体 ---
        print("正在加载字体...")
        font = None
        font_path = os.path.join(script_dir, font_filename)
        font_load_error = False
        try:
            print(f"尝试从以下路径加载字体: {font_path} (大小: {font_size})")
            if not os.path.exists(font_path):
                # 如果本地路径不存在，尝试让Pillow查找系统字体
                print(f"警告: 本地路径未找到 '{font_path}'。尝试系统字体 '{font_filename}'...")
                try:
                    font = ImageFont.truetype(font_filename, font_size)
                    print(f"成功加载系统字体 '{font_filename}'。")
                except IOError:
                     print(f"错误: 无法在本地或系统中找到/加载字体 '{font_filename}'。")
                     raise # 重新引发IOError以被外部捕获
            else:
                # 本地路径存在，直接加载
                font = ImageFont.truetype(font_path, font_size)
                print("字体加载成功。")

        except IOError as e:
            print(f"致命错误：无法加载字体文件 '{font_filename}'。")
            print(f"错误详情: {e}")
            print(f"请确保字体文件存在于脚本目录 ({script_dir}) 或系统字体路径中，并且名称 '{font_filename}' 正确。")
            results = {'input_type': 'font_error', 'font_name': font_filename, 'font_path_tried': font_path}
            font_load_error = True # 设置标志位
        except Exception as e:
            print(f"致命错误：加载字体时发生意外错误: {e}")
            results = {'input_type': 'font_error', 'font_name': font_filename, 'font_path_tried': font_path}
            font_load_error = True # 设置标志位

        if font_load_error:
             duration = time.perf_counter() - start_time
             print_summary(results, duration)
             sys.exit(1)
        # --- 字体加载部分结束 ---

        # --- 获取输入路径 ---
        input_path = get_input_path()
        if input_path is None:
            print("未提供输入路径或操作已取消。退出。")
            sys.exit(0) # 用户取消或未输入

        # --- 开始处理计时器 (主要处理部分) ---
        processing_start_time = time.perf_counter()

        # --- 判断路径类型并处理 ---
        if os.path.isfile(input_path):
            results['input_type'] = 'file'
            file_dir = os.path.dirname(os.path.abspath(input_path))
            file_name_no_ext, _ = os.path.splitext(os.path.basename(input_path))
            output_dir = os.path.join(file_dir, f"{file_name_no_ext}_ascii_art")
            results['output_location'] = output_dir
            # 处理单个图像 (传递加载的字体和配置宽度)
            img_results = process_image_to_ascii_themes(
                input_path,
                font,
                COLOR_THEMES,
                output_dir,
                output_width_chars # 传递配置宽度
            )
            results['total_success'] = img_results['success']
            results['total_failed'] = img_results['failed']

        elif os.path.isdir(input_path):
            results['input_type'] = 'directory'
            # 处理目录 (传递加载的字体和配置宽度)
            dir_results = process_directory(
                input_path,
                font,
                COLOR_THEMES,
                output_width_chars # 传递配置宽度
             )
            results.update(dir_results) # 合并结果

        else:
            # 这个情况理论上 get_input_path() 应该已经处理了
            print(f"错误：输入路径 '{input_path}' 不是有效的文件或目录。")
            results['input_type'] = 'invalid'

        # --- 停止处理计时器 ---
        processing_end_time = time.perf_counter()
        total_processing_duration = processing_end_time - processing_start_time

        # --- 打印摘要 ---
        print_summary(results, total_processing_duration)

    except Exception as e:
         print("\n--- 发生未处理的异常 ---")
         print(f"错误类型: {type(e).__name__}")
         print(f"错误信息: {e}")
         print("详细追溯信息:")
         traceback.print_exc()
         print("--------------------------")
         results['input_type'] = 'runtime_error' # 或其他表示意外错误的类型
         duration = time.perf_counter() - start_time
         print_summary(results, duration)
         sys.exit(1)


if __name__ == "__main__":
    # 确保在打包成可执行文件时也能找到资源（如果需要）
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包的应用
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path) # 将当前工作目录更改为可执行文件所在目录
        print(f"检测到打包环境，当前目录已设置为: {application_path}")
    main()
