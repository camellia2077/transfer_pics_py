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
DEFAULT_OUTPUT_WIDTH_CHARS = 128 # 默认 ASCII 表示宽度 (降低默认值以便测试)
DEFAULT_FONT_FILENAME = "Consolas.ttf" # 默认字体文件名 (确保此文件存在)
# DEFAULT_FONT_FILENAME = "cour.ttf" # Courier New - 备选，更可能存在于系统
DEFAULT_FONT_SIZE = 15 # 默认字体大小

# --- 其他常量 ---
# 调整字符集，从暗到亮
#ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
ASCII_CHARS = "@%#*+=-:. "

RESIZE_OUTPUT = True # 设置为 True 以将输出 PNG 调整为原始宽高比
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

# --- 颜色主题配置 ---
COLOR_THEMES = {
    "dark":              {"background": "black", "foreground": "white"},#黑底白字
    "green_term":        {"background": "black", "foreground": "lime"},#黑底绿字
    "light":             {"background": "#f0f0f0", "foreground": "black"}, #灰底黑字
    "amber_term":        {"background": "#1c1c1c", "foreground": "#FFBF00"},#黑底黄字
    "original_dark_bg":  {"background": "black", "foreground": None}, #黑底彩色 (使用原色)
    "original_light_bg": {"background": "#f0f0f0", "foreground": None}, # 灰底彩色 (使用原色，可能微调)
}

# --- 选择要生成的主题 ---
# 确保至少有一个 'original' 主题被选中以测试新逻辑
THEMES_TO_GENERATE = [
    "dark",
    # "green_term",
    "original_dark_bg",
    "original_light_bg",
    "light",
    # "amber_term",
]

# --- 配置加载函数 (无变化) ---
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
        print("未找到 config.ini。将使用默认设置。")
        print(f"  默认 OUTPUT_WIDTH_CHARS = {DEFAULT_OUTPUT_WIDTH_CHARS}")
        print(f"  默认 FONT_FILENAME = {DEFAULT_FONT_FILENAME}")
        print(f"  默认 FONT_SIZE = {DEFAULT_FONT_SIZE}")
        return config_values

    parser = configparser.ConfigParser(allow_no_value=True)
    try:
        parser.read(config_filepath, encoding='utf-8')
        print("已找到 config.ini。正在加载设置...")

        if 'Settings' in parser:
            settings_section = parser['Settings']

            # 加载 OUTPUT_WIDTH_CHARS
            try:
                loaded_width = settings_section.getint('OUTPUT_WIDTH_CHARS', fallback=DEFAULT_OUTPUT_WIDTH_CHARS)
                if loaded_width > 0:
                    config_values["output_width_chars"] = loaded_width
                    print(f"  已加载 OUTPUT_WIDTH_CHARS = {config_values['output_width_chars']}")
                else:
                    print(f"  警告: config.ini 中的 OUTPUT_WIDTH_CHARS 值 ({loaded_width}) 无效 (必须 > 0)。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                    config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS
            except ValueError:
                print(f"  警告: config.ini 中的 OUTPUT_WIDTH_CHARS 值不是有效的整数。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS
            except KeyError:
                print(f"  信息: config.ini 中未找到 OUTPUT_WIDTH_CHARS。使用默认值 {DEFAULT_OUTPUT_WIDTH_CHARS}。")
                config_values["output_width_chars"] = DEFAULT_OUTPUT_WIDTH_CHARS

            # 加载 FONT_FILENAME (字符串)
            try:
                loaded_filename = settings_section.get('FONT_FILENAME', fallback=DEFAULT_FONT_FILENAME).strip()
                if loaded_filename:
                    config_values["font_filename"] = loaded_filename
                    print(f"  已加载 FONT_FILENAME = {config_values['font_filename']}")
                else:
                    print(f"  警告: config.ini 中的 FONT_FILENAME 为空。使用默认值 {DEFAULT_FONT_FILENAME}。")
                    config_values["font_filename"] = DEFAULT_FONT_FILENAME
            except KeyError:
                print(f"  信息: config.ini 中未找到 FONT_FILENAME。使用默认值 {DEFAULT_FONT_FILENAME}。")
                config_values["font_filename"] = DEFAULT_FONT_FILENAME

            # 加载 FONT_SIZE
            try:
                loaded_size = settings_section.getint('FONT_SIZE', fallback=DEFAULT_FONT_SIZE)
                if loaded_size > 0:
                    config_values["font_size"] = loaded_size
                    print(f"  已加载 FONT_SIZE = {config_values['font_size']}")
                else:
                    print(f"  警告: config.ini 中的 FONT_SIZE 值 ({loaded_size}) 无效 (必须 > 0)。使用默认值 {DEFAULT_FONT_SIZE}。")
                    config_values["font_size"] = DEFAULT_FONT_SIZE
            except ValueError:
                print(f"  警告: config.ini 中的 FONT_SIZE 值不是有效的整数。使用默认值 {DEFAULT_FONT_SIZE}。")
                config_values["font_size"] = DEFAULT_FONT_SIZE
            except KeyError:
                print(f"  信息: config.ini 中未找到 FONT_SIZE。使用默认值 {DEFAULT_FONT_SIZE}。")
                config_values["font_size"] = DEFAULT_FONT_SIZE

        else:
            print("警告: 在 config.ini 中未找到 [Settings] 部分。将使用所有默认设置。")
            config_values = { # Re-assign defaults explicitly
                "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
                "font_filename": DEFAULT_FONT_FILENAME,
                "font_size": DEFAULT_FONT_SIZE,
            }

    except configparser.Error as e:
        print(f"错误: 读取 config.ini 时出错: {e}。将使用所有默认设置。")
        config_values = { # Re-assign defaults explicitly
            "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
            "font_filename": DEFAULT_FONT_FILENAME,
            "font_size": DEFAULT_FONT_SIZE,
        }
    except Exception as e:
        print(f"错误: 处理 config.ini 时发生意外错误: {e}。将使用所有默认设置。")
        config_values = { # Re-assign defaults explicitly
            "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
            "font_filename": DEFAULT_FONT_FILENAME,
            "font_size": DEFAULT_FONT_SIZE,
        }

    print("配置加载完成。\n")
    return config_values


# --- 图像处理函数 ---
# image_to_ascii 函数 (无变化)
def image_to_ascii(color_image, width_chars, active_theme_name):
    """
    将 PIL 彩色图像转换为包含字符和对应原图点采样颜色的数据结构。
    (函数体无变化)
    """
    try:
        # 确保输入是 RGB
        image_rgb = color_image if color_image.mode == 'RGB' else color_image.convert('RGB')
        original_width, original_height = image_rgb.size

        if original_width <= 0 or original_height <= 0:
            print("错误：原始图像尺寸无效。")
            return None

        # --- 准备用于字符选择的灰度图 ---
        image_gray = image_rgb.convert('L')
        aspect_ratio = original_height / float(original_width)

        # 调整字符宽高比
        char_aspect_ratio_correction = 0.5
        width_chars = max(1, int(width_chars))
        new_height_chars = int(width_chars * aspect_ratio * char_aspect_ratio_correction)
        new_height_chars = max(1, new_height_chars) # 确保至少有一行

        # 调整灰度图像的大小以获取亮度值网格
        resized_gray = image_gray.resize((width_chars, new_height_chars), Image.Resampling.NEAREST)
        gray_pixels_np = np.array(resized_gray, dtype=np.uint8)

        # --- 字符映射准备 ---
        num_chars = len(ASCII_CHARS)
        ascii_map = np.array(list(ASCII_CHARS))

        # 判断背景明暗
        theme_bg = COLOR_THEMES.get(active_theme_name, {}).get("background", "black").lower()
        is_light_bg = theme_bg in ["white", "#ffffff", "lightgrey", "#d3d3d3", "#fff", "ivory", "#f0f0f0"]

        # --- 字符索引计算 ---
        if is_light_bg:
            char_indices = np.floor((255.0 - gray_pixels_np) * (num_chars / 256.0)).astype(int)
        else:
            char_indices = np.floor(gray_pixels_np * (num_chars / 256.0)).astype(int)

        char_indices = np.clip(char_indices, 0, num_chars - 1)
        ascii_grid = ascii_map[char_indices]

        # --- 点采样颜色 ---
        xScale = float(original_width) / width_chars
        yScale = float(original_height) / new_height_chars
        ascii_char_color_data = []
        original_pixels = image_rgb.load() # 尝试优化像素访问

        for y_char in range(new_height_chars):
            row_data = []
            for x_char in range(width_chars):
                char = ascii_grid[y_char, x_char]
                x_orig = int(math.floor((x_char + 0.5) * xScale))
                y_orig = int(math.floor((y_char + 0.5) * yScale))
                x_orig = max(0, min(x_orig, original_width - 1))
                y_orig = max(0, min(y_orig, original_height - 1))

                try:
                    # 使用 .load() 访问器可能更快
                    sampled_color = original_pixels[x_orig, y_orig]
                    # sampled_color = image_rgb.getpixel((x_orig, y_orig)) # getpixel 更安全
                    if not isinstance(sampled_color, tuple) or len(sampled_color) < 3:
                         pixel_img = image_rgb.crop((x_orig, y_orig, x_orig + 1, y_orig + 1))
                         sampled_color = pixel_img.convert("RGB").getpixel((0,0))
                         if not isinstance(sampled_color, tuple) or len(sampled_color) < 3:
                              print(f"警告：无法在 ({x_orig}, {y_orig}) 获取有效的 RGB 颜色。使用默认黑色。")
                              sampled_color = (0, 0, 0)
                except IndexError:
                    print(f"警告：点采样索引 ({x_orig}, {y_orig}) 超出范围。使用默认黑色。")
                    sampled_color = (0, 0, 0)
                except Exception as pixel_err:
                    print(f"警告：获取像素 ({x_orig}, {y_orig}) 时出错: {pixel_err}。使用默认黑色。")
                    sampled_color = (0, 0, 0)

                row_data.append((char, sampled_color[:3]))
            ascii_char_color_data.append(row_data)

        return ascii_char_color_data

    except Exception as e:
        print(f"在主题 '{active_theme_name}' 的 ASCII 转换和颜色采样过程中出错: {e}")
        traceback.print_exc()
        return None

# create_ascii_png 函数 (无变化)
def create_ascii_png(ascii_char_color_data, # 新参数：包含字符和颜色的数据
                      theme_name,
                      output_path,
                      font, # 接收已加载字体
                      background_color,
                      foreground_color, # 仍然需要用于非 'original' 主题
                      original_image_size=None):
    """
    根据包含字符和采样颜色的数据创建 PNG 图像。
    (函数体无变化)
    """
    if not ascii_char_color_data or not ascii_char_color_data[0]:
        print("错误：没有 ASCII 数据或空行来创建 PNG。")
        return False

    if not isinstance(ascii_char_color_data[0][0], tuple) or len(ascii_char_color_data[0][0]) != 2:
        print("错误：传入 create_ascii_png 的数据结构不正确。应为 list[list[tuple[char, color]]]")
        return False

    is_original_color_theme = theme_name in ["original_dark_bg", "original_light_bg"]
    font_size_val = 10 # 后备字体大小

    try:
        if hasattr(font, 'size'):
            font_size_val = font.size

        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        sample_text_height = '|M_g(`'
        sample_line_text = "".join([item[0] for item in ascii_char_color_data[0]])

        try:
            bbox_h = draw.textbbox((0, 0), sample_text_height, font=font)
            line_height = bbox_h[3] - bbox_h[1]
            bbox_w = draw.textbbox((0, 0), sample_line_text, font=font)
            text_width = bbox_w[2] - bbox_w[0]
        except AttributeError:
            print("警告：正在使用较旧的 Pillow 文本测量方法（getsize）。尺寸可能不太准确。")
            try:
                (_, h) = draw.textsize(sample_text_height, font=font)
                line_height = h
                (w, _) = draw.textsize(sample_line_text, font=font)
                text_width = w
            except AttributeError:
                (_, h) = font.getsize('M')
                line_height = int(h * 1.2)
                w = sum(font.getsize(c)[0] for c in sample_line_text)
                text_width = w

        line_spacing = line_height + 2
        if line_spacing <= 0: line_spacing = font_size_val + 2
        if text_width <= 0: text_width = font_size_val * len(sample_line_text)

        num_rows = len(ascii_char_color_data)
        num_cols = len(ascii_char_color_data[0])
        avg_char_width = text_width / num_cols if num_cols > 0 else font_size_val

        img_width = max(1, text_width)
        img_height = max(1, line_spacing * num_rows)

        output_image = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(output_image)
        y_text = 0

        for y, row_data in enumerate(ascii_char_color_data):
            x_pos = 0
            for x, (char, sampled_color) in enumerate(row_data):
                final_color = None
                if is_original_color_theme:
                    final_color = sampled_color
                    if theme_name == "original_light_bg":
                        darken_factor = 0.7
                        r, g, b = sampled_color
                        new_r = max(0, min(255, int(r * darken_factor)))
                        new_g = max(0, min(255, int(g * darken_factor)))
                        new_b = max(0, min(255, int(b * darken_factor)))
                        final_color = (new_r, new_g, new_b)
                else:
                    if foreground_color is None:
                        print(f"错误：非原始主题 '{theme_name}' 缺少前景色。使用白色。")
                        final_color = "white"
                    else:
                        final_color = foreground_color

                try:
                    draw.text((math.floor(x_pos), y_text), char, font=font, fill=final_color)
                except Exception as char_err:
                    print(f"警告：在文本位置 ({x_pos:.0f},{y_text}) 绘制字符 '{char}' 时出错: {char_err}")

                x_pos += avg_char_width
            y_text += line_spacing

        if RESIZE_OUTPUT and original_image_size:
            original_width, original_height = original_image_size
            if original_width > 0 and original_height > 0:
                original_aspect = original_height / float(original_width)
                target_height = max(1, int(img_width * original_aspect))
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.LANCZOS
                try:
                    print(f"  调整 PNG 大小为 {img_width}x{target_height} 以匹配原始宽高比...")
                    output_image = output_image.resize((img_width, target_height), resample_filter)
                except Exception as resize_err:
                    print(f"警告: 调整大小失败: {resize_err}. 使用原始渲染大小。")
            else:
                print("警告：无法调整大小，原始图像尺寸无效。")
        elif RESIZE_OUTPUT:
            print("警告：请求调整大小但未提供原始图像尺寸。")

        output_image.save(output_path)
        return True

    except Exception as e:
        print(f"在路径 '{output_path}' 为主题 '{theme_name}' 创建或保存 PNG 时出错: {e}")
        traceback.print_exc()
        return False


# --- 核心处理函数 ---
# *** 修改后的 process_image_to_ascii_themes 函数 ***
def process_image_to_ascii_themes(image_path, font, themes_config, base_output_dir, output_width_chars):
    """
    处理单个图像文件，将其所有主题输出保存在 base_output_dir 下以图像名命名的子目录中。

    Args:
        image_path (str): 输入图像的完整路径。
        font (PIL.ImageFont.FreeTypeFont): 加载的字体对象。
        themes_config (dict): 颜色主题配置。
        base_output_dir (str): 保存所有输出的**基础**目录。
        output_width_chars (int): ASCII 网格的宽度。
    """
    print(f"\n正在处理图像: {image_path}")
    results = {'success': 0, 'failed': 0}
    original_img = None
    original_dimensions = (0, 0)

    # --- 获取文件名（不含扩展名）以创建子目录 ---
    base_name = os.path.basename(image_path)
    file_name_no_ext, _ = os.path.splitext(base_name)

    # --- 构建并创建此图像的特定输出子目录 ---
    image_specific_output_dir = os.path.join(base_output_dir, file_name_no_ext)
    try:
        os.makedirs(image_specific_output_dir, exist_ok=True)
        print(f"  输出子目录: {image_specific_output_dir}") # 确认子目录路径
    except OSError as e:
        print(f"  错误：无法为此图像创建输出子目录 '{image_specific_output_dir}': {e}。跳过此图像。")
        results['failed'] = len(THEMES_TO_GENERATE) # 标记所有主题都失败
        return results

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
        # 注意：目录已创建，但没有文件生成
        results['failed'] = len(THEMES_TO_GENERATE)
        return results
    except Exception as e:
        print(f"  打开或转换图像文件 '{os.path.basename(image_path)}' 时出错: {e}")
        traceback.print_exc()
        results['failed'] = len(THEMES_TO_GENERATE)
        return results

    # --- 处理每个主题 ---
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

        # 1. 转换为 ASCII 和采样颜色
        ascii_conv_start = time.perf_counter()
        ascii_char_color_data = image_to_ascii(
            color_image=original_img,
            width_chars=output_width_chars,
            active_theme_name=theme_name
        )
        ascii_conv_end = time.perf_counter()

        if not ascii_char_color_data:
            print(f"    错误：为主题 '{theme_name}' 生成 ASCII 数据或采样颜色失败。跳过 PNG 创建。")
            results['failed'] += 1
            continue

        print(f"      ASCII 转换与颜色采样耗时: {ascii_conv_end - ascii_conv_start:.4f}s")

        # 2. 创建 PNG (保存到 image_specific_output_dir)
        resize_suffix = "_resized" if RESIZE_OUTPUT else ""
        output_filename = f"{file_name_no_ext}_ascii_{theme_name}_{output_width_chars}w{resize_suffix}.png"
        # *** 修改点：使用 image_specific_output_dir ***
        output_filepath = os.path.join(image_specific_output_dir, output_filename)

        png_create_start = time.perf_counter()
        png_success = create_ascii_png(
            ascii_char_color_data=ascii_char_color_data,
            theme_name=theme_name,
            output_path=output_filepath,
            font=font,
            background_color=bg_color,
            foreground_color=fg_color,
            original_image_size=original_dimensions
        )
        png_create_end = time.perf_counter()

        if png_success:
            results['success'] += 1
            print(f"      PNG 创建耗时: {png_create_end - png_create_start:.4f}s")
            # 输出文件名相对于子目录即可
            print(f"      输出已保存: {os.path.join(file_name_no_ext, output_filename)}")
        else:
            results['failed'] += 1
            print(f"      错误：为主题 '{theme_name}' 创建 PNG 失败。")

        theme_end_time = time.perf_counter()
        print(f"    主题 '{theme_name}' 处理耗时: {theme_end_time - theme_start_time:.4f}s")

    return results


# --- process_directory 函数 (无变化) ---
# 它已经传递了正确的 base_output_dir 给 process_image_to_ascii_themes
def process_directory(dir_path, font, themes_config, output_width_chars):
    """
    扫描目录，处理所有支持的图像，并将每个图像的结果保存到单独的子目录中。
    """
    print(f"\n正在处理目录: {dir_path}")
    overall_results = {'processed_files': 0, 'total_success': 0, 'total_failed': 0, 'output_location': None}

    dir_name = os.path.basename(os.path.normpath(dir_path))
    parent_dir = os.path.dirname(os.path.abspath(dir_path))
    # 主输出目录名保持不变
    main_output_dir = os.path.join(parent_dir, f"{dir_name}_ascii_art_{output_width_chars}")
    overall_results['output_location'] = main_output_dir # 报告主目录位置

    # 创建主目录（如果不存在）
    try:
        # 不再需要在此处创建主目录，因为 process_image_to_ascii_themes 会创建子目录，
        # 而 os.makedirs 会自动创建父目录。但为了明确和日志记录，保留它无害。
        os.makedirs(main_output_dir, exist_ok=True)
        print(f"主输出目录: {main_output_dir}")
    except OSError as e:
        print(f"错误：无法创建或访问主输出目录 '{main_output_dir}': {e}。中止。")
        overall_results['total_failed'] = 1 # Mark as failed
        return overall_results

    print("正在扫描支持的图像文件...")
    found_files = []
    try:
        for entry in os.scandir(dir_path):
            if entry.is_file() and entry.name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                found_files.append(entry.path)
    except FileNotFoundError:
        print(f"错误：扫描期间未找到输入目录 '{dir_path}'。")
        overall_results['total_failed'] = 1 # Mark as failed
        return overall_results
    except Exception as e:
        print(f"扫描目录 '{dir_path}' 时出错: {e}")
        overall_results['total_failed'] = 1 # Mark as failed
        return overall_results

    if not found_files:
        print("在目录中未找到支持的图像文件。")
        # 即使没有文件，也返回主输出目录位置
        return overall_results

    print(f"找到 {len(found_files)} 个潜在的图像文件。开始处理...")
    overall_results['processed_files'] = len(found_files)

    for image_file_path in found_files:
        # 调用处理函数，传递 main_output_dir 作为基础目录
        image_results = process_image_to_ascii_themes(
            image_path=image_file_path,
            font=font,
            themes_config=themes_config,
            base_output_dir=main_output_dir, # <--- 传递主目录
            output_width_chars=output_width_chars
        )
        overall_results['total_success'] += image_results['success']
        overall_results['total_failed'] += image_results['failed']

    return overall_results

# --- 输入和摘要函数 (无变化) ---
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
    print("           处理摘要")
    print("===================================")
    input_type = results.get('input_type', 'unknown')
    output_location = results.get('output_location') # 主输出目录

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
             # 指向包含图像子目录的基础目录
            print(f"输出基目录：{os.path.dirname(output_location)}")
            print(f"图像子目录：{os.path.basename(output_location)}")
    elif input_type == 'directory':
        processed_files = results.get('processed_files', 0)
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：目录")
        print(f"找到/尝试处理的图像文件数：{processed_files}")
        print(f"成功生成的 PNG 总数：{success_count}")
        print(f"失败/跳过的主题尝试总数：{fail_count}")
        if output_location:
             # 指向包含所有图像子目录的主目录
            print(f"主输出目录：{output_location}")
            print(f" (每个图像的结果保存在其对应的子目录中)")
    else:
        print(f"状态：未知 ({input_type})")

    print("-----------------------------------")
    print("执行时间:")
    print(f"  - 总处理时间：{duration:.4f} 秒")
    print("===================================")

# --- 主执行函数 (无变化) ---
# 它已经正确地确定了基础输出目录并传递给处理函数
def main():
    """主执行函数。"""
    print("--- ASCII 艺术生成器 (点采样颜色版 + 单独文件夹输出) ---") # 更新标题
    results = {}
    start_time = time.perf_counter()

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filename = "config.ini"
        config_filepath = os.path.join(script_dir, config_filename)

        config = load_config(config_filepath)
        output_width_chars = config["output_width_chars"]
        font_filename = config["font_filename"]
        font_size = config["font_size"]

        print("正在加载字体...")
        font = None
        font_path = os.path.join(script_dir, font_filename)
        font_load_error = False
        try:
            print(f"尝试从以下路径加载字体: {font_path} (大小: {font_size})")
            if not os.path.exists(font_path):
                print(f"警告: 本地路径未找到 '{font_path}'。尝试系统字体 '{font_filename}'...")
                try:
                    font = ImageFont.truetype(font_filename, font_size)
                    print(f"成功加载系统字体 '{font_filename}'。")
                except IOError:
                    print(f"错误: 无法在本地或系统中找到/加载字体 '{font_filename}'。")
                    raise
            else:
                font = ImageFont.truetype(font_path, font_size)
                print("字体加载成功。")

        except IOError as e:
            print(f"致命错误：无法加载字体文件 '{font_filename}'。")
            print(f"错误详情: {e}")
            results = {'input_type': 'font_error', 'font_name': font_filename, 'font_path_tried': font_path}
            font_load_error = True
        except Exception as e:
            print(f"致命错误：加载字体时发生意外错误: {e}")
            results = {'input_type': 'font_error', 'font_name': font_filename, 'font_path_tried': font_path}
            font_load_error = True

        if font_load_error:
            duration = time.perf_counter() - start_time
            print_summary(results, duration)
            sys.exit(1)

        input_path = get_input_path()
        if input_path is None:
            print("未提供输入路径或操作已取消。退出。")
            sys.exit(0)

        processing_start_time = time.perf_counter()

        if os.path.isfile(input_path):
            results['input_type'] = 'file'
            file_dir = os.path.dirname(os.path.abspath(input_path))
            file_name_no_ext, _ = os.path.splitext(os.path.basename(input_path))
            # 基础输出目录名保持不变
            base_output_dir = os.path.join(file_dir, f"{file_name_no_ext}_ascii_art_{output_width_chars}w")
            # 报告这个基础目录，实际文件在下一级子目录
            results['output_location'] = os.path.join(base_output_dir, file_name_no_ext) # 指向预期的子目录

            img_results = process_image_to_ascii_themes(
                input_path,
                font,
                COLOR_THEMES,
                base_output_dir, # 传递基础目录
                output_width_chars
            )
            results['total_success'] = img_results['success']
            results['total_failed'] = img_results['failed']

        elif os.path.isdir(input_path):
            results['input_type'] = 'directory'
            dir_results = process_directory(
                input_path,
                font,
                COLOR_THEMES,
                output_width_chars
             )
            results.update(dir_results)

        else:
            print(f"错误：输入路径 '{input_path}' 不是有效的文件或目录。")
            results['input_type'] = 'invalid'

        processing_end_time = time.perf_counter()
        total_processing_duration = processing_end_time - processing_start_time
        print_summary(results, total_processing_duration)

    except Exception as e:
        print("\n--- 发生未处理的异常 ---")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")
        print("详细追溯信息:")
        traceback.print_exc()
        print("--------------------------")
        results['input_type'] = 'runtime_error'
        duration = time.perf_counter() - start_time
        print_summary(results, duration)
        sys.exit(1)

# --- 主程序入口保持不变 ---
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        try:
            os.chdir(application_path)
            print(f"检测到打包环境，当前目录已设置为: {application_path}")
        except Exception as cd_err:
             print(f"警告：无法切换目录到 {application_path}: {cd_err}")

    main()

    print("\n处理完成。按 Enter 键退出...")
    try:
        input()
    except EOFError:
        pass
