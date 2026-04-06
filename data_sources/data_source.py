"""
数据源抽象基类模块
支持本地 txt 和 Notion 云端两种数据源
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Tuple, Optional
from pathlib import Path


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
