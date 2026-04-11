"""
封面图片裁剪工具
用于将封面图裁剪为微信视频号支持的3:4比例
"""

from PIL import Image
import os
from pathlib import Path


def crop_cover_to_34(image_path: str, position: str = 'middle') -> str:
    """
    将封面图裁剪为3:4比例
    
    逻辑：
    - 宽图（16:9, 1:1等宽高比 >= 0.75的）：不需要裁剪，原样上传
    - 高图（9:16等宽高比 < 0.75的）：需要裁剪为3:4比例
    
    Args:
        image_path: 原图路径
        position: 裁剪位置 ('top', 'middle', 'bottom')
                  - top: 保留顶部区域
                  - middle: 保留中间区域  
                  - bottom: 保留底部区域
    
    Returns:
        裁剪后图片的路径（如需裁剪则保存到视频所在文件夹，如无需裁剪则返回原路径）
    """
    if not image_path or not os.path.exists(image_path):
        return image_path
    
    try:
        # 打开图片
        with Image.open(image_path) as img:
            width, height = img.size
            
            # 计算当前宽高比
            current_ratio = width / height
            target_ratio = 3 / 4  # 0.75
            
            # 宽图判断：宽高比大于等于0.75（如16:9约为1.78，1:1等于1.0）
            # 高图判断：宽高比小于0.75（如9:16约为0.56）
            if current_ratio >= target_ratio:
                # 宽图（包括1:1, 16:9等），不需要裁剪
                return image_path
            
            # 高图需要裁剪：按宽度比例计算新的高度
            # 3:4 = width : new_height
            # new_height = width * 4 / 3
            new_height = int(width * 4 / 3)
            
            # 如果计算出的高度大于等于原高度，说明已经是高图但接近3:4，不需要裁剪
            if new_height >= height:
                return image_path
            
            # 根据位置计算裁剪区域
            if position == 'top':
                # 保留顶部：从顶部开始向下取new_height
                top = 0
                bottom = new_height
            elif position == 'bottom':
                # 保留底部：从底部向上取new_height
                bottom = height
                top = height - new_height
            else:  # middle
                # 保留中间
                top = (height - new_height) // 2
                bottom = top + new_height
            
            # 裁剪 (left, top, right, bottom)
            cropped = img.crop((0, top, width, bottom))
            
            # 保存到视频所在文件夹（而不是临时目录）
            video_dir = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = os.path.splitext(image_path)[1].lower()
            
            # 生成裁剪后的文件名，添加 _crop 后缀
            if ext in ['.jpg', '.jpeg']:
                cropped_name = f"{base_name}_crop.jpg"
            else:
                cropped_name = f"{base_name}_crop.png"
            
            cropped_path = os.path.join(video_dir, cropped_name)
            
            # 保存裁剪后的图片
            if ext in ['.jpg', '.jpeg']:
                cropped.save(cropped_path, 'JPEG', quality=95)
            else:
                cropped.save(cropped_path, 'PNG')
            
            return cropped_path
            
    except Exception as e:
        print(f"[CoverCropper] 裁剪封面失败: {e}")
        return image_path


def is_high_image(image_path: str) -> bool:
    """
    检查图片是否是高图（宽高比小于3:4，如9:16）
    
    Args:
        image_path: 图片路径
    
    Returns:
        True 如果是高图（需要裁剪）
    """
    if not image_path or not os.path.exists(image_path):
        return False
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = width / height
            return ratio < 0.75  # 小于3:4比例是高图
    except:
        return False


def is_34_ratio(image_path: str) -> bool:
    """
    检查图片是否已是3:4比例（或接近）
    
    Args:
        image_path: 图片路径
    
    Returns:
        True 如果是3:4比例（允许0.01误差）
    """
    if not image_path or not os.path.exists(image_path):
        return False
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = width / height
            return abs(ratio - 0.75) < 0.01
    except:
        return False


def prepare_douyin_covers(image_path: str, position: str = 'middle') -> tuple:
    """
    为抖音准备双封面（竖封面 3:4 + 横封面 4:3）
    
    Args:
        image_path: 原图路径
        position: 裁剪位置 ('top', 'middle', 'bottom', 'left', 'right')，默认'middle'
                  - top: 保留顶部区域
                  - middle: 居中裁剪
                  - bottom: 保留底部区域
                  - left: 从左侧裁剪（16:9横图）
                  - right: 从右侧裁剪（16:9横图）
    
    Returns:
        (竖封面路径, 横封面路径, 临时文件列表) - 如果裁剪失败则返回原图路径
    """
    if not image_path or not os.path.exists(image_path):
        return image_path, image_path
    
    # middle时不裁剪，直接使用原图
    if position == 'middle':
        return image_path, image_path
    
    temp_files = []  # 跟踪生成的临时文件
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = width / height
            
            # 目标比例
            ratio_34 = 3 / 4   # 0.75
            ratio_43 = 4 / 3   # 1.333
            
            # 判断原图比例
            is_34 = abs(ratio - ratio_34) < 0.01  # 接近3:4
            is_high = ratio < ratio_34  # 高图(9:16等)
            
            video_dir = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = os.path.splitext(image_path)[1].lower()
            
            # 生成文件名
            suffix_34 = f"_{position}_34" if position != 'middle' else "_34"
            suffix_43 = f"_{position}_43" if position != 'middle' else "_43"
            
            if ext in ['.jpg', '.jpeg']:
                path_34 = os.path.join(video_dir, f"{base_name}{suffix_34}.jpg")
                path_43 = os.path.join(video_dir, f"{base_name}{suffix_43}.jpg")
            else:
                path_34 = os.path.join(video_dir, f"{base_name}{suffix_34}.png")
                path_43 = os.path.join(video_dir, f"{base_name}{suffix_43}.png")
            
            # 情况1: 原图是3:4比例
            if is_34:
                # 竖封面直接使用原图
                vertical_path = image_path
                
                # 横封面从3:4中裁剪出4:3（保持宽度，裁剪高度）
                # 4:3高度 = width / (4/3) = width * 3 / 4
                new_height_43 = int(width * 3 / 4)
                
                if position == 'top':
                    top, bottom = 0, new_height_43
                elif position == 'bottom':
                    top, bottom = height - new_height_43, height
                else:  # middle
                    top = (height - new_height_43) // 2
                    bottom = top + new_height_43
                
                horizontal_img = img.crop((0, top, width, bottom))
                if ext in ['.jpg', '.jpeg']:
                    horizontal_img.save(path_43, 'JPEG', quality=95)
                else:
                    horizontal_img.save(path_43, 'PNG')
                horizontal_path = path_43
                temp_files.append(path_43)
            
            # 情况2: 原图是高图(9:16等，ratio < 0.75)
            elif is_high:
                # 竖封面：裁剪为3:4
                new_height_34 = int(width * 4 / 3)
                
                if position == 'top':
                    top_34, bottom_34 = 0, new_height_34
                elif position == 'bottom':
                    top_34, bottom_34 = height - new_height_34, height
                else:  # middle
                    top_34 = (height - new_height_34) // 2
                    bottom_34 = top_34 + new_height_34
                
                vertical_img = img.crop((0, top_34, width, bottom_34))
                if ext in ['.jpg', '.jpeg']:
                    vertical_img.save(path_34, 'JPEG', quality=95)
                else:
                    vertical_img.save(path_34, 'PNG')
                vertical_path = path_34
                temp_files.append(path_34)
                
                # 横封面：从竖封面(3:4)中裁剪出4:3
                # 竖封面已经是3:4，从中取4:3区域（保持宽度，裁剪高度）
                v_width, v_height = vertical_img.size
                new_height_43 = int(v_width * 3 / 4)
                
                if position == 'top':
                    top_43, bottom_43 = 0, new_height_43
                elif position == 'bottom':
                    top_43, bottom_43 = v_height - new_height_43, v_height
                else:  # middle
                    top_43 = (v_height - new_height_43) // 2
                    bottom_43 = top_43 + new_height_43
                
                horizontal_img = vertical_img.crop((0, top_43, v_width, bottom_43))
                if ext in ['.jpg', '.jpeg']:
                    horizontal_img.save(path_43, 'JPEG', quality=95)
                else:
                    horizontal_img.save(path_43, 'PNG')
                horizontal_path = path_43
                temp_files.append(path_43)
            
            # 情况3: 原图是其他比例(宽图如16:9)
            else:
                # 宽图处理：保持高度不变，从左侧/右侧/中间裁剪宽度
                # 竖封面 3:4：目标宽度 = height * 3 / 4
                # 横封面 4:3：目标宽度 = height * 4 / 3
                
                target_width_34 = int(height * 3 / 4)
                target_width_43 = int(height * 4 / 3)
                
                # 竖封面 3:4 裁剪
                if position == 'left':
                    left_34, right_34 = 0, min(target_width_34, width)
                elif position == 'right':
                    left_34, right_34 = max(0, width - target_width_34), width
                else:  # middle, top, bottom 都默认居中裁剪宽度
                    left_34 = max(0, (width - target_width_34) // 2)
                    right_34 = min(width, left_34 + target_width_34)
                
                if right_34 - left_34 > 10:  # 确保有裁剪空间
                    vertical_img = img.crop((left_34, 0, right_34, height))
                    if ext in ['.jpg', '.jpeg']:
                        vertical_img.save(path_34, 'JPEG', quality=95)
                    else:
                        vertical_img.save(path_34, 'PNG')
                    vertical_path = path_34
                else:
                    vertical_path = image_path
                
                # 横封面 4:3 裁剪（同样保持高度不变）
                if position == 'left':
                    left_43, right_43 = 0, min(target_width_43, width)
                elif position == 'right':
                    left_43, right_43 = max(0, width - target_width_43), width
                else:  # middle, top, bottom 都默认居中裁剪宽度
                    left_43 = max(0, (width - target_width_43) // 2)
                    right_43 = min(width, left_43 + target_width_43)
                
                if right_43 - left_43 > 10:
                    horizontal_img = img.crop((left_43, 0, right_43, height))
                    if ext in ['.jpg', '.jpeg']:
                        horizontal_img.save(path_43, 'JPEG', quality=95)
                    else:
                        horizontal_img.save(path_43, 'PNG')
                    horizontal_path = path_43
                    temp_files.append(path_43)
                else:
                    horizontal_path = image_path
            
            return vertical_path, horizontal_path, temp_files
            
    except Exception as e:
        print(f"[CoverCropper] 准备抖音封面失败: {e}")
        return image_path, image_path, []


def prepare_dual_covers(vertical_path: str, horizontal_path: str, position: str = 'middle') -> tuple:
    """
    【双封面模式】分别处理竖封面和横封面
    
    支持独立的竖封面和横封面图片，各自按需裁剪：
    - 竖封面：裁剪为 3:4 比例（支持 top/bottom/middle）
    - 横封面：裁剪为 4:3 比例（支持 left/right/middle）
    
    Args:
        vertical_path: 竖封面图片路径（优先用于竖封面上传）
        horizontal_path: 横封面图片路径（4:3，可选）
        position: 裁剪位置
            - 'top'/'bottom': 竖封面从顶部/底部裁剪
            - 'left'/'right': 横封面从左侧/右侧裁剪  
            - 'middle': 不裁剪，直接使用原图
    
    Returns:
        (处理后的竖封面路径, 处理后的横封面路径, 临时文件列表)
    """
    from PIL import Image
    
    temp_files = []  # 跟踪生成的临时文件
    
    # 处理竖封面（裁剪为3:4）
    processed_vertical = vertical_path
    if vertical_path and os.path.exists(vertical_path) and position != 'middle':
        try:
            with Image.open(vertical_path) as img:
                width, height = img.size
                ratio = width / height
                target_ratio = 3 / 4  # 0.75
                
                # 只有需要裁剪时才处理
                if abs(ratio - target_ratio) > 0.01:
                    new_height = int(width * 4 / 3)
                    
                    if position == 'top':
                        top, bottom = 0, min(new_height, height)
                    elif position == 'bottom':
                        top, bottom = max(0, height - new_height), height
                    else:
                        top = max(0, (height - new_height) // 2)
                        bottom = min(height, top + new_height)
                    
                    if bottom - top > 10:
                        video_dir = os.path.dirname(vertical_path)
                        base_name = os.path.splitext(os.path.basename(vertical_path))[0]
                        ext = os.path.splitext(vertical_path)[1].lower()
                        suffix = f"_{position}_34" if position != 'middle' else "_34"
                        
                        if ext in ['.jpg', '.jpeg']:
                            output_path = os.path.join(video_dir, f"{base_name}{suffix}.jpg")
                            img.crop((0, top, width, bottom)).save(output_path, 'JPEG', quality=95)
                        else:
                            output_path = os.path.join(video_dir, f"{base_name}{suffix}.png")
                            img.crop((0, top, width, bottom)).save(output_path, 'PNG')
                        
                        processed_vertical = output_path
                        temp_files.append(output_path)
        except Exception as e:
            print(f"[CoverCropper] 竖封面裁剪失败: {e}")
    
    # 处理横封面（裁剪为4:3）
    processed_horizontal = horizontal_path
    if horizontal_path and os.path.exists(horizontal_path) and position != 'middle':
        try:
            with Image.open(horizontal_path) as img:
                width, height = img.size
                ratio = width / height
                target_ratio = 4 / 3  # 1.333
                
                # 只有需要裁剪时才处理
                if abs(ratio - target_ratio) > 0.01:
                    new_width = int(height * 4 / 3)
                    
                    if position == 'left':
                        left, right = 0, min(new_width, width)
                    elif position == 'right':
                        left, right = max(0, width - new_width), width
                    else:
                        left = max(0, (width - new_width) // 2)
                        right = min(width, left + new_width)
                    
                    if right - left > 10:
                        video_dir = os.path.dirname(horizontal_path)
                        base_name = os.path.splitext(os.path.basename(horizontal_path))[0]
                        ext = os.path.splitext(horizontal_path)[1].lower()
                        suffix = f"_{position}_43" if position != 'middle' else "_43"
                        
                        if ext in ['.jpg', '.jpeg']:
                            output_path = os.path.join(video_dir, f"{base_name}{suffix}.jpg")
                            img.crop((left, 0, right, height)).save(output_path, 'JPEG', quality=95)
                        else:
                            output_path = os.path.join(video_dir, f"{base_name}{suffix}.png")
                            img.crop((left, 0, right, height)).save(output_path, 'PNG')
                        
                        processed_horizontal = output_path
                        temp_files.append(output_path)
        except Exception as e:
            print(f"[CoverCropper] 横封面裁剪失败: {e}")
    
    return processed_vertical, processed_horizontal, temp_files


def cleanup_temp_covers(temp_files: list):
    """
    清理临时裁剪的封面文件
    
    Args:
        temp_files: 临时文件路径列表
    """
    if not temp_files:
        return
    
    cleaned = []
    for temp_path in temp_files:
        if not temp_path:
            continue
        try:
            temp_file = Path(temp_path)
            if temp_file.exists():
                temp_file.unlink()
                cleaned.append(temp_file.name)
        except Exception:
            pass
    
    if cleaned:
        print(f"  🗑️  已清理临时封面: {', '.join(cleaned)}")


def detect_cover_type(image_path: str) -> str:
    """
    检测封面图片类型（竖/横/正方）
    
    Args:
        image_path: 图片路径
    
    Returns:
        'vertical' (竖图, ratio < 1.0)
        'horizontal' (横图, ratio > 1.0)  
        'square' (正方, ratio ≈ 1.0)
        'invalid' (无效路径)
    """
    from PIL import Image
    
    if not image_path or not os.path.exists(image_path):
        return 'invalid'
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = width / height
            
            if abs(ratio - 1.0) < 0.01:
                return 'square'
            elif ratio < 1.0:
                return 'vertical'
            else:
                return 'horizontal'
    except Exception as e:
        print(f"[CoverCropper] 检测封面类型失败: {e}")
        return 'invalid'
