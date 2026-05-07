#!/usr/bin/env python3
"""
Bilibili 视频批量自动上传工具
支持本地、Notion、飞书三种数据源
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import time

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from conf import BASE_DIR
from data_sources.local_data_source import LocalDataSource
from data_sources.notion_data_source import NotionDataSource
from data_sources.feishu_data_source import FeishuDataSource
from uploader.bilibili_uploader.main import BilibiliVideo, ensure_login, extract_keys_from_json, random_emoji
from utils.constant import BILIBILI_ACCOUNT_FILE
from utils.output_utils import (
    header, success, error, warning, info,
    result_summary, mode_badge, print_final_summary
)
from utils.text_utils import parse_publish_date
from utils.log import bilibili_logger


class BilibiliVideoUploader:
    """Bilibili 视频上传管理器"""
    
    def __init__(
        self,
        mode: str,
        copyright_type: int = 1,
        date_range: Optional[tuple] = None,
        publish_type: str = "1",
        no_interactive: bool = False
    ):
        """
        初始化 Bilibili 视频上传管理器
        
        Args:
            mode: 数据源模式 (local/notion/feishu)
            copyright_type: 版权类型，1=自制，2=转载
            date_range: 日期范围筛选 (start_date, end_date)
            publish_type: 发布类型，"1"=定时发布，"2"=立即发布
            no_interactive: 是否非交互模式
        """
        self.mode = mode
        self.copyright_type = copyright_type
        self.date_range = date_range
        self.publish_type = publish_type
        self.no_interactive = no_interactive
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化数据源
        self.data_source = self._init_data_source()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        config_path = Path(BASE_DIR) / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _init_data_source(self):
        """初始化数据源"""
        if self.mode == "local":
            return LocalDataSource()
        elif self.mode == "notion":
            return NotionDataSource(self.config)
        elif self.mode == "feishu":
            return FeishuDataSource(self.config)
        else:
            raise ValueError(f"不支持的数据源模式: {self.mode}")
    
    async def _ensure_login(self):
        """确保已登录"""
        try:
            await ensure_login(BILIBILI_ACCOUNT_FILE)
        except ValueError as e:
            error(str(e))
            sys.exit(1)
    
    def get_videos(self) -> List:
        """获取待上传视频列表"""
        header("获取视频列表", icon="📋")
        
        if self.mode == "local":
            videos = self.data_source.get_videos(self.date_range)
        else:
            # Notion/飞书使用混合模式
            videos = self.data_source.get_videos(self.date_range)
        
        info(f"共获取 {len(videos)} 个视频")
        return videos
    
    async def upload_videos(self, videos: List) -> tuple:
        """
        上传视频列表
        
        Returns:
            (成功列表, 失败列表)
        """
        success_videos = []
        failed_videos = []
        
        header("开始上传视频", icon="⬆️")
        
        for i, video_info in enumerate(videos, 1):
            info(f"[{i}/{len(videos)}] 正在上传: {video_info.name_for_match}")
            
            try:
                # 准备发布日期
                if self.publish_type == "1" and video_info.publish_date:
                    # 定时发布
                    publish_date = video_info.publish_date
                else:
                    # 立即发布
                    publish_date = None
                
                # 准备标题（添加随机emoji避免重复）
                title = video_info.title or video_info.name_for_match
                # B站不允许相同标题的视频，添加随机emoji
                title = title + random_emoji()
                
                # 准备标签
                tags = []
                if video_info.tags:
                    # 将逗号分隔的标签转换为列表
                    tags = [t.strip() for t in video_info.tags.replace("，", ",").split(",") if t.strip()]
                if not tags:
                    # 如果没有标签，使用标题关键词作为标签
                    tags = ["B站", "视频"]
                
                # 确定类型（自制/转载）
                # 优先使用数据源中的video_type字段，其次使用命令行参数
                video_type = getattr(video_info, 'video_type', None)
                if video_type:
                    copyright_type = 1 if video_type == "自制" else 2
                else:
                    copyright_type = self.copyright_type
                
                # 【修复】定义上传成功回调函数，用于更新数据源状态
                def on_upload_success():
                    """上传成功后的回调，更新数据源状态"""
                    if hasattr(self.data_source, 'update_video_status'):
                        try:
                            record_id = getattr(video_info, 'notion_page_id', None) or \
                                       getattr(video_info, 'record_id', None)
                            if record_id:
                                self.data_source.update_video_status(
                                    record_id,
                                    "已发布",
                                    platform="bilibili"
                                )
                                info(f"  ✓ 已更新数据源状态: {video_info.name_for_match} -> 已发布")
                        except Exception as e:
                            warning(f"  ⚠️ 更新数据源状态失败: {e}")
                
                # 创建上传任务，传入回调
                bilibili_video = BilibiliVideo(
                    title=title,
                    file_path=video_info.video_path,
                    tags=tags,
                    publish_date=publish_date,
                    description=video_info.description or title,
                    copyright=copyright_type,
                    account_file=BILIBILI_ACCOUNT_FILE,
                    cover_path=video_info.cover_path,
                    on_upload_success=on_upload_success  # 【新增】传入回调
                )
                
                # 执行上传
                result = await bilibili_video.upload()
                
                if result:
                    success_videos.append(video_info)
                    success(f"上传成功: {video_info.name_for_match}")
                    # 回调已在上传器内部调用，无需重复更新状态
                else:
                    failed_videos.append(video_info)
                    error(f"上传失败: {video_info.name_for_match}")
                
                # 上传间隔，避免触发限制
                if i < len(videos):
                    info("等待 30 秒后继续...")
                    time.sleep(30)
                    
            except Exception as e:
                failed_videos.append(video_info)
                error(f"上传异常: {video_info.name_for_match}, 错误: {e}")
                bilibili_logger.exception(f"上传视频时发生异常: {e}")
        
        return success_videos, failed_videos
    
    async def run(self):
        """执行上传流程"""
        mode_badge("Bilibili", source=self.mode.upper())
        
        # 确保已登录
        await self._ensure_login()
        
        # 获取视频
        videos = self.get_videos()
        
        if not videos:
            warning("没有找到待上传的视频")
            return
        
        # 显示视频列表
        header(f"待上传视频列表 ({len(videos)} 个)", icon="📋")
        for v in videos:
            date_str = v.publish_date.strftime("%Y-%m-%d %H:%M") if v.publish_date else "立即发布"
            info(f"  • {v.name_for_match} [{date_str}]")
        
        # 交互确认
        if not self.no_interactive:
            response = input("\n是否开始上传? (y/n): ")
            if response.lower() != "y":
                info("已取消上传")
                return
        
        # 执行上传
        success_videos, failed_videos = await self.upload_videos(videos)
        
        # 打印结果
        print_final_summary(success_videos, failed_videos)


def parse_date_range(date_range_str: Optional[str]) -> Optional[tuple]:
    """
    解析日期范围字符串
    
    格式: "YYYY-MM-DD,YYYY-MM-DD"
    """
    if not date_range_str:
        return None
    
    try:
        parts = date_range_str.split(",")
        if len(parts) != 2:
            return None
        
        start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
        end_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
        
        return (start_date, end_date)
    except ValueError:
        return None




async def main():
    parser = argparse.ArgumentParser(
        description="Bilibili 视频批量自动上传工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 本地模式上传
  python upload_bilibili_videos.py --mode local
  
  # Notion混合模式
  python upload_bilibili_videos.py --mode notion
  
  # 飞书混合模式（转载视频）
  python upload_bilibili_videos.py --mode feishu --copyright 2
"""
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["local", "notion", "feishu"],
        default="local",
        help="数据源模式: local=本地, notion=Notion, feishu=飞书 (默认: local)"
    )
    
    
    parser.add_argument(
        "--copyright",
        type=int,
        choices=[1, 2],
        default=1,
        help="版权类型: 1=自制, 2=转载 (默认: 1)"
    )
    
    parser.add_argument(
        "--date-range",
        type=str,
        help="日期范围筛选，格式: YYYY-MM-DD,YYYY-MM-DD"
    )
    
    parser.add_argument(
        "--publish-type",
        type=str,
        choices=["1", "2"],
        default="1",
        help="发布方式: 1=按数据源时间定时发布, 2=立即发布 (默认: 1)"
    )
    
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="非交互模式，自动确认上传"
    )
    
    args = parser.parse_args()
    
    # 解析日期范围
    date_range = parse_date_range(args.date_range)
    
    # 创建上传管理器
    uploader = BilibiliVideoUploader(
        mode=args.mode,
        copyright_type=args.copyright,
        date_range=date_range,
        publish_type=args.publish_type,
        no_interactive=args.no_interactive
    )
    
    # 执行上传
    await uploader.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
