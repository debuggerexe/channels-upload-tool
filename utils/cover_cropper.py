"""
封面图片裁剪工具
用于将封面图裁剪为微信视频号支持的3:4比例
"""

from PIL import Image
import os


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

