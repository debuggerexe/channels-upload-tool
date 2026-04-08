"""
文件下载工具模块
提供通用的异步文件下载功能，支持重试机制和进度回调
"""

import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse
from conf import BASE_DIR


async def download_file_async(
    file_url: str,
    filename: str,
    temp_subdir: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    max_retries: int = 3,
    custom_headers: Optional[dict] = None,
    timeout_seconds: int = 300
) -> str:
    """
    从 URL 异步下载文件到临时目录（带重试机制）
    
    Args:
        file_url: 文件下载链接
        filename: 保存的文件名
        temp_subdir: 临时文件子目录名（如 'notion_downloads' 或 'feishu_downloads'）
        progress_callback: 可选的进度回调函数，接收 (filename, progress_percent)
        max_retries: 最大重试次数
        custom_headers: 可选的自定义请求头
        timeout_seconds: 下载超时时间（秒）
        
    Returns:
        本地临时文件路径
        
    Raises:
        Exception: 下载失败（已重试 max_retries 次）
    """
    # 创建临时目录
    temp_dir = Path(BASE_DIR) / "temp" / temp_subdir
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    local_path = temp_dir / filename
    
    # 准备请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    if custom_headers:
        headers.update(custom_headers)
    
    # 重试循环
    for attempt in range(1, max_retries + 1):
        print(f"⬇️ 开始下载: {filename} (尝试 {attempt}/{max_retries})")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    file_url, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"   ❌ HTTP {response.status}: {error_text[:200]}")
                        raise Exception(f"下载失败，HTTP {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                progress_callback(filename, progress)
            
            # 验证文件大小
            if local_path.exists() and local_path.stat().st_size > 0:
                print(f"✅ 下载完成: {local_path} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)")
                return str(local_path)
            else:
                raise Exception("下载文件为空")
                
        except Exception as e:
            print(f"❌ 下载失败 {filename} (尝试 {attempt}/{max_retries}): {e}")
            # 清理失败的文件
            if local_path.exists():
                local_path.unlink()
            
            if attempt < max_retries:
                # 指数退避等待
                wait_time = 2 ** attempt
                print(f"   ⏳ {wait_time}秒后重试...")
                await asyncio.sleep(wait_time)
            else:
                # 所有重试都失败
                raise Exception(f"下载失败，已重试{max_retries}次: {e}")
    
    raise Exception("下载失败，超出最大重试次数")


def generate_filename_from_url(url: str, name_for_match: str, publish_date, default_name: str = 'file') -> tuple:
    """
    从 URL 生成文件名
    
    Args:
        url: 文件URL
        name_for_match: 用于匹配的名称
        publish_date: 发布日期（用于文件名时间戳）
        default_name: 默认文件名前缀
        
    Returns:
        tuple: (filename_with_ext, filename_without_ext)
    """
    parsed_url = urlparse(url)
    url_name = Path(parsed_url.path).stem or default_name
    url_ext = Path(parsed_url.path).suffix or '.jpg'
    
    date_str = publish_date.strftime('%Y%m%d') if publish_date else 'unknown'
    filename = f"{name_for_match or default_name}_{date_str}{url_ext}"
    
    return filename, url_name


def generate_video_filename(name_for_match: str, publish_date) -> str:
    """
    生成视频文件名
    
    Args:
        name_for_match: 用于匹配的名称
        publish_date: 发布日期
        
    Returns:
        带时间戳的视频文件名（.mp4）
    """
    date_str = publish_date.strftime('%Y%m%d') if publish_date else 'unknown'
    return f"{name_for_match or 'video'}_{date_str}.mp4"


def generate_cover_filename(name_for_match: str, publish_date, url: Optional[str] = None) -> str:
    """
    生成封面文件名
    
    Args:
        name_for_match: 用于匹配的名称
        publish_date: 发布日期
        url: 可选的封面URL（用于获取扩展名）
        
    Returns:
        带时间戳的封面文件名
    """
    date_str = publish_date.strftime('%Y%m%d') if publish_date else 'unknown'
    
    if url:
        parsed_url = urlparse(url)
        ext = Path(parsed_url.path).suffix or '.jpg'
    else:
        ext = '.jpg'
    
    return f"{name_for_match or 'cover'}_{date_str}{ext}"
