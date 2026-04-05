"""
本地数据源实现
从 videos/ 文件夹读取 txt 文件获取视频信息
"""

import os
from datetime import datetime, date
from typing import List, Optional
from pathlib import Path

from .data_source import VideoDataSource, VideoInfo
from conf import BASE_DIR
from utils.match_utils import (
    remove_date_prefix,
    calculate_similarity,
    select_best_matching_video
)


class LocalDataSource(VideoDataSource):
    """本地数据源（从 txt 文件读取）"""
    
    def __init__(self, config: Optional[dict] = None):
        self.videos_dir = Path(BASE_DIR) / "videos"
        self.config = config or {}
        
        # 从配置获取默认发布时间
        publish_times = self.config.get('publish_times', ['10:00'])
        self.default_publish_hour = int(publish_times[0].split(':')[0]) if publish_times else 10
        self.default_publish_minute = int(publish_times[0].split(':')[1]) if publish_times and ':' in publish_times[0] else 0
        
        # 从配置获取默认发布日期
        self.config_publish_date = self._get_config_publish_date()
    
    def _get_config_publish_date(self) -> datetime:
        """从 config.json 获取发布日期作为默认日期"""
        publish_date_str = self.config.get('publish_date')
        if publish_date_str:
            try:
                return datetime.strptime(publish_date_str, "%Y-%m-%d")
            except ValueError:
                pass
        return datetime.now()
    
    def extract_date_from_folder(self, folder_name: str) -> Optional[datetime]:
        """从文件夹名中提取日期 (YYMMDD)"""
        import re
        match = re.match(r'^(\d{6})', folder_name)
        if not match:
            return None
        
        date_str = match.group(1)
        try:
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return datetime(year, month, day)
        except (ValueError, IndexError):
            return None
    
    def _select_best_matching_video(self, video_files: List[Path], folder_name: str) -> Optional[Path]:
        """从多个视频文件中选择与文件夹名最匹配的那个（使用工具函数）"""
        best_match, _ = select_best_matching_video(video_files, folder_name, verbose=True)
        return best_match
    
    def _get_folder_videos(self, folder_path: Path) -> Optional[VideoInfo]:
        """从单个文件夹获取视频信息，支持多视频智能匹配"""
        # 查找视频文件
        video_files = list(folder_path.glob("*.mp4"))
        if not video_files:
            return None
        
        # 【新增】智能选择最匹配的视频
        video_file = self._select_best_matching_video(video_files, folder_path.name)
        
        # 查找文本文件
        txt_files = list(folder_path.glob("*.txt"))
        if txt_files:
            with open(txt_files[0], 'r', encoding='utf-8') as f:
                title = f.readline().strip()
                # 剩余的作为描述（不含标题行）
                remaining = f.read().strip()
                # 最后一行可能是标签
                lines = remaining.split('\n')
                if lines and lines[-1].startswith('#'):
                    tags = lines[-1]
                    description = '\n'.join(lines[:-1])
                else:
                    tags = ""
                    description = remaining
        else:
            title = video_file.stem
            description = ""
            tags = ""
        
        # 查找封面图
        cover_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.jpeg")) + list(folder_path.glob("*.png"))
        cover_path = str(cover_files[0]) if cover_files else None
        
        # 获取发布日期
        folder_date = self.extract_date_from_folder(folder_path.name)
        if folder_date:
            publish_date = folder_date.replace(
                hour=self.default_publish_hour,
                minute=self.default_publish_minute
            )
        else:
            publish_date = self.config_publish_date.replace(
                hour=self.default_publish_hour,
                minute=self.default_publish_minute
            )
        
        return VideoInfo(
            title=title,
            short_title=title,
            description=description,
            tags=tags,
            video_path=str(video_file),
            cover_path=cover_path,
            publish_date=publish_date,
            collections=[]  # 本地模式默认空合集
        )
    
    def get_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """获取本地视频列表"""
        if not self.videos_dir.exists():
            return []
        
        videos = []
        for folder in self.videos_dir.iterdir():
            if not folder.is_dir():
                continue
            
            # 获取文件夹日期
            folder_date = self.extract_date_from_folder(folder.name)
            if not folder_date:
                folder_date = self.config_publish_date
            
            # 日期范围筛选
            if date_range:
                start_date, end_date = date_range
                if not (start_date <= folder_date.date() <= end_date):
                    continue
            
            video_info = self._get_folder_videos(folder)
            if video_info:
                videos.append(video_info)
        
        # 按日期排序
        videos.sort(key=lambda x: x.publish_date)
        return videos
    
    def get_videos_count(self, date_range: Optional[Tuple[date, date]] = None) -> int:
        """获取视频数量"""
        return len(self.get_videos(date_range))


if __name__ == "__main__":
    # 测试代码
    source = LocalDataSource()
    videos = source.get_videos()
    print(f"找到 {len(videos)} 个视频:")
    for v in videos:
        print(f"- {v.title} ({v.publish_date.date()})")
