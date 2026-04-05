import os
import re
import asyncio
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import shutil

from conf import BASE_DIR
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from utils.files_times import get_title_and_hashtags
from playwright.async_api import async_playwright

# 导入数据源
from data_sources.data_source import VideoInfo
from data_sources.local_data_source import LocalDataSource
from data_sources.notion_data_source import NotionDataSource, sanitize_short_title

class WeChatVideoUploader:
    def __init__(self, account_file: str, data_source=None):
        self.account_file = account_file
        self.videos_dir = Path(BASE_DIR) / "videos"
        
        # 从 config.json 加载设置
        self.config = self._load_config()
        self.original_declaration = self.config.get('original_declaration', False)
        self.cover_position = self.config.get('cover_position', 'middle')
        self.publish_times = self.config.get('publish_times', ['10:00'])
        self.default_publish_hour = int(self.publish_times[0].split(':')[0]) if self.publish_times else 10
        self.default_publish_minute = int(self.publish_times[0].split(':')[1]) if self.publish_times and ':' in self.publish_times[0] else 0
        self.collection = self.config.get('collection', '')  # 合集配置（本地模式使用）
        # 解析合集列表（支持逗号分隔的多个合集）
        self.collections = []
        if self.collection:
            self.collections = [c.strip() for c in self.collection.split(',') if c.strip()]
        
        # 数据源
        self.data_source = data_source
        
    def _load_config(self) -> dict:
        """加载配置，优先读取 config.json，不存在则读取 config.example.json"""
        # 优先读取本地配置
        config_path = Path(BASE_DIR) / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 本地配置不存在，读取示例配置
        example_path = Path(BASE_DIR) / "config.example.json"
        if example_path.exists():
            print("⚠️ 未找到 config.json，使用默认配置（config.example.json）")
            with open(example_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
        
    def extract_date_from_folder(self, folder_name: str) -> Optional[datetime]:
        """从文件夹名中提取日期"""
        # 匹配前6位数字作为日期 (YYMMDD)
        match = re.match(r'^(\d{6})', folder_name)
        if not match:
            return None
            
        date_str = match.group(1)
        try:
            # 将YYMMDD转换为datetime对象 (假设20xx年)
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return datetime(year, month, day)
        except (ValueError, IndexError):
            return None
    
    def get_video_info(self, folder_path: Path) -> Optional[Dict]:
        """获取视频文件夹中的视频、标题和封面信息，使用智能匹配选择视频"""
        video_files = list(folder_path.glob("*.mp4"))
        if not video_files:
            print(f"警告: 在 {folder_path} 中未找到视频文件")
            return None
        
        # 【修复】使用智能匹配选择最佳视频文件
        from utils.match_utils import select_best_matching_video
        best_video, score = select_best_matching_video(video_files, folder_path.name, verbose=True)
        if not best_video:
            print(f"警告: 无法找到匹配的视频文件: {folder_path}")
            return None
        video_file = best_video
        
        # 查找文本文件 (标题和描述)
        txt_files = list(folder_path.glob("*.txt"))
        if txt_files:
            with open(txt_files[0], 'r', encoding='utf-8') as f:
                title = f.readline().strip()
                description = f.read().strip()
        else:
            title = video_file.stem
            description = ""
        
        # 【新增】本地模式短标题处理：超过16字自动截断
        original_title = title
        title = sanitize_short_title(title)
        if len(re.sub(r'[^\u4e00-\u9fa5]', '', original_title)) > 16:
            print(f"⚠️ 短标题超过16字已截断: '{original_title}' → '{title}'")
        
        # 查找封面图片
        cover_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.jpeg")) + list(folder_path.glob("*.png"))
        cover_path = str(cover_files[0]) if cover_files else None
        
        return {
            'video_path': str(video_file),
            'title': title,
            'description': description,
            'cover_path': cover_path
        }
    
    def get_sorted_video_folders(self) -> List[Tuple[datetime, Path, bool]]:
        """获取按日期排序的视频文件夹，无日期的使用config中的默认日期"""
        dated_folders = []
        for folder in self.videos_dir.iterdir():
            if not folder.is_dir():
                continue
            # 尝试从文件夹名提取日期
            date = self.extract_date_from_folder(folder.name)
            has_date_in_name = date is not None
            
            # 如果没有提取到日期，使用config中的默认日期
            if not date:
                date = self.config_publish_date
            
            # 只保留2025年8月1日之后的日期（或今天之后的日期）
            if date >= datetime(2025, 8, 1):
                dated_folders.append((date, folder, has_date_in_name))
        
        # 先按日期排序，有日期的排前面，日期相同的按文件夹名排序
        dated_folders.sort(key=lambda x: (x[0], not x[2], x[1].name))
        return dated_folders
    
    async def _upload_single_video(self, video_data: Dict, playwright, is_last_video: bool = False, 
                                   publish_mode: str = '1', max_retries: int = 3) -> bool:
        """
        统一的单视频上传方法
        
        Args:
            video_data: 视频数据字典，包含 title, description, video_path, cover_path, publish_date 等
            playwright: Playwright 实例
            is_last_video: 是否是最后一个视频
            publish_mode: 发布模式 ('1'=定时发布, '2'=保存草稿)
            max_retries: 最大重试次数
            
        Returns:
            bool: 上传是否成功
        """
        print(f"\n准备上传视频: {video_data['title']}")
        print(f"计划发布时间: {video_data['publish_date'].strftime('%Y-%m-%d %H:%M')}")
        if is_last_video:
            print("最后一个视频，上传完成后保持浏览器打开")
        
        category = 15  # 15 是生活类
        
        # 创建视频对象，传入文件移动回调
        video_path = video_data['video_path']
        video_title = video_data['title']
        
        async def on_upload_success():
            """上传成功后的回调，在浏览器保持打开前执行文件移动"""
            await self._move_to_published(video_path, video_title)
        
        app = TencentVideo(
            short_title=video_data['title'],
            title_and_tags=video_data['description'],
            file_path=video_path,
            publish_date=video_data['publish_date'],
            account_file=self.account_file,
            category=category,
            original_declaration=self.original_declaration,
            cover_position=self.cover_position,
            thumbnail_path=video_data.get('cover_path'),
            keep_open=is_last_video,
            publish_mode=publish_mode,
            collections=video_data.get('collections', self.collections),
            on_upload_success=on_upload_success if is_last_video else None  # 只有最后一个视频需要回调
        )
        
        # 尝试上传
        for attempt in range(1, max_retries + 1):
            try:
                result = await app.upload(playwright)
                if result:
                    print(f"✅ 视频上传成功: {video_data['title']}")
                    return True
                else:
                    print(f"❌ 视频上传失败: {video_data['title']}")
            except Exception as e:
                print(f"❌ 视频上传失败: {video_data['title']} - {str(e)}")
            
            if attempt < max_retries:
                print(f"❌ 上传失败 (尝试 {attempt}/{max_retries}): {video_data['title']}")
                await asyncio.sleep(5)
            else:
                print(f"⏭️ 最终失败，跳过此视频: {video_data['title']}")
        
        return False

    async def _move_to_published(self, video_path: str, video_title: str):
        """
        将视频移动到 published 目录
        
        Args:
            video_path: 视频文件路径
            video_title: 视频标题（用于日志输出）
        """
        try:
            video_path_obj = Path(video_path)
            published_dir = Path(BASE_DIR) / "published"
            published_dir.mkdir(exist_ok=True)
            
            # 判断是子文件夹形式还是直接存放形式
            if video_path_obj.parent.name == "videos":
                # 方式2: 视频直接放在 videos/ 目录下
                # 移动单个视频文件和对应的封面图
                target_video = published_dir / video_path_obj.name
                shutil.move(str(video_path_obj), str(target_video))
                print(f"✅ 已移动视频: {video_path_obj.name} -> published/")
                
                # 同时移动同名的封面图（如果存在）
                for ext in ['.jpg', '.jpeg', '.png']:
                    cover_file = video_path_obj.with_suffix(ext)
                    if cover_file.exists():
                        target_cover = published_dir / cover_file.name
                        shutil.move(str(cover_file), str(target_cover))
                        print(f"✅ 已移动封面: {cover_file.name} -> published/")
                        break
                
                # 同时移动裁剪后的封面图（如果存在）
                video_stem = video_path_obj.stem
                for crop_ext in ['.jpg', '.jpeg', '.png']:
                    crop_file = video_path_obj.parent / f"{video_stem}_crop{crop_ext}"
                    if crop_file.exists():
                        target_crop = published_dir / crop_file.name
                        shutil.move(str(crop_file), str(target_crop))
                        print(f"✅ 已移动裁剪封面: {crop_file.name} -> published/")
                        break
            else:
                # 方式1: 视频在子文件夹中
                folder = video_path_obj.parent
                target_folder = published_dir / folder.name
                
                if folder.exists() and folder != published_dir:
                    shutil.move(str(folder), str(target_folder))
                    print(f"✅ 已移动文件夹: {folder.name} -> published/")
                else:
                    print(f"⚠️ 文件夹不存在或已在 published: {folder.name}")
        except Exception as move_error:
            print(f"❌ 移动失败: {move_error}")
    
    async def upload_all_videos(self, publish_mode: str = '1', skip_confirm: bool = False):
        """上传所有视频（本地模式）"""
        print("开始扫描视频文件夹...")
        dated_folders = self.get_sorted_video_folders()
        
        if not dated_folders:
            print("未找到有效的视频文件夹！")
            return
            
        print(f"\n找到 {len(dated_folders)} 个视频待上传，按日期排序:")
        for date, folder, has_date in dated_folders:
            print(f"- {date.strftime('%Y-%m-%d')}: {folder.name}")
        
        # 只有需要确认时才询问（兼容直接调用场景）
        if not skip_confirm:
            confirm = input("\n确认开始上传？(y/n): ")
            if confirm.lower() != 'y':
                print("上传已取消")
                return
        else:
            print(f"\n直接开始上传，共 {len(dated_folders)} 个视频...")
        
        # 登录微信视频号
        print("\n正在登录微信视频号...")
        if not await weixin_setup(self.account_file, handle=True):
            print("登录失败，请检查账号配置")
            return
        
        # 上传每个视频
        success_count = 0
        
        async with async_playwright() as playwright:
            for idx, (date, folder, has_date) in enumerate(dated_folders):
                video_info = self.get_video_info(folder)
                if not video_info:
                    print(f"跳过无效文件夹: {folder}")
                    continue
                
                # 设置发布时间为当天的配置小时和分钟
                publish_time = datetime.combine(
                    date.date(), 
                    datetime.min.time().replace(hour=self.default_publish_hour, minute=self.default_publish_minute)
                )
                
                # 如果发布时间早于当前时间，设置为当前时间 + 10 分钟
                now = datetime.now()
                if publish_time < now:
                    publish_time = now + timedelta(minutes=10)
                    tencent_logger.warning(f"视频日期已调整: {publish_time.strftime('%Y-%m-%d %H:%M')}")
                
                # 组装视频数据
                video_data = {
                    'title': video_info['title'],
                    'description': video_info['description'],
                    'video_path': video_info['video_path'],
                    'cover_path': video_info.get('cover_path'),
                    'publish_date': publish_time,
                    'collections': self.collections
                }
                
                # 判断是否是最后一个视频
                is_last_video = (idx == len(dated_folders) - 1)
                
                # 使用公共方法上传
                success = await self._upload_single_video(
                    video_data, playwright, is_last_video, publish_mode
                )
                
                if success:
                    success_count += 1
                    # 移动到 published 目录（最后一个视频通过回调移动）
                    if not is_last_video:
                        await self._move_to_published(video_info['video_path'], video_info['title'])
                
                # 如果不是最后一个视频，添加延迟
                if not is_last_video:
                    await asyncio.sleep(5)
        
        print(f"\n{'='*60}")
        print(f"上传完成！成功上传 {success_count}/{len(dated_folders)} 个视频")
        print(f"{'='*60}")

    async def upload_videos_from_source(self, videos: List[VideoInfo], publish_mode: str = '1'):
        """从数据源上传视频（云端模式）"""
        if not videos:
            print("未找到要上传的视频")
            return
        
        # 登录微信视频号
        print("\n正在登录微信视频号...")
        if not await weixin_setup(self.account_file, handle=True):
            print("登录失败，请检查账号配置")
            return
        
        # 上传每个视频
        success_count = 0
        
        async with async_playwright() as playwright:
            for idx, video in enumerate(videos):
                # 组装视频数据
                video_data = {
                    'title': video.short_title,
                    'description': video.description,
                    'video_path': video.video_path,
                    'cover_path': video.cover_path,
                    'publish_date': video.publish_date,
                    'collections': video.collections
                }
                
                # 判断是否是最后一个视频
                is_last_video = (idx == len(videos) - 1)
                
                # 使用公共方法上传
                success = await self._upload_single_video(
                    video_data, playwright, is_last_video, publish_mode
                )
                
                if success:
                    success_count += 1
                    # 移动到 published 目录（最后一个视频通过回调移动）
                    if not is_last_video:
                        await self._move_to_published(video.video_path, video.title)
                
                # 如果不是最后一个视频，添加延迟
                if not is_last_video:
                    await asyncio.sleep(5)
        
        # 上传完成统计
        print(f"\n{'='*60}")
        print(f"上传完成！成功上传 {success_count}/{len(videos)} 个视频")
        print(f"{'='*60}")


async def main():
    # 账号配置文件路径
    account_file = str(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")
    
    # 确保账号文件存在
    if not os.path.exists(account_file):
        print(f"错误: 账号文件不存在: {account_file}")
        print("请先运行 examples/get_tencent_cookie.py 获取cookie")
        return
    
    # ==================== 交互式菜单 ====================
    print("\n" + "="*60)
    print("🎬 微信视频号批量上传工具")
    print("="*60)
    print("\n请选择数据源：")
    print("1. 本地模式（从 videos/ 文件夹读取 txt 文件）")
    print("2. 云端模式（从 Notion 数据库读取视频信息）")
    print()
    
    mode = input("请输入选项 (1/2): ").strip()
    
    data_source = None
    
    # 加载配置（优先 config.json，不存在则读取 config.example.json）
    def load_config():
        config_path = Path(BASE_DIR) / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        example_path = Path(BASE_DIR) / "config.example.json"
        if example_path.exists():
            return json.load(example_path)
        
        return {}
    
    if mode == "1":
        print("\n✅ 已选择：本地模式")
        config = load_config()
        data_source = LocalDataSource(config)
        
    elif mode == "2":
        print("\n✅ 已选择：云端模式（Notion）")
        print("\n📁 将扫描 videos/ 文件夹中的视频，并从 Notion 获取标题/描述/标签")
        
        # 检查 Notion API Token
        if not os.getenv("NOTION_API_TOKEN"):
            print("\n⚠️ 请先设置环境变量 NOTION_API_TOKEN")
            print("示例: export NOTION_API_TOKEN='your_token_here'")
            
            choice = input("\n请选择：1. 切换到本地模式  2. 退出程序 : ").strip()
            if choice == "1":
                print("\n✅ 已切换至：本地模式")
                config = load_config()
                data_source = LocalDataSource(config)
            else:
                print("程序已退出")
                return
        else:
            # 读取配置
            config = load_config()
            
            try:
                data_source = NotionDataSource(config)
            except ValueError as e:
                print(f"\n⚠️ {e}")
                
                choice = input("\n请选择：1. 切换到本地模式  2. 退出程序 : ").strip()
                if choice == "1":
                    print("\n✅ 已切换至：本地模式")
                    data_source = LocalDataSource(config)
                else:
                    print("程序已退出")
                    return
            else:
                # 云端模式正常初始化
                print("\n正在扫描本地视频并匹配 Notion 数据...")
                videos = data_source.get_videos()
                
                if not videos:
                    print("❌ 未找到可上传的视频（请确保 videos/ 文件夹中有视频且 Notion 中有匹配的标题）")
                    return
                
                print("\n请选择发布方式：")
                print("1. 定时发布（设置发布时间后发表）")
                print("2. 保存草稿（不发表，仅保存到草稿箱）")
                print("3. 退出")
                
                publish_choice = input("\n请输入选项 (1/2/3): ").strip()
                
                if publish_choice == '3':
                    print("上传已取消")
                    return
                elif publish_choice not in ['1', '2']:
                    print("无效选项，默认使用定时发布")
                    publish_choice = '1'
                
                # 创建上传器并执行云端模式上传
                uploader = WeChatVideoUploader(account_file, data_source)
                await uploader.upload_videos_from_source(videos, publish_mode=publish_choice)
                return
        
    else:
        print("❌ 无效选项，默认使用本地模式")
        config = load_config()
        data_source = LocalDataSource(config)
    
    # 本地模式上传
    try:
        # 创建 uploader 对象（本地模式需要在这里创建）
        uploader = WeChatVideoUploader(account_file, data_source)
        
        print("\n开始扫描视频文件夹...")
        dated_folders = uploader.get_sorted_video_folders()
        
        if not dated_folders:
            print("未找到有效的视频文件夹！")
            return
            
        print(f"\n找到 {len(dated_folders)} 个视频待上传，按日期排序:")
        for date, folder, has_date in dated_folders:
            print(f"- {date.strftime('%Y-%m-%d')}: {folder.name}")
        
        # 【优化】合并确认和发布方式选择，减少一次交互
        print("\n请选择操作：")
        print("1. 定时发布")
        print("2. 保存草稿")
        print("3. 取消上传")
        
        choice = input("\n请输入选项 (1/2/3): ").strip()
        
        if choice == '3':
            print("上传已取消")
            return
        
        publish_choice = '1' if choice == '1' else '2'
        action_name = "定时发布" if choice == '1' else "保存草稿"
        print(f"\n✅ 确认使用{action_name}模式，开始上传...")
        
        await uploader.upload_all_videos(publish_mode=publish_choice, skip_confirm=True)
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
