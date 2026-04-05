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
    title: str                    # 视频标题（对应 Notion Cover 字段）
    short_title: str              # 短标题（对应 Notion Title 字段，可选）
    description: str              # 视频描述（不含标签）
    tags: str                     # 话题标签行
    video_path: str               # 本地视频文件路径
    cover_path: Optional[str]     # 本地封面图路径
    publish_date: datetime        # 发布日期
    collections: List[str]        # 合集名称列表（支持多选）


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
