"""
数据源抽象基类模块
支持本地 txt 和 Notion 云端两种数据源
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Tuple, Optional
from pathlib import Path
from urllib.parse import urlparse
from utils.match_utils import match_local_video, match_local_cover
import aiohttp


@dataclass
class VideoInfo:
    """视频信息数据结构"""
    title: str                    # 视频标题（对应 Notion 标题字段）
    short_title: str              # 短标题（对应 Notion 短标题字段，16字以内）
    description: str                # 视频描述（不含标签）
    tags: str                     # 话题标签行
    video_path: str               # 本地视频文件路径
    cover_path: Optional[str]     # 本地封面图路径
    publish_date: datetime        # 发布日期
    collections: List[str]        # 合集名称列表（支持多选）
    original_declaration: bool = True  # 声明原创
    cover_position: str = "middle"    # 封面调整位置 (top/middle/bottom)
    location: str = "平台默认"     # 位置设置："不显示位置" | "平台默认"
    name_for_match: str = ""      # 用于匹配本地视频的Name字段（如 我的视频名称）
    folder_name: str = ""         # 文件夹名称（用于日志显示）
    
    # 云端模式新增字段
    source_mode: str = "local"     # 数据来源模式："local" | "notion"
    video_url: Optional[str] = None      # 云端模式下视频文件的URL
    cover_url: Optional[str] = None      # 云端模式下封面图片的URL
    temp_local_video_path: Optional[str] = None  # 从云端下载后的本地视频临时路径
    temp_local_cover_path: Optional[str] = None  # 从云端下载后的本地封面临时路径
    notion_page_id: Optional[str] = None  # Notion页面ID，用于更新状态
    publish_mode: Optional[str] = None  # 发布方式（"1"=定时发布, "2"=保存草稿）


class VideoDataSource(ABC):
    """视频数据源抽象基类"""
    
    def __init__(self):
        self.temp_dir = None
        self.videos_dir = None
    
    @abstractmethod
    def get_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """
        获取视频列表
        
        Args:
            date_range: 可选的日期范围 (start_date, end_date)
        
        Returns:
            VideoInfo 列表
        """
        pass
    
    @abstractmethod
    def get_videos_count(self, date_range: Optional[Tuple[date, date]] = None) -> int:
        """
        获取视频数量（用于预览）
        
        Args:
            date_range: 可选的日期范围
        
        Returns:
            视频数量
        """
        pass
    
    async def download_video_files(self, videos: List[VideoInfo], progress_callback=None) -> List[VideoInfo]:
        """
        【公共方法】批量下载云端视频文件到本地临时目录
        【混合模式】优先使用本地 videos/ 文件夹中的文件，没有则从云端下载
        
        Args:
            videos: VideoInfo 列表（包含 video_url 和 cover_url）
            progress_callback: 可选的进度回调函数
            
        Returns:
            更新后的 VideoInfo 列表（填充了 video_path 和 cover_path）
        """
        async def download_single_video(video: VideoInfo) -> VideoInfo:
            try:
                # 【本地优先】先检查 videos/ 文件夹是否有匹配的文件
                local_video_path = match_local_video(video.name_for_match, self.videos_dir)
                local_cover_path = None
                
                if local_video_path:
                    # 找到本地视频，直接使用
                    video.video_path = str(local_video_path)
                    print(f"📁 使用本地视频: {local_video_path.name}")
                    
                    # 同时检查本地封面
                    local_cover_path = match_local_cover(local_video_path)
                    if local_cover_path:
                        video.cover_path = str(local_cover_path)
                        print(f"📁 使用本地封面: {Path(local_cover_path).name}")
                else:
                    # 本地没有，从云端下载视频
                    if video.video_url:
                        video_filename = f"{video.name_for_match or 'video'}_{video.publish_date.strftime('%Y%m%d')}.mp4"
                        video.temp_local_video_path = await self._download_file_async(
                            video.video_url, 
                            video_filename,
                            progress_callback,
                            max_retries=3
                        )
                        # 更新 video_path 为下载后的本地路径
                        video.video_path = video.temp_local_video_path
                
                # 如果本地没有封面，尝试从云端下载
                if not video.cover_path and video.cover_url:
                    try:
                        parsed_url = urlparse(video.cover_url)
                        cover_name = Path(parsed_url.path).stem or 'cover'
                        cover_ext = Path(parsed_url.path).suffix or '.jpg'
                        cover_filename = f"{video.name_for_match or 'cover'}_{video.publish_date.strftime('%Y%m%d')}{cover_ext}"
                        video.temp_local_cover_path = await self._download_file_async(
                            video.cover_url,
                            cover_filename,
                            progress_callback,
                            max_retries=2  # 封面下载重试次数较少
                        )
                        # 更新 cover_path 为下载后的本地路径
                        video.cover_path = video.temp_local_cover_path
                    except Exception as cover_error:
                        # 封面下载失败不影响视频上传
                        print(f"⚠️ 封面下载失败（将使用视频默认封面）: {cover_error}")
                        video.cover_url = None  # 清空封面URL，使用视频默认封面
                
                return video
                
            except Exception as e:
                print(f"❌ 处理失败 {video.name_for_match}: {e}")
                raise
        
        # 并发处理所有视频
        tasks = [download_single_video(v) for v in videos]
        processed_videos = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉失败的
        successful_videos = []
        for v in processed_videos:
            if isinstance(v, Exception):
                print(f"⚠️ 跳过失败的视频")
                continue
            successful_videos.append(v)
        
        # 统计本地和云端
        local_count = sum(1 for v in successful_videos if "videos/" in str(v.video_path))
        cloud_count = len(successful_videos) - local_count
        print(f"✅ 处理完成: {local_count} 个本地视频, {cloud_count} 个云端下载")
        return successful_videos
    
    async def _download_file_async(self, url: str, filename: str, progress_callback=None, max_retries: int = 3) -> str:
        """
        【公共方法】异步下载文件
        
        Args:
            url: 文件URL
            filename: 保存的文件名
            progress_callback: 进度回调函数
            max_retries: 最大重试次数
            
        Returns:
            下载后的本地文件路径
        """
        # 确保临时目录存在
        if not self.temp_dir:
            from conf import BASE_DIR
            self.temp_dir = Path(BASE_DIR) / "temp" / f"{self.__class__.__name__.lower().replace('datasource', '')}_downloads"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = self.temp_dir / filename
        
        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                        if response.status != 200:
                            raise Exception(f"HTTP {response.status}")
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if progress_callback and total_size > 0:
                                        progress_callback(downloaded, total_size)
                
                return str(file_path)
                
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise Exception(f"下载失败，已重试{max_retries}次: {e}")
        
        raise Exception("下载失败，超出最大重试次数")
