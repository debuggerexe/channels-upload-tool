"""
Notion 数据源实现
从 Notion API 获取视频元数据，支持混合模式（优先本地，无本地则从云端下载）
"""

import os
import re
import time
import aiohttp
import asyncio
from datetime import datetime, date
from typing import List, Tuple, Optional
from pathlib import Path
import requests

from .data_source import VideoDataSource, VideoInfo
from conf import BASE_DIR
from utils.match_utils import (
    remove_date_prefix,
    calculate_similarity,
    select_best_matching_video,
    find_best_match_in_list,
    match_local_video,
    match_local_cover,
    detect_local_dual_covers
)
from utils.text_utils import (
    assemble_description,
    sanitize_short_title,
    parse_publish_date,
    calculate_publish_mode,
    parse_collections
)
from utils.output_utils import (
    print_data_source_header,
    print_records_returned,
    print_pending_videos,
    print_pending_video_item,
    print_skipped_non_pending,
    print_no_videos_warning,
    print_scan_local_videos,
    print_match_summary,
    print_final_video_summary
)

class NotionDataSource(VideoDataSource):
    """Notion 云端数据源"""
    
    # 默认数据库 ID（当 config 中未配置时作为回退）
    DEFAULT_DATABASE_ID = ""
    NOTION_API_BASE = "https://api.notion.com/v1"
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__()  # 调用基类__init__设置temp_dir
        self.api_token = os.getenv("NOTION_API_TOKEN")
        if not self.api_token:
            raise ValueError("请设置环境变量 NOTION_API_TOKEN")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.videos_dir = Path(BASE_DIR) / "videos"
        self.config = config or {}
        
        # 【简化】使用固定的默认发布时间 09:00，不再从本地配置读取
        # 混合模式下，发布时间应完全从 Notion/飞书 获取
        self.default_hour = 9
        self.default_minute = 0
        
        # 从配置获取数据库ID或名称
        self.database_id = self._get_database_id_from_config()
    
    def _get_database_id_from_config(self) -> str:
        """
        从配置中获取数据库ID
        优先级：notion_database_id > notion_database_name（通过API查找）
        两个字段都为空时抛出异常
        """
        # 1. 优先使用 notion_database_id
        db_id = self.config.get('notion_database_id', '').strip()
        if db_id:
            return db_id
        
        # 2. 如果有配置 notion_database_name，尝试搜索
        db_name = self.config.get('notion_database_name', '').strip()
        if db_name:
            try:
                return self._search_database_by_name(db_name)
            except Exception as e:
                raise ValueError(f"通过名称 '{db_name}' 搜索数据库失败: {e}")
        
        # 3. 两个字段都为空，抛出异常
        raise ValueError(
            "未配置 Notion 数据库信息。\n"
            "请在 config.json 中配置以下任一字段：\n"
            "  - notion_database_id: 数据库ID（如 xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）\n"
            "  - notion_database_name: 数据库名称（如 MyDatabase）\n"
            "\n或者切换到本地模式上传。"
        )
    
    def _search_database_by_name(self, name: str) -> str:
        """通过名称搜索数据库"""
        url = f"{self.NOTION_API_BASE}/search"
        payload = {
            "query": name,
            "filter": {"value": "database", "property": "object"},
            "page_size": 10
        }
        # 确保 headers 正确编码
        headers = self.headers.copy()
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        results = response.json().get("results", [])
        if not results:
            raise ValueError(f"未找到名称为 '{name}' 的数据库")
        
        # 优先精确匹配
        for db in results:
            db_title = self._extract_title_from_db(db)
            if db_title == name:
                return db["id"]
        
        # 返回第一个结果
        return results[0]["id"]
    
    def _extract_title_from_db(self, db: dict) -> str:
        """从数据库对象中提取标题"""
        title_items = db.get("title", [])
        if title_items:
            return "".join([item.get("plain_text", "") for item in title_items])
        return ""
    
    def _query_database(self, filter_obj: Optional[dict] = None, max_retries: int = 3) -> List[dict]:
        """
        查询 Notion 数据库（带重试机制）
        
        Args:
            filter_obj: 可选的查询过滤器
            max_retries: 最大重试次数（默认3次）
            
        Returns:
            查询结果列表
        """
        url = f"{self.NOTION_API_BASE}/databases/{self.database_id}/query"
        
        payload = {"page_size": 100}
        if filter_obj:
            payload["filter"] = filter_obj
        
        # 重试循环
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                return data.get("results", [])
                
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.HTTPError) as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避：2, 4, 8秒
                    print(f"⚠️ Notion API 请求失败 (尝试 {attempt}/{max_retries}): {e}")
                    print(f"   ⏳ {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Notion API 请求失败，已重试{max_retries}次: {e}")
                    raise
            except Exception as e:
                # 其他异常不重试，直接抛出
                print(f"❌ Notion API 请求出错: {e}")
                raise
        
        return []
    
    def _parse_description(self, description: str) -> Tuple[str, str]:
        """
        解析 Description 字段
        格式：多行描述 + 最后一行话题标签
        """
        if not description:
            return "", ""
        
        lines = description.strip().split('\n')
        
        # 如果最后一行以 # 开头，认为是话题标签
        if lines and lines[-1].strip().startswith('#'):
            tags_line = lines[-1].strip()
            desc_lines = lines[:-1]
            return '\n'.join(desc_lines).strip(), tags_line
        
        return description.strip(), ""
    
    def _extract_property(self, page: dict, property_name: str) -> any:
        """从页面属性中提取值（支持所有Notion字段类型）"""
        properties = page.get("properties", {})
        prop = properties.get(property_name, {})
        prop_type = prop.get("type", "")
        
        if prop_type == "title":
            title_items = prop.get("title", [])
            return "".join([item.get("plain_text", "") for item in title_items])
        
        elif prop_type == "rich_text":
            rich_text = prop.get("rich_text", [])
            return "".join([item.get("plain_text", "") for item in rich_text])
        
        elif prop_type == "date":
            date_obj = prop.get("date", {})
            if date_obj:
                return date_obj.get("start", "")
            return ""
        
        elif prop_type == "multi_select":
            multi_select = prop.get("multi_select", [])
            return ", ".join([item.get("name", "") for item in multi_select if item.get("name")])
        
        elif prop_type == "select":
            select_obj = prop.get("select", {})
            if select_obj:
                return select_obj.get("name", "")
            return ""
        
        elif prop_type == "checkbox":
            return prop.get("checkbox", False)
        
        elif prop_type == "files":
            # Files & media 类型 - 返回文件列表
            files = prop.get("files", [])
            result = []
            for f in files:
                file_info = {
                    "name": f.get("name", ""),
                    "type": f.get("type", "")
                }
                if f.get("type") == "external":
                    file_info["url"] = f.get("external", {}).get("url", "")
                elif f.get("type") == "file":
                    file_info["url"] = f.get("file", {}).get("url", "")
                result.append(file_info)
            return result
        
        return None
    
    def get_videos_hybrid(self, date_range: Optional[Tuple[date, date]] = None, download_files: bool = False, status_filter: str = "待发布") -> List[VideoInfo]:
        """
        【混合模式】从 Notion 获取视频信息和文件
        
        此模式下：
        1. 从 Notion 数据库读取所有视频元数据
        2. 优先匹配本地 videos/ 文件夹中的视频文件
        3. 本地没有时，从 Notion「视频」字段获取URL，待下载
        
        Args:
            date_range: 可选的日期范围筛选
            download_files: 是否立即下载文件（异步下载）
            status_filter: 状态筛选（默认"待发布"）
            
        Returns:
            VideoInfo 列表，包含视频元数据和云端文件 URL
        """
        print("☁️【混合模式】正在从 Notion 获取视频信息...")
        
        # 构建查询过滤器（如果有日期范围）
        filter_obj = None
        if date_range:
            start_date, end_date = date_range
            filter_obj = {
                "and": [
                    {"property": "发布日期", "date": {"on_or_after": start_date.isoformat()}},
                    {"property": "发布日期", "date": {"on_or_before": end_date.isoformat()}}
                ]
            }
        
        # 查询 Notion 数据库
        pages = self._query_database(filter_obj)
        print(f"  • Notion 返回 {len(pages)} 条记录")
        
        videos = []
        for page in pages:
            try:
                # 提取所有字段
                name_for_match = self._extract_property(page, "Name")
                short_title = self._extract_property(page, "短标题")
                title = self._extract_property(page, "标题")
                description = self._extract_property(page, "描述")
                tags = self._extract_property(page, "标签")
                collections_str = self._extract_property(page, "合集")
                date_str = self._extract_property(page, "发布日期")
                
                # 【云端配置】从 Notion 读取配置项
                cover_position = self._extract_property(page, "封面裁剪") or "middle"
                original_declaration = self._extract_property(page, "声明原创")
                if original_declaration is None:
                    original_declaration = True
                
                # 【位置设置】从 Notion 读取位置字段，默认"平台默认"
                location = self._extract_property(page, "位置") or "平台默认"
                
                # 【发布方式】从 Notion 读取并计算优先级
                publish_mode_notion = self._extract_property(page, "发布方式")
                publish_mode = calculate_publish_mode(publish_mode_notion, bool(date_str))
                
                # 【云端文件】从 Notion 读取视频文件和封面图片
                video_files = self._extract_property(page, "视频") or []
                cover_files = self._extract_property(page, "封面") or []
                horizontal_cover_files = self._extract_property(page, "横封面") or []
                
                # 【状态筛选】从 Notion 读取发布状态，筛选待发布和发布失败的视频
                publish_status = self._extract_property(page, "发布状态")
                allowed_statuses = ["待发布", "发布失败"]
                if publish_status not in allowed_statuses:
                    continue  # 跳过非待发布/发布失败的记录
                
                # 跳过缺少必要字段的记录
                if not name_for_match:
                    print(f"⚠️ 跳过：Notion 记录缺少 Name 字段")
                    continue
                
                if not date_str:
                    print(f"⚠️ 跳过：'{name_for_match}' 缺少发布日期")
                    continue
                
                # 检查是否有视频文件
                if not video_files:
                    print(f"⚠️ 跳过：'{name_for_match}' 缺少视频文件")
                    continue
                
                # 处理合集名称列表
                collections = []
                if collections_str:
                    collections = [c.strip() for c in collections_str.split(",") if c.strip()]
                
                # 清理短标题
                final_short_title = sanitize_short_title(short_title if short_title else "")
                
                # 【云端模式】使用公共函数组装描述
                full_description = assemble_description(title, description, tags, verbose=False)
                
                # 解析日期和时间
                publish_date = parse_publish_date(date_str, self.default_hour, self.default_minute)
                if not publish_date:
                    print(f"⚠️ 日期解析失败 '{date_str}'，跳过")
                    continue
                
                # 获取视频文件 URL
                video_url = None
                if video_files and len(video_files) > 0:
                    video_url = video_files[0].get("url")
                
                # 获取封面文件 URL
                cover_url = None
                if cover_files and len(cover_files) > 0:
                    cover_url = cover_files[0].get("url")
                
                # 获取横封面文件 URL
                horizontal_cover_url = None
                if horizontal_cover_files and len(horizontal_cover_files) > 0:
                    horizontal_cover_url = horizontal_cover_files[0].get("url")
                
                video_info = VideoInfo(
                    title=title if title else short_title,
                    short_title=final_short_title,
                    description=full_description,
                    tags=tags,
                    video_path="",  # 待下载后填充
                    cover_path=None,  # 待下载后填充
                    publish_date=publish_date,
                    collections=collections,
                    original_declaration=bool(original_declaration),
                    cover_position=cover_position,
                    location=location,  # 位置设置
                    name_for_match=name_for_match,
                    folder_name=name_for_match,
                    source_mode="notion",
                    video_url=video_url,
                    cover_url=cover_url,
                    horizontal_cover_url=horizontal_cover_url,
                    notion_page_id=page.get("id"),  # 保存 Notion 页面 ID 用于更新状态
                    publish_mode=publish_mode  # 发布方式（"1"或"2"）
                )
                videos.append(video_info)
                print(f"✅ 云端记录: {name_for_match} (视频: {len(video_files)}个, 封面: {len(cover_files)}个)")
                
            except Exception as e:
                print(f"⚠️ 处理 Notion 记录时出错: {e}")
                continue
        
        print(f"\n☁️ Notion混合模式共找到 {len(videos)} 个【待发布/发布失败】状态的视频")
        
        # 按日期排序
        videos.sort(key=lambda x: x.publish_date, reverse=False)
        
        print(f"\n找到 {len(videos)} 个视频（按上传顺序）：")
        for v in videos:
            print(f"- {v.title} ({v.publish_date.strftime('%Y-%m-%d %H:%M')})")
        
        return videos
    
    def get_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """
        【Notion混合模式】优先本地视频，无本地则从Notion云端下载

        此模式下：
        1. 从 Notion 获取视频元数据（只获取待发布/发布失败的）
        2. 优先匹配本地 videos/ 文件夹中的视频
        3. 本地没有时，从 Notion「视频」字段获取URL，待下载

        Args:
            date_range: 可选的日期范围筛选

        Returns:
            VideoInfo 列表，包含本地路径或云端URL
        """
        # ========== 第一步：从 Notion 获取所有记录并筛选 ==========
        print_data_source_header("Notion")

        # 构建查询过滤器（如果有日期范围）
        filter_obj = None
        if date_range:
            start_date, end_date = date_range
            filter_obj = {
                "and": [
                    {"property": "发布日期", "date": {"on_or_after": start_date.isoformat()}},
                    {"property": "发布日期", "date": {"on_or_before": end_date.isoformat()}}
                ]
            }

        # 查询 Notion 数据库
        all_pages = self._query_database(filter_obj)
        print_records_returned(len(all_pages))

        # 按状态筛选：只保留"待发布"和"发布失败"
        pending_pages = []
        skipped_records = []
        for page in all_pages:
            name = self._extract_property(page, "Name") or "未知"
            status = self._extract_property(page, "发布状态")
            date_str = self._extract_property(page, "发布日期")

            if status in ["待发布", "发布失败"]:
                pending_pages.append(page)
            else:
                skipped_records.append((name, status or "无状态"))

        # 【修复】按发布日期排序待上传视频
        from datetime import datetime
        def get_page_date(page):
            date_str = self._extract_property(page, "发布日期") or ""
            if date_str:
                try:
                    # 解析ISO格式日期，去除时区信息
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    return dt
                except Exception:
                    pass
            return datetime.max  # 无日期的排最后
        pending_pages.sort(key=get_page_date)

        # 显示待上传视频列表
        print_pending_videos(len(pending_pages), "Notion")
        for page in pending_pages:
            name = self._extract_property(page, "Name") or "未知"
            status = self._extract_property(page, "发布状态") or "无状态"
            date_str = self._extract_property(page, "发布日期") or "无日期"
            print_pending_video_item(name, status, date_str)

        if skipped_records:
            print_skipped_non_pending(len(skipped_records))

        if not pending_pages:
            print_no_videos_warning()
            return []

        # ========== 第二步：扫描本地视频 ==========
        video_items = self._scan_videos()
        print_scan_local_videos(len(video_items))

        # 建立本地视频索引
        local_videos = {}
        for video_file, container_name in video_items:
            clean_name = remove_date_prefix(container_name)
            local_videos[clean_name] = (video_file, container_name)
            local_videos[container_name] = (video_file, container_name)

        # ========== 第三步：匹配本地视频 / 标记需要下载 ==========
        local_matched = []      # (video_info, local_path, cover_path)
        need_download = []      # (video_info, video_url, cover_url)
        skipped_no_source = []  # 无本地也无云端URL

        for page in pending_pages:
            try:
                # 提取字段
                name_for_match = self._extract_property(page, "Name")
                short_title = self._extract_property(page, "短标题")
                title = self._extract_property(page, "标题")
                description = self._extract_property(page, "描述")
                tags = self._extract_property(page, "标签")
                collections_str = self._extract_property(page, "合集")
                date_str = self._extract_property(page, "发布日期")
                cover_position = self._extract_property(page, "封面裁剪") or "middle"
                original_declaration = self._extract_property(page, "声明原创")
                location = self._extract_property(page, "位置") or "平台默认"
                publish_mode_notion = self._extract_property(page, "发布方式")

                if not name_for_match or not date_str:
                    continue

                # 尝试匹配本地视频
                local_video = None
                local_cover = None
                for local_name in [name_for_match, remove_date_prefix(name_for_match)]:
                    if local_name in local_videos:
                        local_video, _ = local_videos[local_name]
                        # 检测双图模式（竖图+横图）
                        vertical_cover, horizontal_cover = detect_local_dual_covers(local_video)
                        if vertical_cover:
                            local_cover = vertical_cover
                            local_horizontal_cover = horizontal_cover
                        break

                # 解析日期和其他字段
                publish_date = parse_publish_date(date_str, self.default_hour, self.default_minute)
                if not publish_date:
                    continue

                final_short_title = sanitize_short_title(short_title if short_title else "")
                full_description = assemble_description(title, description, tags, verbose=False)
                collections = parse_collections(collections_str)
                publish_mode = calculate_publish_mode(publish_mode_notion, bool(date_str))

                video_info = VideoInfo(
                    title=title if title else short_title,
                    short_title=final_short_title,
                    description=full_description,
                    tags=tags,
                    video_path=str(local_video) if local_video else None,
                    cover_path=str(local_cover) if local_cover else None,
                    horizontal_cover_path=str(local_horizontal_cover) if local_horizontal_cover else None,
                    video_url=None,
                    cover_url=None,
                    publish_date=publish_date,
                    collections=collections,
                    original_declaration=bool(original_declaration) if original_declaration is not None else True,
                    cover_position=cover_position,
                    location=location,
                    name_for_match=name_for_match,
                    folder_name=name_for_match,
                    source_mode="notion_hybrid",
                    notion_page_id=page.get("id"),
                    publish_mode=publish_mode
                )

                if local_video:
                    local_matched.append((video_info, name_for_match))
                else:
                    # 本地没有，尝试获取云端URL
                    video_files = self._extract_property(page, "视频") or []
                    cover_files = self._extract_property(page, "封面") or []

                    if video_files and len(video_files) > 0:
                        video_info.video_url = video_files[0].get("url")
                        if cover_files and len(cover_files) > 0:
                            video_info.cover_url = cover_files[0].get("url")
                        need_download.append((video_info, name_for_match))
                    else:
                        skipped_no_source.append(name_for_match)

            except Exception as e:
                print(f"⚠️ 处理记录时出错: {e}")
                continue

        # ========== 第四步：显示匹配结果 ==========
        print_match_summary(
            local_count=len(local_matched),
            download_count=len(need_download),
            no_source_count=len(skipped_no_source),
            local_names=[name for _, name in local_matched],
            download_names=[name for _, name in need_download],
            no_source_names=skipped_no_source
        )

        # ========== 第五步：汇总并返回 ==========
        videos = [v for v, _ in local_matched] + [v for v, _ in need_download]

        # 使用公共函数打印最终汇总
        print_final_video_summary(videos)

        return videos
    
    def _scan_videos(self) -> List[Tuple[Path, str]]:
        """
        扫描 videos 目录，返回所有视频文件列表
        
        支持两种存放方式：
        1. 子文件夹形式: videos/文件夹名/视频.mp4 -> (视频路径, 文件夹名)
           - 如果文件夹中有多个视频，选择与文件夹名最匹配的那个
        2. 直接存放: videos/视频.mp4 -> (视频路径, 视频文件名不含扩展名)
        
        Returns:
            List[Tuple[Path, str]]: [(视频文件路径, 用于匹配的名称)]
        """
        video_items = []
        
        if not self.videos_dir.exists():
            return video_items
        
        # 方式1: 扫描子文件夹
        for item in self.videos_dir.iterdir():
            if item.is_dir():
                # 在子文件夹中查找视频文件
                video_files = list(item.glob("*.mp4"))
                if not video_files:
                    continue
                
                # 清理文件夹名（去除日期前缀）
                folder_name_clean = remove_date_prefix(item.name)
                
                if len(video_files) == 1:
                    # 只有一个视频，直接使用
                    video_items.append((video_files[0], item.name))
                else:
                    # 多个视频：选择与文件夹名最匹配的那个
                    best_match, _ = select_best_matching_video(video_files, item.name, verbose=False)
                    if best_match:
                        video_items.append((best_match, item.name))
        
        # 方式2: 扫描直接放在 videos 目录下的视频文件
        for video_file in self.videos_dir.glob("*.mp4"):
            if video_file.is_file():
                # 使用视频文件名（不含扩展名）进行匹配
                video_name = video_file.stem
                video_items.append((video_file, video_name))
        
        return video_items
    
    def _find_notion_record(self, title: str, notion_records: dict) -> Optional[dict]:
        """
        在 Notion 记录中查找匹配项
        
        匹配策略：
        1. 精确匹配（去除前后空格）
        2. 包含匹配（title 包含在 Cover 中，或 Cover 包含在 title 中）
        3. 相似度匹配（60% 阈值）
        """
        clean_title = title.strip()
        
        # 策略1：精确匹配
        if clean_title in notion_records:
            return notion_records[clean_title]
        
        # 策略2 & 3：遍历查找最佳匹配
        best_match = None
        best_score = 0.0
        
        for cover, page in notion_records.items():
            cover_clean = cover.strip()
            
            # 包含匹配
            if clean_title in cover_clean or cover_clean in clean_title:
                score = 0.8
                if score > best_score:
                    best_score = score
                    best_match = page
                continue
            
            # 相似度匹配
            similarity = calculate_similarity(clean_title, cover_clean)
            if similarity > 0.6 and similarity > best_score:
                best_score = similarity
                best_match = page
        
        return best_match
    
    def get_videos_count(self, date_range: Optional[Tuple[date, date]] = None) -> int:
        """获取视频数量"""
        return len(self.get_videos(date_range))
    
    def get_all_notion_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """
        获取所有 Notion 云端视频记录（不依赖本地视频文件）
        
        用于视频预览页面的"云端"模式，直接显示所有 Notion 数据库中的视频
        """
        print("📡 正在从 Notion 获取所有云端视频...")
        
        # 构建查询过滤器（如果有日期范围）
        filter_obj = None
        if date_range:
            start_date, end_date = date_range
            filter_obj = {
                "and": [
                    {"property": "发布日期", "date": {"on_or_after": start_date.isoformat()}},
                    {"property": "发布日期", "date": {"on_or_before": end_date.isoformat()}}
                ]
            }
        
        # 查询 Notion 数据库
        pages = self._query_database(filter_obj)
        print(f"📡 Notion API 返回 {len(pages)} 条记录")
        
        videos = []
        for page in pages:
            try:
                # 提取 Notion 中的信息
                name_for_match = self._extract_property(page, "Name")  # 用于匹配本地视频
                short_title = self._extract_property(page, "短标题")  # 视频号短标题
                title = self._extract_property(page, "标题")  # 视频号主标题
                description = self._extract_property(page, "描述")  # 视频描述区内容
                tags = self._extract_property(page, "标签")  # 话题标签
                collections_str = self._extract_property(page, "合集")  # 合集名称
                date_str = self._extract_property(page, "发布日期")
                cover_position = self._extract_property(page, "封面裁剪") or "middle"
                original_declaration = self._extract_property(page, "声明原创")
                location = self._extract_property(page, "位置") or "平台默认"
                
                # 跳过缺少必要字段的记录
                if not name_for_match:
                    print(f"⚠️ 跳过：Notion 记录缺少 Name 字段")
                    continue
                
                if not date_str:
                    print(f"⚠️ 跳过：'{name_for_match}' 缺少发布日期")
                    continue
                
                # 处理合集名称列表
                collections = []
                if collections_str:
                    collections = [c.strip() for c in collections_str.split(",") if c.strip()]
                
                # 清理短标题
                final_short_title = sanitize_short_title(short_title if short_title else "")
                
                # 使用公共函数组装描述
                full_description = assemble_description(title, description, tags, verbose=False)
                
                # 解析日期
                try:
                    if 'T' in date_str:
                        publish_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_part = datetime.fromisoformat(date_str)
                        publish_date = date_part.replace(hour=self.default_hour, minute=self.default_minute)
                    if publish_date.tzinfo is not None:
                        publish_date = publish_date.replace(tzinfo=None)
                except Exception as e:
                    print(f"⚠️ 日期解析失败 '{date_str}'，跳过: {e}")
                    continue
                
                # 尝试匹配本地封面（如果有对应的本地视频）
                cover_path = None
                video_path = None
                
                video_info = VideoInfo(
                    title=title if title else short_title,
                    short_title=final_short_title,
                    description=full_description,
                    tags=tags,
                    video_path=video_path or "",
                    cover_path=cover_path,
                    publish_date=publish_date,
                    collections=collections,
                    original_declaration=bool(original_declaration) if original_declaration is not None else True,
                    cover_position=cover_position,
                    location=location
                )
                videos.append(video_info)
                
            except Exception as e:
                print(f"⚠️ 处理 Notion 记录时出错: {e}")
                continue
        
        print(f"✅ 从 Notion 获取到 {len(videos)} 条云端视频记录")
        
        # 按日期排序
        videos.sort(key=lambda x: x.publish_date, reverse=False)
        
        return videos
    
    def update_video_status(self, page_id: str, status: str = "已发布") -> bool:
        """
        更新 Notion 中视频的状态
        
        Args:
            page_id: Notion 页面 ID
            status: 新状态值（默认"已发布"）
            
        Returns:
            是否更新成功
        """
        try:
            url = f"{self.NOTION_API_BASE}/pages/{page_id}"
            payload = {
                "properties": {
                    "发布状态": {
                        "select": {
                            "name": status
                        }
                    }
                }
            }
            response = requests.patch(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ 更新状态失败: {e}")
            return False


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python notion_data_source.py <notion_api_token>")
        sys.exit(1)
    
    os.environ["NOTION_API_TOKEN"] = sys.argv[1]
    
    try:
        source = NotionDataSource()
        videos = source.get_videos()
        print(f"找到 {len(videos)} 个视频:")
        for v in videos:
            print(f"- {v.title} ({v.publish_date.date()})")
    except Exception as e:
        print(f"错误: {e}")
