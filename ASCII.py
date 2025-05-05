# -*- coding: utf-8 -*-
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import traceback
import time
import configparser # 导入配置解析器
import concurrent.futures # 用于并行处理
import multiprocessing # 获取 CPU 核心数
import shutil # 用于文件复制

# --- 默认配置 (如果 config.ini 不存在或无效则使用) ---
DEFAULT_OUTPUT_WIDTH_CHARS = 128 # 默认 ASCII 表示宽度
DEFAULT_FONT_FILENAME = "Consolas.ttf" # 默认字体文件名 (确保此文件存在)
DEFAULT_FONT_SIZE = 12 # 默认字体大小
DEFAULT_THEMES_TO_GENERATE = ["light"] # <-- 新增：默认生成的主题列表

ASCII_CHARS = "@%#*+=-:. " # 假设@最暗, ' ' 最亮
# ASCII_CHARS = " .:-=+*#%@" # 反转后，需要调整映射或接受 ' ' 代表最暗

RESIZE_OUTPUT = True # 设置为 True 以将输出 PNG 调整为原始宽高比
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

# --- 颜色主题配置 (无变化) ---
COLOR_THEMES = {
    "dark":              {"background": "black", "foreground": "white"}, # 黑底白字
    "green_term":        {"background": "black", "foreground": "lime"}, # 黑底绿字
    "light":             {"background": "#f0f0f0", "foreground": "black"}, # 灰底黑字
    "amber_term":        {"background": "#1c1c1c", "foreground": "#FFBF00"}, # 黑底黄字
    "original_dark_bg":  {"background": "#363636", "foreground": None}, # 黑底彩色
    "original_light_bg": {"background": "#f0f0f0", "foreground": None}, # 灰底彩色
}

# --- 全局 THEMES_TO_GENERATE 列表已被移除 ---
# 现在从 config.ini 加载

# --- 配置加载函数 (已修改) ---
def load_config(config_filepath):
    """
    从指定的路径加载配置。
    如果文件不存在、键缺失或值无效，则使用默认值。
    返回包含配置值的字典。
    """
    # --- 默认值 ---
    config_values = {
        "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
        "font_filename": DEFAULT_FONT_FILENAME,
        "font_size": DEFAULT_FONT_SIZE,
        "enable_filter": False,
        "filter_type": "gaussian",
        "filter_gaussian_radius": 1.0,
        "filter_median_size": 3,
        "themes_to_generate": list(DEFAULT_THEMES_TO_GENERATE) # <-- 新增: 主题列表默认值 (使用副本)
    }
    print(f"尝试从以下路径加载配置文件: {config_filepath}")
    if not os.path.exists(config_filepath):
        print("未找到 config.ini。将使用默认设置。")
        # 打印所有默认值
        print(f"  默认 OUTPUT_WIDTH_CHARS = {config_values['output_width_chars']}")
        print(f"  默认 FONT_FILENAME = {config_values['font_filename']}")
        print(f"  默认 FONT_SIZE = {config_values['font_size']}")
        print(f"  默认 ENABLE_FILTER = {config_values['enable_filter']}")
        print(f"  默认 FILTER_TYPE = {config_values['filter_type']}")
        print(f"  默认 FILTER_GAUSSIAN_RADIUS = {config_values['filter_gaussian_radius']}")
        print(f"  默认 FILTER_MEDIAN_SIZE = {config_values['filter_median_size']}")
        print(f"  默认 THEMES_TO_GENERATE = {config_values['themes_to_generate']}") # <-- 新增
        return config_values

    parser = configparser.ConfigParser(allow_no_value=True, inline_comment_prefixes=('#', ';'))
    try:
        parser.read(config_filepath, encoding='utf-8')
        print("已找到 config.ini。正在加载设置...")

        # --- 加载 [Settings] 部分 ---
        if 'Settings' in parser:
            settings_section = parser['Settings']
            # (加载 OUTPUT_WIDTH_CHARS, FONT_FILENAME, FONT_SIZE 的代码保持不变)
            # 加载 OUTPUT_WIDTH_CHARS
            try:
                loaded_width = settings_section.getint('OUTPUT_WIDTH_CHARS', fallback=config_values['output_width_chars'])
                if loaded_width > 0:
                    config_values["output_width_chars"] = loaded_width
                    print(f"  已加载 OUTPUT_WIDTH_CHARS = {config_values['output_width_chars']}")
                else:
                    print(f"  警告: config.ini 中的 OUTPUT_WIDTH_CHARS 值 ({loaded_width}) 无效 (必须 > 0)。使用默认值 {config_values['output_width_chars']}。")
            except ValueError:
                print(f"  警告: config.ini 中的 OUTPUT_WIDTH_CHARS 值不是有效的整数。使用默认值 {config_values['output_width_chars']}。")
            except KeyError:
                print(f"  信息: config.ini 中未找到 OUTPUT_WIDTH_CHARS。使用默认值 {config_values['output_width_chars']}。")

            # 加载 FONT_FILENAME (字符串)
            try:
                loaded_filename = settings_section.get('FONT_FILENAME', fallback=config_values['font_filename']).strip()
                if loaded_filename:
                    config_values["font_filename"] = loaded_filename
                    print(f"  已加载 FONT_FILENAME = {config_values['font_filename']}")
                else:
                    print(f"  警告: config.ini 中的 FONT_FILENAME 为空。使用默认值 {config_values['font_filename']}。")
            except KeyError:
                print(f"  信息: config.ini 中未找到 FONT_FILENAME。使用默认值 {config_values['font_filename']}。")

            # 加载 FONT_SIZE
            try:
                loaded_size = settings_section.getint('FONT_SIZE', fallback=config_values['font_size'])
                if loaded_size > 0:
                    config_values["font_size"] = loaded_size
                    print(f"  已加载 FONT_SIZE = {config_values['font_size']}")
                else:
                    print(f"  警告: config.ini 中的 FONT_SIZE 值 ({loaded_size}) 无效 (必须 > 0)。使用默认值 {config_values['font_size']}。")
            except ValueError:
                print(f"  警告: config.ini 中的 FONT_SIZE 值不是有效的整数。使用默认值 {config_values['font_size']}。")
            except KeyError:
                print(f"  信息: config.ini 中未找到 FONT_SIZE。使用默认值 {config_values['font_size']}。")

            # --- 新增：加载 THEMES_TO_GENERATE ---
            try:
                themes_str = settings_section.get('THEMES_TO_GENERATE', fallback=None)
                if themes_str is not None:
                    # 解析逗号分隔的字符串，去除空白，过滤空字符串
                    raw_themes = [theme.strip() for theme in themes_str.split(',')]
                    potential_themes = [theme for theme in raw_themes if theme]

                    if potential_themes:
                        valid_themes = []
                        invalid_themes = []
                        # 验证主题是否存在于 COLOR_THEMES
                        for theme in potential_themes:
                            if theme in COLOR_THEMES:
                                valid_themes.append(theme)
                            else:
                                invalid_themes.append(theme)

                        if valid_themes:
                            config_values["themes_to_generate"] = valid_themes
                            print(f"  已加载 THEMES_TO_GENERATE = {config_values['themes_to_generate']}")
                            if invalid_themes:
                                print(f"  警告: 在 config.ini 中发现无效的主题名称: {invalid_themes}。这些主题将被忽略。")
                        else:
                            print(f"  警告: config.ini 中的 THEMES_TO_GENERATE ('{themes_str}') 不包含任何有效的主题名称。使用默认值 {config_values['themes_to_generate']}。")
                            # 保持默认值不变
                    else:
                        print(f"  警告: config.ini 中的 THEMES_TO_GENERATE 值为空或只包含逗号/空格。使用默认值 {config_values['themes_to_generate']}。")
                        # 保持默认值不变
                else:
                    # fallback 为 None 表示键不存在
                    print(f"  信息: config.ini 中未找到 THEMES_TO_GENERATE。使用默认值 {config_values['themes_to_generate']}。")
                    # 保持默认值不变
            except KeyError: # 虽然 get 有 fallback，但以防万一
                 print(f"  信息: config.ini 中未找到 THEMES_TO_GENERATE。使用默认值 {config_values['themes_to_generate']}。")
                 # 保持默认值不变
            except Exception as e_theme: # 捕获其他可能的解析错误
                print(f"  错误: 读取或解析 THEMES_TO_GENERATE 时出错: {e_theme}。使用默认值 {config_values['themes_to_generate']}。")
                # 保持默认值不变

        else:
            print("警告: 在 config.ini 中未找到 [Settings] 部分。将使用所有默认设置。")
            # 默认值已在 config_values 中设置好

        # --- 加载 [Filter] 部分 (代码不变) ---
        if 'Filter' in parser:
            filter_section = parser['Filter']
            print("  正在加载 [Filter] 设置...")
            # ... (加载 ENABLE_FILTER, FILTER_TYPE, FILTER_GAUSSIAN_RADIUS, FILTER_MEDIAN_SIZE 的代码保持不变) ...
            # 加载 ENABLE_FILTER
            try:
                config_values['enable_filter'] = filter_section.getboolean('ENABLE_FILTER', fallback=config_values['enable_filter'])
                print(f"    已加载 ENABLE_FILTER = {config_values['enable_filter']}")
            except ValueError:
                print(f"    警告: config.ini 中的 ENABLE_FILTER 值不是有效的布尔值 (True/False)。使用默认值 {config_values['enable_filter']}。")
            except KeyError:
                 print(f"    信息: config.ini 中未找到 ENABLE_FILTER。使用默认值 {config_values['enable_filter']}。")

            # 加载 FILTER_TYPE
            try:
                loaded_type = filter_section.get('FILTER_TYPE', fallback=config_values['filter_type']).lower().strip()
                if loaded_type in ['gaussian', 'median']:
                    config_values['filter_type'] = loaded_type
                    print(f"    已加载 FILTER_TYPE = {config_values['filter_type']}")
                else:
                    print(f"    警告: config.ini 中的 FILTER_TYPE 值 '{loaded_type}' 无效 (应为 'gaussian' 或 'median')。使用默认值 '{config_values['filter_type']}'。")
            except KeyError:
                print(f"    信息: config.ini 中未找到 FILTER_TYPE。使用默认值 '{config_values['filter_type']}'。")

            # 加载 FILTER_GAUSSIAN_RADIUS
            try:
                loaded_radius = filter_section.getfloat('FILTER_GAUSSIAN_RADIUS', fallback=config_values['filter_gaussian_radius'])
                if loaded_radius > 0:
                     config_values['filter_gaussian_radius'] = loaded_radius
                     print(f"    已加载 FILTER_GAUSSIAN_RADIUS = {config_values['filter_gaussian_radius']}")
                else:
                     print(f"    警告: config.ini 中的 FILTER_GAUSSIAN_RADIUS 值 ({loaded_radius}) 无效 (必须 > 0)。使用默认值 {config_values['filter_gaussian_radius']}。")
            except ValueError:
                print(f"    警告: config.ini 中的 FILTER_GAUSSIAN_RADIUS 值不是有效的浮点数。使用默认值 {config_values['filter_gaussian_radius']}。")
            except KeyError:
                print(f"    信息: config.ini 中未找到 FILTER_GAUSSIAN_RADIUS。使用默认值 {config_values['filter_gaussian_radius']}。")

            # 加载 FILTER_MEDIAN_SIZE
            try:
                loaded_median_size = filter_section.getint('FILTER_MEDIAN_SIZE', fallback=config_values['filter_median_size'])
                if loaded_median_size >= 3 and loaded_median_size % 2 != 0:
                    config_values['filter_median_size'] = loaded_median_size
                    print(f"    已加载 FILTER_MEDIAN_SIZE = {config_values['filter_median_size']}")
                else:
                    print(f"    警告: config.ini 中的 FILTER_MEDIAN_SIZE 值 ({loaded_median_size}) 无效 (必须是 >= 3 的奇数)。使用默认值 {config_values['filter_median_size']}。")
            except ValueError:
                print(f"    警告: config.ini 中的 FILTER_MEDIAN_SIZE 值不是有效的整数。使用默认值 {config_values['filter_median_size']}。")
            except KeyError:
                print(f"    信息: config.ini 中未找到 FILTER_MEDIAN_SIZE。使用默认值 {config_values['filter_median_size']}。")
        else:
             print("信息: 在 config.ini 中未找到 [Filter] 部分。将使用默认滤波设置 (关闭)。")
             # 默认值已在 config_values 中设置好

    except configparser.Error as e:
        print(f"错误: 读取 config.ini 时出错: {e}。将使用所有默认设置。")
        # 重置为所有默认值 (确保主题列表也是默认的)
        config_values = {
            "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
            "font_filename": DEFAULT_FONT_FILENAME,
            "font_size": DEFAULT_FONT_SIZE,
            "enable_filter": False,
            "filter_type": "gaussian",
            "filter_gaussian_radius": 1.0,
            "filter_median_size": 3,
            "themes_to_generate": list(DEFAULT_THEMES_TO_GENERATE) # 确保重置时也使用默认主题
        }
    except Exception as e:
        print(f"错误: 处理 config.ini 时发生意外错误: {e}。将使用所有默认设置。")
        # 重置为所有默认值
        config_values = {
            "output_width_chars": DEFAULT_OUTPUT_WIDTH_CHARS,
            "font_filename": DEFAULT_FONT_FILENAME,
            "font_size": DEFAULT_FONT_SIZE,
            "enable_filter": False,
            "filter_type": "gaussian",
            "filter_gaussian_radius": 1.0,
            "filter_median_size": 3,
            "themes_to_generate": list(DEFAULT_THEMES_TO_GENERATE)
        }

    print("配置加载完成。\n")
    return config_values

# --- 图像处理函数 ---

# ==============================================================================
# *** image_to_ascii 函数 (无变化) ***
# ==============================================================================
def image_to_ascii(color_image, width_chars, active_theme_name):
    """
    将 PIL 彩色图像转换为包含字符和对应原图点采样颜色的数据结构。
    此版本模拟 C++ 逻辑：
    1. 直接在原始彩色图像上采样。
    2. 使用 (R+G+B)/3 计算灰度值。
    3. 字符映射逻辑不考虑背景明暗。
    """
    try:
        # 1. 确保输入是 RGB 并获取尺寸
        image_rgb = color_image if color_image.mode == 'RGB' else color_image.convert('RGB')
        original_width, original_height = image_rgb.size

        if original_width <= 0 or original_height <= 0:
            print("错误：原始图像尺寸无效。")
            return None

        # 2. 计算目标字符网格的高度 (保持宽高比)
        aspect_ratio = original_height / float(original_width)
        # C++ 版本使用 charAspectRatioCorrection = 2.0 (默认)，这里保持 Python 之前的 0.5
        # 如果想严格模拟 C++ 的默认行为，需要调整这里
        char_aspect_ratio_correction = 0.5 # 或者调整为 2.0? 取决于 C++ 配置
        width_chars = max(1, int(width_chars))
        new_height_chars = int(width_chars * aspect_ratio * char_aspect_ratio_correction)
        new_height_chars = max(1, new_height_chars) # 确保至少有一行

        # 3. 准备字符映射
        num_chars = len(ASCII_CHARS)
        if num_chars == 0:
            print("错误：ASCII_CHARS 不能为空。")
            return None

        # 4. 计算采样比例因子
        xScale = float(original_width) / width_chars
        yScale = float(original_height) / new_height_chars

        # 5. 准备像素访问器和结果列表
        ascii_char_color_data = []
        try:
            original_pixels = image_rgb.load() # 优化像素访问
        except Exception as load_err:
             print(f"警告: 无法创建像素访问对象: {load_err}. 将使用 getpixel (可能较慢)。")
             original_pixels = None # 标记，后面用 getpixel

        # 6. 遍历目标字符网格
        for y_char in range(new_height_chars):
            row_data = []
            for x_char in range(width_chars):
                # a. 计算原始图像中的采样坐标 (中心点)
                x_orig = int(math.floor((x_char + 0.5) * xScale))
                y_orig = int(math.floor((y_char + 0.5) * yScale))

                # b. 确保坐标在边界内
                x_orig = max(0, min(x_orig, original_width - 1))
                y_orig = max(0, min(y_orig, original_height - 1))

                # c. 获取采样点的 RGB 颜色
                sampled_color = (0, 0, 0) # Default to black on error
                try:
                    if original_pixels:
                        sampled_color = original_pixels[x_orig, y_orig]
                    else:
                        sampled_color = image_rgb.getpixel((x_orig, y_orig))

                    # 确保是有效的 RGB 元组
                    if not isinstance(sampled_color, tuple) or len(sampled_color) < 3:
                        # Fallback if pixel access didn't return expected tuple (e.g., for palette images)
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

                # d. 从采样颜色计算灰度值 (模拟 C++ 的简单平均法)
                r, g, b = sampled_color[:3] # 取前三个元素以防有 alpha 通道
                # gray = (int(r) + int(g) + int(b)) // 3 # 整数除法
                # 使用浮点数除法和 floor 模拟 C++ 的 floor((gray/256.0f)...)
                gray = (int(r) + int(g) + int(b)) / 3.0

                # e. 映射灰度值到字符索引 (模拟 C++ 逻辑)
                # C++: floor((gray / 256.0f) * NUM_ASCII_CHARS)
                # Python: math.floor((gray / 256.0) * num_chars)
                ascii_index = math.floor((gray / 256.0) * num_chars)

                # f. 确保索引在有效范围内
                ascii_index = max(0, min(ascii_index, num_chars - 1))

                # g. 选择字符
                char = ASCII_CHARS[ascii_index]

                # h. 存储字符和原始颜色
                row_data.append((char, sampled_color[:3]))
            # i. 添加行数据到结果列表
            ascii_char_color_data.append(row_data)

        # 7. 返回结果
        return ascii_char_color_data

    except Exception as e:
        # 保留原始的异常处理
        print(f"在主题 '{active_theme_name}' 的 ASCII 转换和颜色采样过程中出错: {e}")
        # traceback.print_exc() # 在子进程中打印完整的traceback可能比较混乱，可以选择性注释掉
        return None
# ==============================================================================
# *** image_to_ascii 函数修改结束 (无变化) ***
# ==============================================================================


# ==============================================================================
# *** create_ascii_png 函数 (无变化) ***
# ==============================================================================
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
        sample_text_height = '|M_g(`' # 尝试包含一些升部和降部字符
        # 确保 sample_line_text 不为空
        if not ascii_char_color_data[0]: return False # 如果第一行为空则无法继续
        sample_line_text = "".join([item[0] for item in ascii_char_color_data[0]])
        if not sample_line_text: # 如果第一行全是空字符或无法获取字符
             # 尝试用 'M' 来估算宽度
             print("警告：无法从第一行获取样本文本，将使用'M'估算宽度。")
             sample_line_text = 'M' * len(ascii_char_color_data[0])
             if not sample_line_text: sample_line_text = "M" # 最终后备


        # 使用 getbbox 获取更准确的尺寸
        try:
            # left, top, right, bottom
            bbox_h = draw.textbbox((0, 0), sample_text_height, font=font, anchor="lt") # 左上角对齐
            # 使用所有字符中最高的 ascent 和 最低的 descent 可能更准确，但复杂
            # 这里用包含升降部的字符串近似
            line_height = bbox_h[3] - bbox_h[1] if bbox_h else font_size_val # 从 bbox 获取高度

            bbox_w = draw.textbbox((0, 0), sample_line_text, font=font, anchor="lt")
            text_width = bbox_w[2] - bbox_w[0] if bbox_w else font_size_val * len(sample_line_text) # 从 bbox 获取宽度

        except AttributeError: # Pillow < 9.2.0? or other issues
            print("警告：textbbox 不可用或出错。正在使用较旧的 Pillow 文本测量方法（textsize）。尺寸可能不太准确。")
            try:
                # textsize 可能不包含字体内部的空白
                size_h = draw.textsize(sample_text_height, font=font)
                line_height = size_h[1]
                size_w = draw.textsize(sample_line_text, font=font)
                text_width = size_w[0]
            except AttributeError: # Pillow < 8.0.0?
                print("警告：textsize 不可用。正在使用更旧的 font.getsize。尺寸可能非常不准确。")
                try:
                    (_, h) = font.getsize('M') # 用 'M' 的高度近似
                    line_height = int(h * 1.2) # 增加一点行间距
                    w = sum(font.getsize(c)[0] for c in sample_line_text)
                    text_width = w
                except Exception as e_getsize:
                    print(f"错误: 无法使用任何方法测量文本尺寸: {e_getsize}. 使用默认值。")
                    line_height = font_size_val + 4
                    text_width = font_size_val * len(sample_line_text)


        # 确保尺寸有效
        line_spacing = line_height + 2 # 增加2像素行间距
        if line_spacing <= 0: line_spacing = font_size_val + 2
        if text_width <= 0: text_width = font_size_val * len(sample_line_text) if sample_line_text else font_size_val

        num_rows = len(ascii_char_color_data)
        num_cols = len(ascii_char_color_data[0]) if num_rows > 0 else 0
        # 平均字符宽度可能不准，特别是对于比例字体。但对于等宽字体尚可。
        avg_char_width = text_width / num_cols if num_cols > 0 else font_size_val

        img_width = max(1, int(math.ceil(text_width))) # 使用 ceil 确保宽度足够
        img_height = max(1, int(math.ceil(line_spacing * num_rows))) # 使用 ceil

        output_image = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(output_image)
        y_text = 0 # 从顶部开始绘制

        # 绘制文本
        for y, row_data in enumerate(ascii_char_color_data):
            x_pos = 0 # 每行开始时重置 x 位置
            for x, (char, sampled_color) in enumerate(row_data):
                final_color = None
                if is_original_color_theme:
                    final_color = sampled_color
                    # 轻微调暗亮背景上的彩色字符
                    if theme_name == "original_light_bg":
                        darken_factor = 0.8 # 稍微调暗一点
                        try:
                            r, g, b = sampled_color
                            new_r = max(0, min(255, int(r * darken_factor)))
                            new_g = max(0, min(255, int(g * darken_factor)))
                            new_b = max(0, min(255, int(b * darken_factor)))
                            final_color = (new_r, new_g, new_b)
                        except (TypeError, ValueError):
                            final_color = sampled_color # 如果颜色无效则保持原样
                else: # 非原始颜色主题
                    if foreground_color is None:
                        print(f"错误：非原始主题 '{theme_name}' 缺少前景色。使用白色。")
                        final_color = "white"
                    else:
                        final_color = foreground_color

                # 使用 draw.text 绘制单个字符
                try:
                    # anchor='lt' 表示文本的左上角位于 (x_pos, y_text)
                    draw.text((math.floor(x_pos), y_text), char, font=font, fill=final_color, anchor="lt")
                except Exception as char_err:
                    print(f"警告：在文本位置 ({x_pos:.0f},{y_text}) 绘制字符 '{char}' 时出错: {char_err}")

                # 更新 x 位置，使用平均宽度（对于等宽字体较准）
                x_pos += avg_char_width
            # 更新 y 位置，移动到下一行
            y_text += line_spacing

        # 调整大小 (可选)
        if RESIZE_OUTPUT and original_image_size:
            original_width, original_height = original_image_size
            if original_width > 0 and original_height > 0:
                # 保持输出图像的宽度不变，根据原始宽高比调整高度
                original_aspect = original_height / float(original_width)
                target_height = max(1, int(img_width * original_aspect))
                try:
                    resample_filter = Image.Resampling.LANCZOS # 高质量重采样
                except AttributeError:
                    resample_filter = Image.LANCZOS # 兼容旧版 Pillow
                try:
                    # 注意：这个 print 语句可能在子进程中执行，输出会混合
                    # print(f"    调整 PNG 大小为 {img_width}x{target_height} 以匹配原始宽高比...")
                    output_image = output_image.resize((img_width, target_height), resample_filter)
                except Exception as resize_err:
                    print(f"警告: 调整大小失败: {resize_err}. 使用原始渲染大小。")
            else:
                print("警告：无法调整大小，原始图像尺寸无效。")
        elif RESIZE_OUTPUT:
            print("警告：请求调整大小但未提供原始图像尺寸。")

        # 保存图像
        output_image.save(output_path)
        return True

    except Exception as e:
        print(f"在路径 '{output_path}' 为主题 '{theme_name}' 创建或保存 PNG 时出错: {e}")
        # traceback.print_exc() # 在子进程中打印完整的traceback可能比较混乱
        return False
# ==============================================================================
# *** create_ascii_png 函数修改结束 (无变化) ***
# ==============================================================================


# ==============================================================================
# *** 修改后的 process_image_to_ascii_themes 函数 ***
# ==============================================================================
# 修改签名，接收 filter_settings 和 themes_list_to_generate
def process_image_to_ascii_themes(image_path, font_info, themes_config, base_output_dir,
                                  output_width_chars, filter_settings, themes_list_to_generate): # <-- 新增 themes_list_to_generate
    """
    处理单个图像文件，将其所有指定主题的输出保存在 base_output_dir 下以图像名命名的子目录中。
    此函数在单独的进程中执行，并在开始时加载字体。
    根据 filter_settings 对加载的图像应用滤波器。
    返回一个字典，包含成功和失败的主题数量。
    """
    process_id = os.getpid()
    short_image_name = os.path.basename(image_path)
    # 使用传入的主题列表计算失败数
    num_themes_attempted = len(themes_list_to_generate)
    results = {'success': 0, 'failed': 0}
    font = None # <-- 在子进程中初始化

    # --- 在子进程开始时加载字体 (代码不变) ---
    try:
        font_type = font_info.get('type')
        if font_type == 'truetype':
            font = ImageFont.truetype(font_info['path'], font_info['size'])
        elif font_type == 'default':
            font = ImageFont.load_default()
        else:
            print(f"[PID:{process_id}] 错误: 无效的 font_info 类型 '{font_type}'。回退到默认字体。")
            font = ImageFont.load_default() # Fallback
    except Exception as e_load_worker:
        print(f"[PID:{process_id}] 错误: 在工作进程中加载字体失败: {e_load_worker}。回退到默认字体。")
        try:
            font = ImageFont.load_default()
        except Exception as e_load_default_worker:
            print(f"[PID:{process_id}] 致命错误: 连默认字体都无法在工作进程中加载: {e_load_default_worker}")
            results['failed'] = num_themes_attempted # 所有尝试的主题都失败
            return results

    # --- 处理逻辑 ---
    original_img = None
    original_dimensions = (0, 0)

    base_name = os.path.basename(image_path)
    file_name_no_ext, _ = os.path.splitext(base_name)
    image_specific_output_dir = os.path.join(base_output_dir, file_name_no_ext)

    try:
        os.makedirs(image_specific_output_dir, exist_ok=True)
    except OSError as e:
        print(f"[PID:{process_id}] 错误: 无法创建输出子目录 '{image_specific_output_dir}': {e}。跳过图像。")
        results['failed'] = num_themes_attempted
        return results

    img_to_process = None # 用于存储可能被滤波处理后的图像
    try:
        with Image.open(image_path) as img_opened:
            original_img = img_opened.copy() # 复制一份，避免修改原始对象（如果后续需要）
            original_dimensions = original_img.size
            img_to_process = original_img.convert('RGB') # 转换为RGB用于处理

        if not img_to_process: raise ValueError("无法加载或转换图像。")

        # --- 应用滤波器 (代码不变) ---
        apply_filter = filter_settings.get('enable_filter', False)
        if apply_filter:
            filter_type = filter_settings.get('filter_type', 'gaussian')
            gaussian_radius = filter_settings.get('filter_gaussian_radius', 1.0)
            median_size = filter_settings.get('filter_median_size', 3)
            print(f"[PID:{process_id}] 文件 '{short_image_name}': 启用滤波器。") # 提示滤波已启用
            try:
                filter_start_time = time.perf_counter()
                if filter_type == 'gaussian':
                    print(f"  应用高斯模糊 (半径={gaussian_radius})...")
                    img_to_process = img_to_process.filter(ImageFilter.GaussianBlur(radius=gaussian_radius))
                elif filter_type == 'median':
                    # 确保 size 合法 (虽然 load_config 已做检查，双重保险)
                    median_size = median_size if median_size >= 3 and median_size % 2 != 0 else 3
                    print(f"  应用中值滤波 (尺寸={median_size})...")
                    img_to_process = img_to_process.filter(ImageFilter.MedianFilter(size=median_size))
                filter_end_time = time.perf_counter()
                # print(f"  滤波耗时: {filter_end_time - filter_start_time:.4f} 秒") # 可选：打印滤波耗时
            except Exception as filter_err:
                 print(f"  警告: 应用滤波器 ({filter_type}) 失败: {filter_err}。将使用原始图像进行转换。")
                 img_to_process = original_img.convert('RGB') # 确保回退到原始RGB图像

    except FileNotFoundError:
        print(f"[PID:{process_id}] 错误: 未找到图像文件 '{image_path}'。跳过。")
        results['failed'] = num_themes_attempted
        return results
    except Exception as e:
        print(f"[PID:{process_id}] 打开/转换/滤波图像 '{short_image_name}' 时出错: {e}")
        results['failed'] = num_themes_attempted
        return results

    # --- 后续处理使用 img_to_process (可能已滤波) ---
    # --- 修改循环：使用传入的 themes_list_to_generate ---
    for theme_name in themes_list_to_generate:
        theme_details = themes_config.get(theme_name)
        # theme_name 应该总是有效的，因为 load_config 已经验证过
        # 但为了安全起见，还是检查一下
        if not theme_details:
            print(f"[PID:{process_id}] 内部错误警告: 尝试生成未定义的主题 '{theme_name}'。跳过。")
            results['failed'] += 1
            continue

        bg_color = theme_details["background"]
        fg_color = theme_details.get("foreground")

        # --- 调用 image_to_ascii 时传入处理过的图像 ---
        ascii_char_color_data = image_to_ascii(img_to_process, output_width_chars, theme_name) # <--- 使用 img_to_process
        if not ascii_char_color_data:
            print(f"[PID:{process_id}] 错误: 为主题 '{theme_name}' 生成 ASCII 数据失败。")
            results['failed'] += 1
            continue

        # 添加滤波信息到输出文件名 (代码不变)
        filter_suffix = ""
        if apply_filter:
             filter_suffix = f"_filter-{filter_settings.get('filter_type','na')}" # 例如 _filter-gaussian

        resize_suffix = "_resized" if RESIZE_OUTPUT else ""
        # 将滤波后缀放在宽度后面，主题前面
        output_filename = f"{file_name_no_ext}_ascii_{output_width_chars}w{filter_suffix}_{theme_name}{resize_suffix}.png"
        output_filepath = os.path.join(image_specific_output_dir, output_filename)

        # 使用在子进程中加载的 font 对象
        png_success = create_ascii_png(
            ascii_char_color_data, theme_name, output_filepath, font,
            bg_color, fg_color, original_dimensions
        )

        if png_success:
            results['success'] += 1
        else:
            results['failed'] += 1
            print(f"[PID:{process_id}] 错误: 为主题 '{theme_name}' 创建 PNG 失败。")

    return results


# ==============================================================================
# *** 修改后的 process_directory 函数 ***
# ==============================================================================
# 修改签名，接收 filter_settings, config_filepath, 和 themes_list_to_generate
def process_directory(dir_path, font_info, themes_config, output_width_chars,
                      filter_settings, config_filepath, themes_list_to_generate): # <-- 新增 themes_list_to_generate
    """
    扫描目录，使用进程池并行处理所有支持的图像。
    传递 font_info, filter_settings 和 themes_list_to_generate 给子进程。
    在主输出目录创建后，复制 config.ini。
    目录名包含滤波器信息。
    """
    print(f"\n正在处理目录: {dir_path}")
    # 计算可能的总失败数（如果一个文件失败，所有主题都计入）
    num_themes_per_file = len(themes_list_to_generate)
    overall_results = {'processed_files': 0, 'total_success': 0, 'total_failed': 0, 'output_location': None}
    start_dir_processing_time = time.perf_counter()

    dir_name = os.path.basename(os.path.normpath(dir_path))
    parent_dir = os.path.dirname(os.path.abspath(dir_path))

    # --- 确定滤波器标识用于文件夹命名 (代码不变) ---
    filter_tag = "nofilter"
    if filter_settings.get("enable_filter", False):
        filter_type = filter_settings.get("filter_type", "gaussian")
        if filter_type == 'gaussian':
            filter_tag = 'gaussian'
        elif filter_type == 'median':
            filter_tag = 'median'

    # --- 主输出目录名包含宽度和滤波器类型 (代码不变) ---
    main_output_dir = os.path.join(parent_dir, f"{dir_name}_ascii_art_{output_width_chars}w_{filter_tag}")
    overall_results['output_location'] = main_output_dir

    try:
        os.makedirs(main_output_dir, exist_ok=True)
        print(f"主输出目录: {main_output_dir}")

        # --- 复制配置文件 (代码不变) ---
        if os.path.exists(config_filepath):
            try:
                dest_config_path = os.path.join(main_output_dir, "config_used.txt")
                shutil.copy2(config_filepath, dest_config_path) # copy2 尝试保留元数据
                print(f"  已将配置文件复制到: {dest_config_path}")
            except Exception as copy_err:
                print(f"  警告：复制配置文件 '{config_filepath}' 到输出目录失败: {copy_err}")
        else:
             print(f"  警告：未找到原始配置文件 '{config_filepath}'，无法复制。")

    except OSError as e:
        print(f"错误：无法创建主输出目录 '{main_output_dir}': {e}。")
        overall_results['total_failed'] = 1 # 标记失败，因为无法创建输出目录
        return overall_results # 提前返回

    # --- 扫描和处理逻辑 ---
    print("正在扫描支持的图像文件...")
    found_files = []
    try:
        for entry in os.scandir(dir_path):
             if entry.is_file() and entry.name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                 found_files.append(entry.path)
    except Exception as e:
        print(f"扫描目录 '{dir_path}' 时出错: {e}")
        overall_results['total_failed'] = 1
        return overall_results

    if not found_files:
        print("在目录中未找到支持的图像文件。")
        return overall_results

    num_files = len(found_files)
    print(f"找到 {num_files} 个支持的图像文件。开始并行处理...")
    overall_results['processed_files'] = num_files

    max_workers = None
    futures = {}
    # 使用 try...finally 确保 executor 被关闭
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
    try:
        for image_file_path in found_files:
            # --- 修改：在 submit 时传递 themes_list_to_generate ---
            future = executor.submit(
                process_image_to_ascii_themes, # Target function
                image_file_path,               # Args...
                font_info,                     # <-- 传递 font_info
                themes_config,
                main_output_dir,               # <-- 使用新的目录名
                output_width_chars,
                filter_settings,               # <-- 传递 filter_settings
                themes_list_to_generate        # <-- 新增：传递主题列表
            )
            futures[future] = image_file_path

        processed_count = 0
        print("--- 开始处理文件 (每个文件完成后会显示结果) ---")
        for future in concurrent.futures.as_completed(futures):
            image_path = futures[future]
            image_basename = os.path.basename(image_path)
            processed_count += 1
            try:
                image_results = future.result()
                overall_results['total_success'] += image_results.get('success', 0)
                overall_results['total_failed'] += image_results.get('failed', 0)
                print(f"  [进度 {processed_count}/{num_files}] 处理完成: '{image_basename}'")
            except Exception as exc:
                 print(f"  [进度 {processed_count}/{num_files}] 处理图像 '{image_basename}' 时主进程捕获到异常: {exc}")
                 # 如果子进程异常退出，假设该文件的所有主题都失败了
                 overall_results['total_failed'] += num_themes_per_file
        print("--- 所有文件处理任务已完成 ---")

    finally:
        print("正在关闭进程池...")
        executor.shutdown(wait=True)
        print("进程池已关闭。")


    end_dir_processing_time = time.perf_counter()
    print(f"目录 '{dir_path}' 处理总耗时: {end_dir_processing_time - start_dir_processing_time:.4f} 秒")

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
                input_path = ""
        except KeyboardInterrupt:
            print("\n操作被用户取消。")
            return None
        except EOFError:
            print("\n接收到输入结束信号。")
            return None
    return input_path

def print_summary(results, duration):
    """打印最终的处理摘要。"""
    print("\n===================================")
    print("             处理摘要")
    print("===================================")
    input_type = results.get('input_type', 'unknown')
    output_location = results.get('output_location')
    themes_generated = results.get('themes_generated_list', []) # 获取实际生成的主题列表

    if input_type == 'invalid':
        print("状态：失败（无效的输入路径）")
    elif input_type == 'font_error':
        print("状态：失败（无法加载所需字体）")
        font_name = results.get('font_name', '未知')
        font_path_tried = results.get('font_path_tried', '未知')
        print(f"  尝试加载字体: '{font_name}'")
        print(f"  尝试路径: {font_path_tried}")
    elif input_type == 'runtime_error':
         print("状态：失败（发生运行时错误）")
    elif input_type == 'no_themes':
         print("状态：未执行（没有有效的主题可供生成）")
         print(f"  请检查 config.ini 中的 THEMES_TO_GENERATE 设置。")
    elif input_type == 'file':
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：单个文件")
        if themes_generated:
            print(f"尝试生成的主题: {themes_generated}")
        print(f"已处理的主题数：{success_count + fail_count}")
        print(f"  - 成功的 PNG 数量：{success_count}")
        print(f"  - 失败/跳过的主题数量：{fail_count}")
        if (success_count > 0 or fail_count > 0) and output_location:
            print(f"输出基目录：{os.path.dirname(output_location)}")
            print(f"图像子目录：{os.path.basename(output_location)}")
    elif input_type == 'directory':
        processed_files = results.get('processed_files', 0)
        success_count = results.get('total_success', 0)
        fail_count = results.get('total_failed', 0)
        print(f"输入类型：目录")
        print(f"找到/尝试处理的图像文件数：{processed_files}")
        if themes_generated:
            print(f"每个文件尝试生成的主题: {themes_generated}")
        print(f"成功生成的 PNG 总数（跨所有文件和主题）：{success_count}")
        print(f"失败/跳过的主题尝试总数（跨所有文件）：{fail_count}")
        if output_location:
            print(f"主输出目录：{output_location}")
            print(f" (每个图像的结果保存在其对应的子目录中)")
    else:
        print(f"状态：未知 ({input_type})")

    print("-----------------------------------")
    print("执行时间:")
    print(f"  - 总处理时间：{duration:.4f} 秒")
    print("===================================")


# ==============================================================================
# *** 修改后的 main 函数 ***
# ==============================================================================
def main():
    """主执行函数。"""
    print("--- ASCII 艺术生成器 ---")
    results = {'input_type': 'unknown'}
    start_time = time.perf_counter()
    font_info = None

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_filename = "config.ini"
        config_filepath = os.path.join(script_dir, config_filename) # 获取 config.ini 的完整路径

        # --- 加载配置 (现在包含滤波和主题列表设置) ---
        config = load_config(config_filepath)
        output_width_chars = config["output_width_chars"]
        font_filename = config["font_filename"]
        font_size = config["font_size"]
        themes_to_generate = config["themes_to_generate"] # <-- 获取主题列表
        results['themes_generated_list'] = themes_to_generate # <-- 存储用于摘要
        # --- 提取滤波设置 (代码不变) ---
        filter_settings = {
            "enable_filter": config.get("enable_filter", False),
            "filter_type": config.get("filter_type", "gaussian"),
            "filter_gaussian_radius": config.get("filter_gaussian_radius", 1.0),
            "filter_median_size": config.get("filter_median_size", 3),
        }

        # --- 确定滤波器标识用于文件夹命名 (代码不变) ---
        filter_tag = "nofilter"
        if filter_settings["enable_filter"]:
            filter_type = filter_settings["filter_type"]
            if filter_type == 'gaussian':
                filter_tag = 'gaussian'
            elif filter_type == 'median':
                filter_tag = 'median'

        # 打印应用的滤波设置（如果启用）(代码不变)
        if filter_settings["enable_filter"]:
             print(f"图像预处理滤波器已启用: 类型={filter_settings['filter_type']} (标识: {filter_tag})")
             if filter_settings['filter_type'] == 'gaussian':
                 print(f"  高斯模糊半径: {filter_settings['filter_gaussian_radius']}")
             elif filter_settings['filter_type'] == 'median':
                 print(f"  中值滤波尺寸: {filter_settings['filter_median_size']}")
        else:
             print(f"图像预处理滤波器已禁用 (标识: {filter_tag})。")
        print("-" * 20) # 分隔线


        # --- 新增：检查是否有主题需要生成 ---
        if not themes_to_generate:
            print("错误：根据配置文件，没有有效的主题需要生成。请检查 config.ini。")
            results['input_type'] = 'no_themes' # 特殊状态码
            duration = time.perf_counter() - start_time
            print_summary(results, duration)
            sys.exit(1) # 退出，因为无事可做

        print(f"将为每个图像生成以下主题: {themes_to_generate}")
        print("-" * 20) # 分隔线


        print("检查字体设置...")
        # --- 字体加载逻辑 (代码不变) ---
        preferred_font_loaded = False
        local_font_path = os.path.join(script_dir, font_filename)
        try:
             # 1. 尝试本地路径
             print(f"尝试本地路径: {local_font_path} (大小: {font_size})")
             if os.path.exists(local_font_path):
                 _ = ImageFont.truetype(local_font_path, font_size)
                 print(f"成功验证本地字体 '{font_filename}'。")
                 font_info = {'type': 'truetype', 'path': local_font_path, 'size': font_size}
                 results['font_used'] = f"本地 '{font_filename}'"
                 results['font_size_used'] = font_size
                 preferred_font_loaded = True

             # 2. 尝试系统路径
             if not preferred_font_loaded:
                 print(f"警告: 本地未找到。尝试系统字体 '{font_filename}'...")
                 try:
                     _ = ImageFont.truetype(font_filename, font_size)
                     print(f"成功验证系统字体 '{font_filename}'。")
                     font_info = {'type': 'truetype', 'path': font_filename, 'size': font_size}
                     results['font_used'] = f"系统 '{font_filename}'"
                     results['font_size_used'] = font_size
                     preferred_font_loaded = True
                 except IOError:
                     print(f"警告: 系统中也未找到 '{font_filename}'。将使用默认字体。")

        except IOError as e:
             print(f"警告: 验证首选字体 '{font_filename}' 时出错: {e}。将使用默认字体。")
        except Exception as e:
             print(f"警告: 验证首选字体 '{font_filename}' 时发生意外错误: {e}。将使用默认字体。")

         # 3. 如果首选字体验证失败，设置使用默认字体
        if not preferred_font_loaded:
             print("设置使用 Pillow 内置默认字体。")
             font_info = {'type': 'default'}
             results['font_used'] = "Pillow 内置默认字体"
             try:
                 temp_default_font = ImageFont.load_default()
                 bbox = temp_default_font.getbbox("M") if hasattr(temp_default_font, 'getbbox') else (0,0,6,10) # Fallback size estimate
                 default_font_approx_height = bbox[3] - bbox[1]
                 results['font_size_used'] = f"~{default_font_approx_height}px (内置)"
                 del temp_default_font
             except Exception:
                 results['font_size_used'] = "未知 (内置)"


        # --- 字体信息准备完成 ---
        if font_info is None:
            print("致命错误：未能确定要使用的字体信息。")
            sys.exit(1)

        input_path = get_input_path()
        if input_path is None:
            print("操作已取消。")
            duration = time.perf_counter() - start_time
            print_summary(results, duration)
            sys.exit(0)

        processing_start_time = time.perf_counter()

        if os.path.isfile(input_path):
            results['input_type'] = 'file'
            file_dir = os.path.dirname(os.path.abspath(input_path))
            file_name_no_ext, _ = os.path.splitext(os.path.basename(input_path))
            # --- 主输出目录命名 (代码不变) ---
            base_output_dir = os.path.join(file_dir, f"{file_name_no_ext}_ascii_art_{output_width_chars}w_{filter_tag}")

            print(f"\n正在处理单个文件: {os.path.basename(input_path)}")
            print(f"主输出目录: {base_output_dir}")

            # --- 创建目录并复制配置文件 (单文件模式) (代码不变) ---
            try:
                os.makedirs(base_output_dir, exist_ok=True)
                # --- 复制配置文件 ---
                if os.path.exists(config_filepath):
                    try:
                        dest_config_path = os.path.join(base_output_dir, "config_used.txt")
                        shutil.copy2(config_filepath, dest_config_path)
                        print(f"  已将配置文件复制到: {dest_config_path}")
                    except Exception as copy_err:
                        print(f"  警告：复制配置文件 '{config_filepath}' 到输出目录失败: {copy_err}")
                else:
                     print(f"  警告：未找到原始配置文件 '{config_filepath}'，无法复制。")

                # --- 处理单文件，传递 filter_settings 和 themes_to_generate ---
                img_results = process_image_to_ascii_themes(
                    input_path,
                    font_info,
                    COLOR_THEMES,        # 传递完整的 COLOR_THEMES 字典
                    base_output_dir,     # <-- 使用新的目录名
                    output_width_chars,
                    filter_settings,     # <-- 传递 filter_settings
                    themes_to_generate   # <-- 新增：传递要生成的主题列表
                )
                results['total_success'] = img_results.get('success', 0)
                results['total_failed'] = img_results.get('failed', 0)
                # output_location 对于单文件是指包含该文件输出的那个子目录
                results['output_location'] = os.path.join(base_output_dir, file_name_no_ext)
                print(f"处理完成: '{os.path.basename(input_path)}'")

            except OSError as e:
                 print(f"错误：无法创建主输出目录 '{base_output_dir}': {e}。")
                 results['total_failed'] = len(themes_to_generate) # 标记失败

            except Exception as single_err:
                 print(f"处理单文件 '{input_path}' 时发生顶层错误: {single_err}")
                 traceback.print_exc() # 打印详细错误
                 results['total_failed'] = len(themes_to_generate) # 假定所有主题都失败了

        elif os.path.isdir(input_path):
            results['input_type'] = 'directory'
            # --- 处理目录，传递 filter_settings, config_filepath 和 themes_to_generate ---
            dir_results = process_directory(
                input_path,
                font_info,
                COLOR_THEMES,          # 传递完整的 COLOR_THEMES 字典
                output_width_chars,
                filter_settings,       # <-- 传递 filter_settings
                config_filepath,       # <-- 传递 config_filepath
                themes_to_generate     # <-- 新增：传递主题列表
             )
            results.update(dir_results)

        else:
            print(f"错误：输入路径 '{input_path}' 不是有效的文件或目录。")
            results['input_type'] = 'invalid'

        processing_end_time = time.perf_counter()
        total_processing_duration = processing_end_time - processing_start_time
        # 将总时长传递给 print_summary
        results['total_duration_incl_load'] = time.perf_counter() - start_time
        # 使用 processing_duration 显示处理时间
        print_summary(results, total_processing_duration)


    except Exception as e:
        print("\n--- 发生未处理的全局异常 ---")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")
        traceback.print_exc()
        results['input_type'] = 'runtime_error'
        duration = time.perf_counter() - start_time
        if 'font_used' not in results: results['font_used'] = '加载失败或未知'
        if 'font_size_used' not in results: results['font_size_used'] = '未知'
        print_summary(results, duration)
        sys.exit(1)

# --- 主程序入口 (确保在 __main__ 下) ---
if __name__ == "__main__":
    # 这段代码对于多进程打包应用（如使用 PyInstaller）很重要
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        try:
            os.chdir(application_path)
            print(f"检测到打包环境，当前目录已设置为: {application_path}")
        except Exception as cd_err:
             print(f"警告：无法切换目录到 {application_path}: {cd_err}")

    # 确保在 Windows 等平台上多进程正常工作
    multiprocessing.freeze_support() # <--- 支持冻结环境下的多进程

    main()

    print("\n处理完成。按 Enter 键退出...")
    try:
        input()
    except EOFError:
        pass
