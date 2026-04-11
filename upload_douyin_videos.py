#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频批量自动上传工具

支持三种数据源模式：
1. 本地模式 (--mode local): 从本地 videos/ 文件夹读取视频和 txt 元数据
2. Notion混合模式 (--mode notion): 从 Notion 获取元数据，优先匹配本地视频
3. 飞书混合模式 (--mode feishu): 从飞书多维表格获取元数据，优先匹配本地视频

用法：
    python upload_douyin_videos.py --mode local
    python upload_douyin_videos.py --mode notion --publish 1 --no-interactive
    python upload_douyin_videos.py --mode feishu

作者：AI Assistant
日期：2026-04-10
"""

import os
import re
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from conf import BASE_DIR
from uploader.douyin_uploader.main import DouYinVideo, douyin_setup, DOUYIN_ACCOUNT_FILE
from data_sources.data_source import VideoInfo
from utils.output_utils import (
    print_douyin_header, print_final_summary, print_data_source_header,
    success, error, warning, info,
    Colors
)


# ==================== 数据源导入 ====================
def get_data_source(mode: str, config: dict):
    """根据模式获取数据源实例"""
    if mode == 'local':
        from data_sources.local_data_source import LocalDataSource
        return LocalDataSource()
    elif mode == 'notion':
        from data_sources.notion_data_source import NotionDataSource
        return NotionDataSource(config)
    elif mode == 'feishu':
        from data_sources.feishu_data_source import FeishuDataSource
        return FeishuDataSource(config)
    else:
        raise ValueError(f"不支持的模式: {mode}")


# ==================== 配置文件加载 ====================
def load_config() -> dict:
    """加载配置文件"""
    config_path = Path(BASE_DIR) / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# ==================== Cookie 验证 ====================
async def ensure_login(account_file: str, no_interactive: bool = False) -> bool:
    """确保已登录，如有需要引导用户登录"""
    if not os.path.exists(account_file):
        if no_interactive:
            error(f"Cookie 文件不存在: {account_file}")
            info("请先运行: python examples/get_douyin_cookie.py")
            return False
        
        warning("Cookie 文件不存在，即将打开浏览器登录...")
        os.makedirs(os.path.dirname(account_file), exist_ok=True)
        return await douyin_setup(account_file, handle=True)
    
    # 验证 Cookie 有效性
    info("正在验证 Cookie...")
    return await douyin_setup(account_file, handle=not no_interactive)


# ==================== 视频上传 ====================
async def upload_single_video(
    video: VideoInfo,
    account_file: str,
    publish_mode: str = '1',
    verbose: bool = True,
    index: int = 1,
    total: int = 1
) -> bool:
    """
    上传单个视频到抖音

    Args:
        video: 视频信息对象
        account_file: Cookie 文件路径
        publish_mode: 发布模式 '1'=定时发布 '2'=保存草稿
        verbose: 是否打印详细信息
        index: 当前视频序号
        total: 视频总数

    Returns:
        True 表示上传成功
    """
    try:
        # 解析话题标签（从描述最后一行提取，只保留前5个）
        tags = []
        description_clean = video.description if hasattr(video, 'description') else ""
        if description_clean:
            lines = description_clean.strip().split('\n')
            # 移除描述中的标题（第一行如果等于title则删除，避免重复）
            if lines and video.title and lines[0].strip() == video.title.strip():
                lines = lines[1:]
            if lines:
                last_line = lines[-1].strip()
                # 如果最后一行以 # 开头，说明是标签行
                if last_line.startswith('#'):
                    # 提取所有 # 开头的标签
                    tag_matches = re.findall(r'#([^#\s]+)', last_line)
                    # 只保留前5个
                    tags = tag_matches[:5]
                    # 从描述中移除最后一行（标签行）
                    lines = lines[:-1]
            description_clean = '\n'.join(lines) if lines else ""

        # 确定发布时间 - 优先使用 video.publish_date
        publish_date = None
        if publish_mode == '1' and video.publish_date:
            publish_date = video.publish_date
            info(f"发布时间设定: {publish_date.strftime('%Y-%m-%d %H:%M')}")

        # 确定封面路径和裁剪位置
        cover_path = None
        if video.cover_path:
            cover_path = str(video.cover_path)
            info(f"使用封面: {cover_path}")
        
        # 确定横封面路径
        horizontal_cover_path = None
        if hasattr(video, 'horizontal_cover_path') and video.horizontal_cover_path:
            horizontal_cover_path = str(video.horizontal_cover_path)
            info(f"使用横封面: {horizontal_cover_path}")
        
        # 获取封面裁剪位置
        cover_position = "middle"
        if hasattr(video, 'cover_position') and video.cover_position:
            cover_position = video.cover_position
            info(f"封面裁剪位置: {cover_position}")

        # 创建上传实例
        app = DouYinVideo(
            title=video.title or "",
            file_path=str(video.video_path),
            tags=tags,
            publish_date=publish_date,
            account_file=account_file,
            thumbnail_path=cover_path,
            horizontal_thumbnail_path=horizontal_cover_path,
            location=video.location if hasattr(video, 'location') and video.location else "杭州市",
            sync_to_toutiao=True,
            description=description_clean,
            cover_position=cover_position,
            collections=video.collections if hasattr(video, 'collections') else None
        )

        # 执行上传（uploader 会在 finally 块中自动清理临时封面文件）
        upload_success = await app.main()
        
        return upload_success
        
    except Exception as e:
        if verbose:
            error(f"上传视频失败: {e}")
        return False


async def upload_videos_from_source(
    videos: List[VideoInfo],
    account_file: str,
    publish_mode: str = '1',
    data_source=None,
    index: int = 0,
    total: int = 0
) -> Dict[str, List[VideoInfo]]:
    """
    批量上传视频
    
    Args:
        videos: 视频信息列表
        account_file: Cookie 文件路径
        publish_mode: 发布模式
        data_source: 数据源实例（用于更新状态）
        
    Returns:
        {'success': [...], 'failed': [...]}
    """
    result = {'success': [], 'failed': []}
    
    total = len(videos)
    print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 开始批量上传，共 {total} 个视频{Colors.RESET}")
    
    for index, video in enumerate(videos, 1):
        print(f"\n{Colors.BRIGHT_BLUE}{Colors.BOLD}▶ [{index}/{total}] {video.name_for_match or video.title}{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")

        upload_success = await upload_single_video(video, account_file, publish_mode, True, index, total)
        
        if upload_success:
            result['success'].append(video)
            success(f"✅ 视频上传成功: {video.name_for_match or video.title}")
        else:
            result['failed'].append(video)
            error(f"❌ 视频上传失败: {video.name_for_match or video.title}")
        
        # 视频间间隔，避免触发风控
        if index < total:
            info("等待 3 秒后继续...")
            await asyncio.sleep(3)
    
    return result


def update_videos_publish_status(data_source, result: dict, source_name: str):
    """
    更新视频发布状态到数据源
    
    Args:
        data_source: 数据源实例
        result: 上传结果 {'success': [...], 'failed': [...]}
        source_name: 数据源名称（用于日志）
    """
    if not data_source:
        return
    
    print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 正在更新 {source_name} 发布状态...{Colors.RESET}")
    
    success_count = 0
    fail_count = 0
    
    # 标记成功的视频
    for video in result.get('success', []):
        try:
            if hasattr(video, 'notion_page_id') and video.notion_page_id:
                status_updated = data_source.update_video_status(video.notion_page_id, "已发布")
                if status_updated:
                    success(f"  ✅ {video.name_for_match} -> 已发布")
                    success_count += 1
                else:
                    warning(f"  ⚠️ {video.name_for_match} -> 状态更新失败")
            elif hasattr(video, 'feishu_record_id') and video.feishu_record_id:
                status_updated = data_source.update_video_status(video.feishu_record_id, "已发布")
                if status_updated:
                    success(f"  ✅ {video.name_for_match} -> 已发布")
                    success_count += 1
                else:
                    warning(f"  ⚠️ {video.name_for_match} -> 状态更新失败")
        except Exception as e:
            error(f"  ❌ 更新状态失败: {video.name_for_match} - {e}")
    
    # 标记失败的视频
    for video in result.get('failed', []):
        try:
            if hasattr(video, 'notion_page_id') and video.notion_page_id:
                status_updated = data_source.update_video_status(video.notion_page_id, "发布失败")
                if status_updated:
                    error(f"  ❌ {video.name_for_match} -> 发布失败")
                    fail_count += 1
                else:
                    warning(f"  ⚠️ {video.name_for_match} -> 状态更新失败")
            elif hasattr(video, 'feishu_record_id') and video.feishu_record_id:
                status_updated = data_source.update_video_status(video.feishu_record_id, "发布失败")
                if status_updated:
                    error(f"  ❌ {video.name_for_match} -> 发布失败")
                    fail_count += 1
                else:
                    warning(f"  ⚠️ {video.name_for_match} -> 状态更新失败")
        except Exception as e:
            error(f"  ❌ 更新状态失败: {video.name_for_match} - {e}")
    
    if success_count > 0:
        success(f"\n✅ 成功上传并标记 {success_count} 个视频")
    if fail_count > 0:
        error(f"\n❌ {fail_count} 个视频上传失败")


# ==================== 主入口 ====================
async def main():
    """主入口函数"""
    print_douyin_header()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='抖音视频批量自动上传工具')
    parser.add_argument('--mode', type=str, default='local',
                       choices=['local', 'notion', 'feishu'],
                       help='上传模式: local=本地, notion=Notion, feishu=飞书 (默认: local)')
    parser.add_argument('--publish', type=str, default=None,
                       help='发布方式: 1=定时发布, 2=保存草稿 (默认交互式选择)')
    parser.add_argument('--no-interactive', action='store_true',
                       help='非交互模式，无需用户输入')
    parser.add_argument('--account-file', type=str, default=str(DOUYIN_ACCOUNT_FILE),
                       help=f'Cookie 文件路径 (默认: {DOUYIN_ACCOUNT_FILE})')
    
    args = parser.parse_args()
    
    mode = args.mode
    account_file = args.account_file
    
    info(f"当前模式: {mode}")
    info(f"Cookie 文件: {account_file}")
    
    # 确保 Cookie 有效
    if not await ensure_login(account_file, args.no_interactive):
        error("登录验证失败，请检查 Cookie")
        return
    
    success("Cookie 验证通过")
    
    # 加载配置
    config = load_config()
    
    # 获取数据源
    try:
        data_source = get_data_source(mode, config)
    except Exception as e:
        error(f"初始化数据源失败: {e}")
        return
    
    # ==================== 执行上传 ====================
    publish_choice = args.publish
    
    # 本地模式
    if mode == 'local':
        try:
            print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 扫描本地视频...{Colors.RESET}")
            videos = data_source.get_videos()
            
            if not videos:
                warning("未找到可上传的本地视频")
                info("请检查 videos/ 文件夹中是否有视频文件和对应的 .txt 文件")
                return
            
            success(f"找到 {len(videos)} 个视频")
            
            # 显示视频列表
            for i, v in enumerate(videos, 1):
                info(f"  {i}. {v.title} ({v.publish_date.strftime('%Y-%m-%d %H:%M') if v.publish_date else '立即'})")
            
            # 抖音只有定时发布模式，直接使用
            publish_choice = '1'
            success(f"使用定时发布模式，开始上传...")
            
            # 执行批量上传
            result = await upload_videos_from_source(videos, account_file, publish_choice)
            
            # 打印最终汇总
            print_final_summary(result.get('success', []), result.get('failed', []))
            
        except Exception as e:
            error(f"本地模式执行失败: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # Notion混合模式
    elif mode == 'notion':
        try:
            print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ Notion 混合模式 - 获取视频信息...{Colors.RESET}")
            videos = data_source.get_videos()
            
            if not videos:
                warning("未找到可上传的视频")
                info("请检查：")
                info("1. videos/ 文件夹中是否有视频文件")
                info("2. Notion 中是否有对应的视频记录（状态为「待发布」）")
                info("3. 视频文件名是否与 Notion 记录匹配")
                return
            
            # 下载需要云端下载的视频
            need_download = any(v.video_url and not v.video_path for v in videos)
            if need_download:
                print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 正在下载云端视频...{Colors.RESET}")
                videos = await data_source.download_video_files(videos)
                local_count = sum(1 for v in videos if "videos/" in str(v.video_path))
                cloud_count = len(videos) - local_count
                success(f"处理完成: {local_count} 个本地视频, {cloud_count} 个云端下载")
            else:
                info("所有视频已在本地，无需下载")
            
            # 抖音只有定时发布模式
            publish_choice = '1'
            
            # 执行批量上传
            result = await upload_videos_from_source(videos, account_file, publish_choice, data_source)
            
            # 更新发布状态
            update_videos_publish_status(data_source, result, "Notion")
            
            # 打印最终汇总
            print_final_summary(result.get('success', []), result.get('failed', []))
            
        except Exception as e:
            error(f"Notion 模式执行失败: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # 飞书混合模式
    elif mode == 'feishu':
        try:
            print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 飞书混合模式 - 获取视频信息...{Colors.RESET}")
            videos = data_source.get_videos()
            
            if not videos:
                warning("未找到可上传的视频")
                info("请检查：")
                info("1. videos/ 文件夹中是否有视频文件")
                info("2. 飞书多维表格中是否有对应的视频记录（状态为「待发布」）")
                info("3. 视频文件名是否与飞书记录的 Name 字段匹配")
                return
            
            # 下载需要云端下载的视频
            need_download = any(v.video_url and not v.video_path for v in videos)
            if need_download:
                print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}▶ 正在下载云端视频...{Colors.RESET}")
                videos = await data_source.download_video_files(videos)
                local_count = sum(1 for v in videos if "videos/" in str(v.video_path))
                cloud_count = len(videos) - local_count
                success(f"处理完成: {local_count} 个本地视频, {cloud_count} 个云端下载")
            else:
                info("所有视频已在本地，无需下载")
            
            # 抖音只有定时发布模式
            publish_choice = '1'
            
            # 执行批量上传
            result = await upload_videos_from_source(videos, account_file, publish_choice, data_source)
            
            # 更新发布状态
            update_videos_publish_status(data_source, result, "飞书")
            
            # 打印最终汇总
            print_final_summary(result.get('success', []), result.get('failed', []))
            
        except Exception as e:
            error(f"飞书模式执行失败: {e}")
            import traceback
            traceback.print_exc()
            return
    
    success("\n所有操作完成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}")
        sys.exit(1)
