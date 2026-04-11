#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音单视频上传示例

用法：
    python examples/upload_douyin_single.py <视频文件路径>

示例：
    python examples/upload_douyin_single.py videos/my_video.mp4

说明：
    这个脚本演示如何使用 DouYinVideo 类上传单个视频。
    视频文件需要有对应的同名 .txt 文件包含标题和标签。
    例如：my_video.mp4 对应 my_video.txt
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from conf import BASE_DIR
from uploader.douyin_uploader.main import DouYinVideo, douyin_setup, DOUYIN_ACCOUNT_FILE
from utils.files_times import get_title_and_hashtags


async def main():
    # 检查参数
    if len(sys.argv) < 2:
        print("用法: python examples/upload_douyin_single.py <视频文件路径>")
        print("示例: python examples/upload_douyin_single.py videos/my_video.mp4")
        sys.exit(1)
    
    video_file = Path(sys.argv[1])
    
    # 检查视频文件是否存在
    if not video_file.exists():
        print(f"错误: 视频文件不存在: {video_file}")
        sys.exit(1)
    
    # 检查 Cookie
    print("检查 Cookie...")
    if not await douyin_setup(str(DOUYIN_ACCOUNT_FILE), handle=False):
        print("Cookie 无效，请先运行: python examples/get_douyin_cookie.py")
        sys.exit(1)
    
    print("Cookie 有效\n")
    
    # 获取标题和标签
    title, tags = get_title_and_hashtags(str(video_file))
    
    # 解析标签
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split('#') if t.strip()]
    
    # 封面路径
    thumbnail_path = video_file.with_suffix('.jpg')
    if not thumbnail_path.exists():
        thumbnail_path = video_file.with_suffix('.png')
    if not thumbnail_path.exists():
        thumbnail_path = None
    
    # 发布时间（默认明天同一时间）
    publish_date = datetime.now() + timedelta(days=1)
    
    print("=" * 60)
    print("抖音视频上传")
    print("=" * 60)
    print(f"视频文件: {video_file}")
    print(f"标题: {title}")
    print(f"话题标签: {tag_list}")
    print(f"发布时间: {publish_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"封面: {thumbnail_path or '使用视频默认封面'}")
    print("=" * 60)
    
    # 确认上传
    confirm = input("\n确认上传? (y/n): ").strip().lower()
    if confirm != 'y':
        print("上传已取消")
        sys.exit(0)
    
    # 创建上传实例
    app = DouYinVideo(
        title=title,
        file_path=str(video_file),
        tags=tag_list,
        publish_date=publish_date,
        account_file=str(DOUYIN_ACCOUNT_FILE),
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        location="杭州市",
        sync_to_toutiao=True
    )
    
    # 执行上传
    print("\n开始上传...")
    success = await app.main()
    
    if success:
        print("\n✅ 视频上传成功！")
    else:
        print("\n❌ 视频上传失败")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
