"""
视频管理路由
提供视频扫描和预览接口
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from conf import BASE_DIR
from utils.match_utils import remove_date_prefix

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
VIDEOS_DIR = BASE_DIR / "videos"


class VideoInfo(BaseModel):
    id: str
    folder_name: str
    video_path: str
    title: str  # 合并后的标题（优先 Notion）
    short_title: str  # 合并后的短标题
    description: str  # 合并后的描述
    tags: str  # 合并后的标签
    formatted_tags: str = ""
    cover_path: Optional[str]
    cover_position: str = "middle"
    has_date_prefix: bool
    publish_date: Optional[str]
    publish_time: str = ""
    collection: str = ""
    collections: List[str] = []
    original_declaration: bool = True
    data_source: str = "local"  # local/notion/both
    location: str = ""
    music: str = ""
    mentions: str = ""
    # 本地数据源
    local_title: str = ""
    local_description: str = ""
    local_tags: str = ""
    has_local_data: bool = False
    # Notion 数据源
    notion_title: str = ""
    notion_description: str = ""
    notion_tags: str = ""
    has_notion_data: bool = False  # @提及


def extract_date_from_folder(folder_name: str) -> Optional[datetime]:
    """从文件夹名提取日期 (YYMMDD)"""
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


def get_local_videos_only() -> List[Dict[str, Any]]:
    """只获取本地视频数据（不涉及Notion）"""
    videos = []
    
    if not VIDEOS_DIR.exists():
        return videos
    
    # 读取 config.json
    import json
    config_path = BASE_DIR / "config.json"
    default_config = {
        "cover_position": "middle",
        "original_declaration": True,
        "collection": ""
    }
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except:
            pass
    
    for folder in VIDEOS_DIR.iterdir():
        if not folder.is_dir():
            continue
        
        # 查找视频文件
        video_files = list(folder.glob("*.mp4"))
        if not video_files:
            continue
        
        video_file = video_files[0]
        
        # 查找文本文件（本地数据源）
        txt_files = list(folder.glob("*.txt"))
        title = ""
        description = ""
        tags = ""
        
        if txt_files:
            with open(txt_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    title = lines[0].strip()
                    remaining = lines[1:]
                    if remaining:
                        content = ''.join(remaining).strip()
                        lines_list = content.split('\n')
                        if lines_list and lines_list[-1].startswith('#'):
                            tags = lines_list[-1]
                            description = '\n'.join(lines_list[:-1])
                        else:
                            description = content
        
        # 查找封面图
        cover_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
        
        # 提取日期
        folder_date = extract_date_from_folder(folder.name)
        
        has_local = bool(title or description or tags)
        config_collection = default_config.get("collection", "")
        
        videos.append({
            "id": folder.name,
            "folder_name": folder.name,
            "video_path": str(video_file.relative_to(BASE_DIR)),
            "title": title or folder.name,
            "short_title": title[:20] if len(title) > 20 else title or folder.name,
            "description": description,
            "tags": tags,
            "formatted_tags": tags,
            "cover_path": str(cover_files[0].relative_to(BASE_DIR)) if cover_files else None,
            "cover_position": default_config.get("cover_position", "middle"),
            "has_date_prefix": folder_date is not None,
            "publish_date": folder_date.strftime("%Y-%m-%d") if folder_date else None,
            "publish_time": default_config.get("publish_times", ["10:00"])[0] if isinstance(default_config.get("publish_times"), list) else "10:00",
            "use_notion_date": False,
            "collection": config_collection,
            "collections": [config_collection] if config_collection else [],
            "original_declaration": default_config.get("original_declaration", True),
            "data_source": "local",
            "location": "",
            "music": "",
            "mentions": "",
            "notion_publish_date": None,
            "local_title": title,
            "local_description": description,
            "local_tags": tags,
            "has_local_data": has_local,
            "notion_title": "",
            "notion_description": "",
            "notion_tags": "",
            "has_notion_data": False
        })
    
    videos.sort(key=lambda x: x["folder_name"])
    print(f"📋 本地模式：返回 {len(videos)} 个本地视频")
    return videos


def get_notion_videos_only() -> List[Dict[str, Any]]:
    """获取与本地视频匹配的Notion云端视频数据"""
    videos = []
    
    if not VIDEOS_DIR.exists():
        return videos
    
    # 读取 config.json
    import json
    import os
    config_path = BASE_DIR / "config.json"
    config = {
        "notion_api_token": "",
        "notion_database_id": "",
        "notion_database_name": ""
    }
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config.update(json.load(f))
        except:
            pass
    
    # 获取Notion数据
    notion_videos = {}
    if config.get("notion_api_token"):
        try:
            from data_sources.notion_data_source import NotionDataSource
            
            os.environ["NOTION_API_TOKEN"] = config["notion_api_token"]
            temp_config = {
                "notion_database_id": config.get("notion_database_id", ""),
                "notion_database_name": config.get("notion_database_name", "")
            }
            notion_source = NotionDataSource(temp_config)
            notion_data_list = notion_source.get_videos()
            
            for v in notion_data_list:
                key = v.name_for_match or v.short_title or v.title
                notion_videos[key] = v
            
            print(f"✅ 从 Notion 读取到 {len(notion_videos)} 条视频数据")
        except Exception as e:
            print(f"❌ 获取 Notion 数据失败: {e}")
    
    # 扫描本地视频文件夹，只保留有Notion匹配的
    for folder in VIDEOS_DIR.iterdir():
        if not folder.is_dir():
            continue
        
        # 查找视频文件
        video_files = list(folder.glob("*.mp4"))
        if not video_files:
            continue
        
        video_file = video_files[0]
        
        # 查找封面图
        cover_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
        
        # 尝试匹配Notion数据
        clean_folder_name = remove_date_prefix(folder.name)
        notion_data = None
        
        for key in [clean_folder_name, folder.name]:
            if key in notion_videos:
                notion_data = notion_videos[key]
                break
        
        # 如果没有精确匹配，尝试模糊匹配
        if not notion_data:
            for notion_key, nv in notion_videos.items():
                short_title = (nv.short_title or "").strip()
                if short_title and (short_title in clean_folder_name or short_title in folder.name):
                    notion_data = nv
                    break
        
        # 只添加有Notion匹配的视频
        if notion_data:
            # 处理日期时间
            notion_publish_date = getattr(notion_data, 'publish_date', None)
            date_missing = False
            time_defaulted = False
            
            if notion_publish_date:
                publish_date = notion_publish_date.strftime("%Y-%m-%d")
                # 检查是否有具体时间（不是00:00）
                if notion_publish_date.hour == 0 and notion_publish_date.minute == 0:
                    publish_time = "09:00"
                    time_defaulted = True
                else:
                    publish_time = notion_publish_date.strftime("%H:%M")
            else:
                publish_date = None
                publish_time = "09:00"
                date_missing = True
            
            # 组装描述
            description_parts = []
            if notion_data.title:
                description_parts.append(notion_data.title)
            if notion_data.tags:
                tag_list = [t.strip() for t in notion_data.tags.replace('，', ',').split(',') if t.strip()]
                formatted_tags = ' '.join([f"#{tag}" for tag in tag_list])
                description_parts.append(formatted_tags)
            
            full_description = '\n'.join(description_parts)
            
            videos.append({
                "id": folder.name,
                "folder_name": folder.name,
                "video_path": str(video_file.relative_to(BASE_DIR)),
                "title": notion_data.title or notion_data.short_title or folder.name,
                "short_title": notion_data.short_title,
                "description": full_description,
                "tags": notion_data.tags,
                "formatted_tags": formatted_tags if notion_data.tags else "",
                "cover_path": str(cover_files[0].relative_to(BASE_DIR)) if cover_files else None,
                "cover_position": notion_data.cover_position,
                "has_date_prefix": True,
                "publish_date": publish_date,
                "publish_time": publish_time,
                "use_notion_date": True,
                "collection": notion_data.collections[0] if notion_data.collections else "",
                "collections": notion_data.collections,
                "original_declaration": notion_data.original_declaration,
                "data_source": "notion",
                "location": "",
                "music": "",
                "mentions": "",
                "notion_publish_date": notion_publish_date.strftime("%Y-%m-%d %H:%M") if notion_publish_date else None,
                "local_title": "",
                "local_description": "",
                "local_tags": "",
                "has_local_data": False,
                "notion_title": notion_data.title,
                "notion_description": full_description,
                "notion_tags": notion_data.tags,
                "has_notion_data": True,
                "date_missing": date_missing,
                "time_defaulted": time_defaulted
            })
    
    videos.sort(key=lambda x: x["folder_name"])
    print(f"📋 云端模式：返回 {len(videos)} 个匹配视频（本地+Notion）")
    return videos


def scan_videos() -> List[Dict[str, Any]]:
    """扫描视频文件夹，支持本地和 Notion 数据源"""
    videos = []
    
    if not VIDEOS_DIR.exists():
        return videos
    
    # 读取 config.json 获取 Notion 配置
    import json
    import os
    config_path = BASE_DIR / "config.json"
    config = {
        "notion_api_token": "",
        "notion_database_id": "",
        "notion_database_name": "",
        "cover_position": "middle",
        "original_declaration": True,
        "collection": ""
    }
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except:
            pass
    
    # 尝试从 Notion 获取数据（如果配置了 token）
    notion_videos = {}
    try:
        from data_sources.notion_data_source import NotionDataSource
        
        print(f"🔑 Notion API Token: {'已配置' if config.get('notion_api_token') else '未配置'}")
        print(f"🔑 Notion Database ID: {config.get('notion_database_id', '未配置')}")
        
        if config.get("notion_api_token"):
            os.environ["NOTION_API_TOKEN"] = config["notion_api_token"]
            temp_config = {
                "notion_database_id": config.get("notion_database_id", ""),
                "notion_database_name": config.get("notion_database_name", "")
            }
            notion_source = NotionDataSource(temp_config)
            notion_data = notion_source.get_videos()
            for v in notion_data:
                # 使用 name_for_match 作为 key 来匹配本地视频（如 我的视频名称）
                key = v.name_for_match or v.short_title or v.title
                notion_videos[key] = v
            print(f"✅ 从 Notion 读取到 {len(notion_videos)} 条视频数据")
            print(f"📋 Notion keys: {list(notion_videos.keys())[:5]}...")
        else:
            print("⚠️ 未配置 Notion API Token，跳过云端数据获取")
    except Exception as e:
        print(f"Notion 数据源未启用或读取失败: {e}")
        import traceback
        traceback.print_exc()
    
    for folder in VIDEOS_DIR.iterdir():
        if not folder.is_dir():
            continue
        
        # 查找视频文件
        video_files = list(folder.glob("*.mp4"))
        if not video_files:
            continue
        
        video_file = video_files[0]
        
        # 查找文本文件（本地数据源）
        txt_files = list(folder.glob("*.txt"))
        title = ""
        description = ""
        tags = ""
        
        if txt_files:
            with open(txt_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    title = lines[0].strip()
                    remaining = lines[1:]
                    if remaining:
                        content = ''.join(remaining).strip()
                        lines_list = content.split('\n')
                        if lines_list and lines_list[-1].startswith('#'):
                            tags = lines_list[-1]
                            description = '\n'.join(lines_list[:-1])
                        else:
                            description = content
        
        # 查找封面图
        cover_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
        
        # 提取日期
        folder_date = extract_date_from_folder(folder.name)
        
        # 读取 config.json
        import json
        config_path = BASE_DIR / "config.json"
        default_config = {
            "cover_position": "middle",
            "original_declaration": True,
            "collection": ""
        }
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except:
                pass
        
        # 检查是否有 Notion 数据匹配
        clean_folder_name = remove_date_prefix(folder.name)
        match_key = clean_folder_name[:16] if len(clean_folder_name) > 16 else clean_folder_name
        
        # 尝试多种匹配方式
        notion_data = None
        for key in [match_key, clean_folder_name, folder.name]:
            if key in notion_videos:
                notion_data = notion_videos[key]
                break
        
        # 如果没有精确匹配，尝试模糊匹配（检查 short_title 是否包含在文件夹名中）
        if not notion_data:
            for notion_key, notion_video in notion_videos.items():
                short_title = (notion_video.short_title or "").strip()
                if short_title:
                    # 检查短标题是否包含在清理后的文件夹名中（忽略空格）
                    if short_title in clean_folder_name or short_title in folder.name:
                        notion_data = notion_video
                        print(f"  ✓ 模糊匹配成功: '{short_title}' 匹配 '{folder.name}'")
                        break
        
        # 判断数据来源
        has_local = bool(title or description or tags)
        has_notion = notion_data is not None
        
        if has_local and has_notion:
            data_source = "both"
            # 合并数据：Notion 优先，但保留本地数据
            final_title = notion_data.title or title
            final_short_title = notion_data.short_title or title[:20]
            final_description = notion_data.description or description
            final_tags = notion_data.tags or tags
            # 合集：本地配置优先，Notion 作为补充
            notion_collections = notion_data.collections if hasattr(notion_data, 'collections') else []
            config_collection = default_config.get("collection")
            if config_collection:
                # 本地配置优先，Notion 补充
                collections = [config_collection]
                if notion_collections and notion_collections != [config_collection]:
                    # 如果 Notion 有不同合集，合并显示
                    collections = list(set([config_collection] + notion_collections))
            else:
                collections = notion_collections if notion_collections else []
            location = getattr(notion_data, 'location', "")
            music = getattr(notion_data, 'music', "")
            mentions = getattr(notion_data, 'mentions', "")
            # 封面调整和原创声明：使用 Notion 数据
            cover_position = getattr(notion_data, 'cover_position', "middle")
            original_declaration = getattr(notion_data, 'original_declaration', True)
            
            # 发布日期：优先使用 Notion 的 publish_date
            notion_publish_date = getattr(notion_data, 'publish_date', None)
            if notion_publish_date:
                publish_date = notion_publish_date.strftime("%Y-%m-%d")
                publish_time = notion_publish_date.strftime("%H:%M")
                use_notion_date = True
            else:
                # Notion 发布日期为空，使用本地配置
                publish_date = folder_date.strftime("%Y-%m-%d") if folder_date else None
                publish_time = default_config.get("publish_times", ["10:00"])[0] if isinstance(default_config.get("publish_times"), list) else "10:00"
                use_notion_date = False
                print(f"⚠️ 警告: '{folder.name}' Notion 发布日期为空，使用本地配置时间")
                
        elif has_notion:
            data_source = "notion"
            # 云端模式：只使用 Notion 数据，不使用本地配置
            final_title = notion_data.title or title
            final_short_title = notion_data.short_title or title[:20]
            final_description = notion_data.description or description
            final_tags = notion_data.tags or tags
            # 合集：只使用 Notion 数据
            collections = notion_data.collections if hasattr(notion_data, 'collections') else []
            location = getattr(notion_data, 'location', "")
            music = getattr(notion_data, 'music', "")
            mentions = getattr(notion_data, 'mentions', "")
            # 声明原创：使用 Notion 数据
            original_declaration = getattr(notion_data, 'original_declaration', True)
            # 封面调整：使用 Notion 数据
            cover_position = getattr(notion_data, 'cover_position', "middle")
            # 合集配置
            config_collection = ""
            
            # 发布日期：只使用 Notion 的 publish_date
            notion_publish_date = getattr(notion_data, 'publish_date', None)
            if notion_publish_date:
                publish_date = notion_publish_date.strftime("%Y-%m-%d")
                publish_time = notion_publish_date.strftime("%H:%M")
                use_notion_date = True
            else:
                # Notion 发布日期为空，使用文件夹日期
                publish_date = folder_date.strftime("%Y-%m-%d") if folder_date else None
                publish_time = "10:00"
                use_notion_date = False
                print(f"⚠️ 警告: '{folder.name}' Notion 发布日期为空")
                
        else:
            # 使用本地数据
            data_source = "local"
            final_title = title
            final_short_title = title[:20] if len(title) > 20 else title
            final_description = description
            final_tags = tags
            config_collection = default_config.get("collection", "")
            collections = [config_collection] if config_collection else []
            location = ""
            music = ""
            mentions = ""
            publish_date = folder_date.strftime("%Y-%m-%d") if folder_date else None
            publish_time = default_config.get("publish_times", ["10:00"])[0] if isinstance(default_config.get("publish_times"), list) else "10:00"
            use_notion_date = False
            cover_position = default_config.get("cover_position", "middle")
            original_declaration = default_config.get("original_declaration", True)
        
        videos.append({
            "id": folder.name,
            "folder_name": folder.name,
            "video_path": str(video_file.relative_to(BASE_DIR)),
            "title": final_title or folder.name,
            "short_title": final_short_title or folder.name,
            "description": final_description,
            "tags": final_tags,
            "formatted_tags": final_tags,
            "cover_path": str(cover_files[0].relative_to(BASE_DIR)) if cover_files else None,
            "cover_position": cover_position,
            "has_date_prefix": folder_date is not None,
            "publish_date": publish_date,
            "publish_time": publish_time,
            "use_notion_date": use_notion_date,
            "collection": config_collection if has_notion else default_config.get("collection", ""),
            "collections": collections,
            "original_declaration": original_declaration,
            "data_source": data_source,
            "location": location,
            "music": music,
            "mentions": mentions,
            "notion_publish_date": notion_publish_date.strftime("%Y-%m-%d %H:%M") if (has_notion and notion_publish_date) else None,
            # 本地数据源
            "local_title": title,
            "local_description": description,
            "local_tags": tags,
            "has_local_data": has_local,
            # Notion 数据源
            "notion_title": notion_data.title if notion_data else "",
            "notion_description": notion_data.description if notion_data else "",
            "notion_tags": notion_data.tags if notion_data else "",
            "has_notion_data": has_notion
        })
    
    videos.sort(key=lambda x: x["folder_name"])
    return videos


@router.get("", response_model=List[VideoInfo])
async def get_videos(source: str = Query(default="all", description="数据源筛选: local/notion/all")):
    """获取视频列表
    
    Args:
        source: 数据源筛选
            - "all": 返回所有视频（本地+云端混合）
            - "local": 只返回本地视频数据（不涉及Notion）
            - "notion": 只返回Notion云端数据（不扫描本地）
    """
    try:
        if source == "local":
            # 只返回本地视频
            return get_local_videos_only()
        elif source == "notion":
            # 只返回Notion云端视频
            return get_notion_videos_only()
        else:
            # all模式：扫描本地并匹配Notion（原有逻辑）
            return scan_videos()
    except Exception as e:
        import traceback
        print(f"❌ 扫描视频失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"扫描视频失败: {str(e)}")


@router.get("/{video_id}")
async def get_video_detail(video_id: str):
    """获取单个视频详情"""
    videos = scan_videos()
    for video in videos:
        if video["id"] == video_id:
            return video
    raise HTTPException(status_code=404, detail="视频未找到")


@router.get("/stats/count")
async def get_video_stats():
    """获取视频统计信息"""
    videos = scan_videos()
    return {
        "total": len(videos),
        "with_cover": sum(1 for v in videos if v["cover_path"]),
        "with_description": sum(1 for v in videos if v["description"]),
        "with_date_prefix": sum(1 for v in videos if v["has_date_prefix"])
    }
