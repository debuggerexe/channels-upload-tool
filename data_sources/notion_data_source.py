"""
Notion 云端数据源实现
直接从 Notion API 获取视频信息，匹配本地视频文件
"""

import os
import re
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
    find_best_match_in_list
)


def sanitize_short_title(title: str) -> str:
    """
    清理短标题，只保留中文字符
    
    处理流程：
    1. 过滤：只保留中文字符（去掉英文、数字、符号）
    2. 填充：不足6字用空格补充到6字
    3. 截断：超过16字强行截断到16字
    """
    if not title:
        return "      "  # 6个空格
    
    # 步骤1：只保留中文字符
    chinese_only = re.sub(r'[^\u4e00-\u9fa5]', '', title)
    
    # 步骤2：不足6字用空格补充
    if len(chinese_only) < 6:
        chinese_only = chinese_only + ' ' * (6 - len(chinese_only))
    
    # 步骤3：超过16字强行截断（直接截取前16字，不保留完整词义）
    if len(chinese_only) > 16:
        chinese_only = chinese_only[:16]
    
    return chinese_only


class NotionDataSource(VideoDataSource):
    """Notion 云端数据源"""
    
    # 默认数据库 ID（当 config 中未配置时作为回退）
    DEFAULT_DATABASE_ID = ""
    NOTION_API_BASE = "https://api.notion.com/v1"
    
    def __init__(self, config: Optional[dict] = None):
        self.api_token = os.getenv("NOTION_API_TOKEN")
        if not self.api_token:
            raise ValueError("请设置环境变量 NOTION_API_TOKEN")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.videos_dir = Path(BASE_DIR) / "videos"
        
        # 从配置获取默认发布时间
        self.config = config or {}
        publish_times = self.config.get('publish_times', ['10:00'])
        if publish_times and ':' in publish_times[0]:
            time_parts = publish_times[0].split(':')
            self.default_hour = int(time_parts[0])
            self.default_minute = int(time_parts[1])
        else:
            self.default_hour = 10
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
    
    def _query_database(self, filter_obj: Optional[dict] = None) -> List[dict]:
        """查询 Notion 数据库"""
        url = f"{self.NOTION_API_BASE}/databases/{self.database_id}/query"
        
        payload = {"page_size": 100}
        if filter_obj:
            payload["filter"] = filter_obj
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
    
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
    
    def _match_local_video(self, title: str) -> Optional[Path]:
        """
        根据标题匹配本地视频文件
        
        匹配策略（按优先级）：
        1. 直接匹配：Cover 字段完全包含在文件夹名中
        2. 去除前缀匹配：去除常见日期前缀（YYMMDD, MMDD等）后匹配
        3. 模糊匹配：使用相似度匹配
        """
        if not self.videos_dir.exists():
            return None
        
        if not title:
            return None
        
        # 清理标题（去除前后空格）
        clean_title = title.strip()
        
        candidates = []  # (匹配得分, folder, video_path)
        
        for folder in self.videos_dir.iterdir():
            if not folder.is_dir():
                continue
            
            folder_name = folder.name.strip()
            
            # 获取视频文件
            video_files = list(folder.glob("*.mp4"))
            if not video_files:
                continue
            video_file = video_files[0]
            
            # 策略1：直接包含匹配（完全匹配或部分匹配）
            if clean_title in folder_name:
                # 完全匹配得分最高
                score = 100 if folder_name == clean_title else 90
                candidates.append((score, folder, video_file))
                continue
            
            # 策略2：去除常见前缀后匹配
            # 匹配模式：YYMMDD + 标题 或 MMDD + 标题 或 DD + 标题
            clean_folder = remove_date_prefix(folder_name)
            
            if clean_title in clean_folder or clean_folder in clean_title:
                score = 80
                candidates.append((score, folder, video_file))
                continue
            
            # 策略3：模糊匹配（计算相似度）
            similarity = calculate_similarity(clean_title, clean_folder)
            if similarity > 0.6:  # 60% 相似度阈值
                score = int(similarity * 70)  # 最高70分
                candidates.append((score, folder, video_file))
        
        # 按得分排序，返回得分最高的
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_match = candidates[0]
            print(f"✅ 匹配成功: '{title}' -> 文件夹 '{best_match[1].name}' (得分: {best_match[0]})")
            return best_match[2]
        
        print(f"⚠️ 未找到匹配的视频文件: '{title}'")
        return None
    
    def _match_local_cover(self, video_path: Path) -> Optional[str]:
        """匹配本地封面图"""
        folder = video_path.parent
        cover_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        for ext in cover_extensions:
            cover_files = list(folder.glob(f"*{ext}"))
            if cover_files:
                return str(cover_files[0])
        
        return None
    
    def _extract_property(self, page: dict, property_name: str) -> str:
        """从页面属性中提取值"""
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
        
        elif prop_type == "multi_select":
            # 多选类型，返回逗号分隔的字符串
            multi_select = prop.get("multi_select", [])
            return ", ".join([item.get("name", "") for item in multi_select if item.get("name")])
        
        elif prop_type == "select":
            # select 类型
            select_obj = prop.get("select", {})
            if select_obj:
                return select_obj.get("name", "")
            return ""
        
        elif prop_type == "checkbox":
            # checkbox 类型
            return prop.get("checkbox", False)
    
    def get_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """
        从本地 videos/ 文件夹扫描视频，然后去 Notion 查询匹配的信息
        
        支持两种视频存放方式：
        1. 子文件夹形式: videos/文件夹名/视频.mp4
        2. 直接存放: videos/视频.mp4
        
        流程：
        1. 扫描本地 videos/ 文件夹中的所有视频（包括子文件夹和直接存放）
        2. 对每个视频文件名（去除日期前缀），去 Notion 查找 Cover 字段匹配的记录
        3. 优先使用本地封面图（如果存在）
        4. 返回匹配成功的视频列表
        """
        if not self.videos_dir.exists():
            print(f"⚠️ 视频目录不存在: {self.videos_dir}")
            return []
        
        # 首先获取所有 Notion 记录（用于本地视频匹配）
        print("📡 正在从 Notion 获取视频信息...")
        
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
        
        print(f"📡 Notion API 返回 {len(pages)} 条原始记录")
        if pages:
            first_props = pages[0].get('properties', {})
            print(f"📄 第一条记录 properties 列表: {list(first_props.keys())}")
            # 查找 title 类型的属性
            for prop_name, prop_data in first_props.items():
                prop_type = prop_data.get('type', 'unknown')
                if prop_type == 'title':
                    title_items = prop_data.get('title', [])
                    title_text = ''.join([item.get('plain_text', '') for item in title_items])
                    print(f"   ⭐ {prop_name}: type={prop_type} → value='{title_text}'")
            # 打印所有 Name 提取结果
            for page in pages[:3]:
                props = page.get('properties', {})
                for prop_name, prop_data in props.items():
                    if prop_data.get('type') == 'title':
                        title_items = prop_data.get('title', [])
                        title_text = ''.join([item.get('plain_text', '') for item in title_items])
                        print(f"   📄 提取的 title: '{title_text}' (字段: {prop_name})")
        
        # 建立 Notion 记录索引（以 Name 字段为 key，用于匹配视频文件）
        notion_records = {}
        for page in pages:
            name_for_match = self._extract_property(page, "Name")
            if name_for_match:
                notion_records[name_for_match.strip()] = page
        
        print(f"📚 Notion 中共有 {len(notion_records)} 条视频记录")
        print(f"📋 Notion Name 列表: {list(notion_records.keys())}")
        
        # 扫描本地视频（两种方式）
        videos = []
        video_items = self._scan_videos()
        print(f"📁 本地 videos/ 中找到 {len(video_items)} 个视频")
        
        for video_file, container_name in video_items:
            # 在 Notion 中查找匹配的记录
            clean_title = remove_date_prefix(container_name)
            
            if not clean_title:
                print(f"⚠️ 无法解析标题: {container_name}")
                continue
            
            # 在 Notion 中查找匹配的记录
            notion_page = self._find_notion_record(clean_title, notion_records)
            
            if not notion_page:
                print(f"⚠️ Notion 中未找到匹配记录: '{clean_title}' (文件: {container_name})")
                continue
            
            # 提取 Notion 中的信息（新字段映射）
            # Name: 用于匹配本地视频文件名（Title 字段）
            # 短标题: 视频号短标题（16字以内）
            name_for_match = self._extract_property(notion_page, "Name")  # 用于匹配本地视频
            short_title = self._extract_property(notion_page, "短标题")  # 视频号短标题
            title = self._extract_property(notion_page, "标题")  # 视频号主标题
            description = self._extract_property(notion_page, "描述")  # 视频描述区内容
            tags = self._extract_property(notion_page, "标签")  # 话题标签
            collections_str = self._extract_property(notion_page, "合集")  # 合集名称
            date_str = self._extract_property(notion_page, "发布日期")
            cover_position = self._extract_property(notion_page, "封面调整") or "middle"  # select类型，默认middle
            original_declaration = self._extract_property(notion_page, "声明原创")  # checkbox类型
            
            # 使用 Name 字段进行匹配验证
            if not name_for_match:
                print(f"⚠️ Notion 记录缺少 Name 字段，跳过: '{clean_title}'")
                continue
            
            # 检查 发布日期 字段是否为空
            if not date_str:
                print(f"⚠️ Notion 记录缺少 发布日期 字段，跳过: '{clean_title}' (文件: {container_name})")
                print(f"   请在 Notion 中为该视频填写发布日期")
                continue
            
            # 处理合集名称列表（支持 multi_select）
            collections = []
            if collections_str:
                collections = [c.strip() for c in collections_str.split(",") if c.strip()]
            
            # 清理短标题（16字以内）
            final_short_title = sanitize_short_title(short_title if short_title else "")
            
            # 如果截断了，打印提示
            original = short_title if short_title else title
            if original and len(re.sub(r'[^\u4e00-\u9fa5]', '', original)) > 16:
                print(f"⚠️ 短标题超过16字已截断: '{original}' → '{final_short_title}'")
            
            # 视频号描述区逻辑：
            # 格式：标题 + 换行 + 描述 + 换行 + 标签（转换为 #开头格式）
            # 1. 如果描述中已包含以 # 开头的标签行，不再追加标签字段
            # 2. 如果描述中没有标签行，且标签字段存在，将标签追加到描述后面
            description_parts = []
            
            # 0. 添加标题（如果有）
            if title:
                description_parts.append(title)
                print(f"📝 已添加标题到描述区: {title}")
            
            # 转换标签格式：逗号分隔 -> #开头
            formatted_tags = ""
            if tags:
                # 处理逗号分隔的标签（支持中英文逗号）
                tag_list = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
                formatted_tags = ' '.join([f"#{tag}" for tag in tag_list])
            
            # 1. 添加描述（如果有）
            if description:
                description_parts.append(description)
                
                # 检查描述中是否已有标签行（以#开头的行）
                has_tag_in_desc = any(line.strip().startswith('#') for line in description.strip().split('\n'))
                if has_tag_in_desc:
                    # 描述中已包含标签行，不再追加标签字段
                    print(f"📝 描述已包含标签，跳过追加")
                elif formatted_tags:
                    # 描述中没有标签行，且有标签字段，追加格式化后的标签
                    description_parts.append(formatted_tags)
                    print(f"📝 已追加标签到描述: {formatted_tags}")
            elif formatted_tags:
                # 没有描述但有标签，只添加标签
                description_parts.append(formatted_tags)
                print(f"📝 已添加标签: {formatted_tags}")
            
            # 组装最终描述
            full_description = '\n'.join(description_parts) if description_parts else ""
            
            # 匹配本地封面图（优先使用本地封面）
            cover_path = self._match_local_cover(video_file)
            if cover_path:
                print(f"🖼️ 使用本地封面: {Path(cover_path).name}")
            
            # 解析日期和时间
            try:
                if 'T' in date_str:
                    publish_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_part = datetime.fromisoformat(date_str)
                    # 创建无时区的日期
                    publish_date = date_part.replace(hour=self.default_hour, minute=self.default_minute)
                # 确保日期是 offset-naive（无时区）
                if publish_date.tzinfo is not None:
                    publish_date = publish_date.replace(tzinfo=None)
            except Exception as e:
                print(f"⚠️ 日期解析失败 '{date_str}': {e}，跳过视频: '{clean_title}'")
                continue
            
            video_info = VideoInfo(
                title=title if title else short_title,  # 主标题
                short_title=final_short_title,  # 短标题（16字以内）
                description=full_description,  # 视频号描述区（描述+标签）
                tags=tags,  # 原始标签
                video_path=str(video_file),
                cover_path=cover_path,
                publish_date=publish_date,
                collections=collections,  # 合集名称列表
                original_declaration=bool(original_declaration) if original_declaration is not None else True,
                cover_position=cover_position,  # 封面调整位置
                name_for_match=name_for_match,  # 用于匹配的Name字段
                folder_name=container_name  # 文件夹名称
            )
            videos.append(video_info)
            print(f"✅ 匹配成功: '{clean_title}' -> 文件 '{container_name}'")
        
        print(f"\n🎬 共找到 {len(videos)} 个可上传视频")
        
        # 按日期从近到远排序（日期小的先发：11→12→13→14→15）
        videos.sort(key=lambda x: x.publish_date, reverse=False)
        
        print(f"\n找到 {len(videos)} 个视频（按上传顺序）：")
        for v in videos:
            print(f"- {v.title} ({v.publish_date.strftime('%Y-%m-%d %H:%M')})")
        
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
                    best_match, _ = select_best_matching_video(video_files, item.name, verbose=True)
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
                cover_position = self._extract_property(page, "封面调整") or "middle"
                original_declaration = self._extract_property(page, "声明原创")
                
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
                
                # 组装描述
                description_parts = []
                if title:
                    description_parts.append(title)
                if description:
                    description_parts.append(description)
                if tags:
                    tag_list = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
                    formatted_tags = ' '.join([f"#{tag}" for tag in tag_list])
                    description_parts.append(formatted_tags)
                
                full_description = '\n'.join(description_parts)
                
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
                    cover_position=cover_position
                )
                videos.append(video_info)
                
            except Exception as e:
                print(f"⚠️ 处理 Notion 记录时出错: {e}")
                continue
        
        print(f"✅ 从 Notion 获取到 {len(videos)} 条云端视频记录")
        
        # 按日期排序
        videos.sort(key=lambda x: x.publish_date, reverse=False)
        
        return videos


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
