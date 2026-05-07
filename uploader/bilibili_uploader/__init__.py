"""
Bilibili 上传器模块
基于 biliup 库实现视频上传功能
"""
from pathlib import Path
from conf import BASE_DIR

# 确保 Bilibili Cookie 目录存在
Path(BASE_DIR / "cookies" / "bilibili").mkdir(exist_ok=True, parents=True)
