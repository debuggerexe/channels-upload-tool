"""
配置管理路由
提供 config.json 的读写接口
"""

import json
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

# 默认配置（中性值，用户应在 config.json 中配置个性化内容）
DEFAULT_CONFIG = {
    "publish_date": "2026-04-03",
    "publish_times": ["11:11"],
    "timezone": "Asia/Shanghai",
    "video_dir": "videos",
    "text_dir": "texts",
    "original_declaration": True,
    "cover_position": "bottom",
    "collection": "",  # 用户合集名称，在 config.json 中配置
    "notion_api_token": "",  # Notion API Token，在 config.json 或环境变量中配置
    "notion_database_id": "",  # Notion 数据库 ID
    "notion_database_name": ""  # Notion 数据库名称
}


class ConfigModel(BaseModel):
    publish_date: str
    publish_times: list[str]
    timezone: str
    video_dir: str
    text_dir: str
    original_declaration: bool
    cover_position: str
    collection: str
    notion_api_token: str = ""  # Notion API Token
    notion_database_id: str
    notion_database_name: str


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """保存配置文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


@router.get("")
async def get_config():
    """获取当前配置"""
    return load_config()


@router.post("")
async def update_config(config: ConfigModel):
    """更新配置"""
    try:
        save_config(config.dict())
        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/test_notion")
async def test_notion_connection(config: dict):
    """测试 Notion 连接"""
    try:
        from data_sources.notion_data_source import NotionDataSource
        import os
        
        # 临时设置 token
        token = config.get("notion_api_token")
        if not token:
            return {"success": False, "message": "请先填写 Notion API Token"}
        
        os.environ["NOTION_API_TOKEN"] = token
        
        # 构建临时配置
        temp_config = {
            "notion_database_id": config.get("notion_database_id", ""),
            "notion_database_name": config.get("notion_database_name", "")
        }
        
        notion_source = NotionDataSource(temp_config)
        videos = notion_source.get_videos()
        
        return {
            "success": True, 
            "message": f"连接成功！从 Notion 读取到 {len(videos)} 条视频数据",
            "count": len(videos)
        }
    except Exception as e:
        error_msg = str(e)
        # 确保错误消息是字符串
        if isinstance(error_msg, bytes):
            error_msg = error_msg.decode('utf-8', errors='replace')
        return {"success": False, "message": f"连接失败: {error_msg}"}
