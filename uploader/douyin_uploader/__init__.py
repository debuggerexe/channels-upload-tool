"""抖音视频号上传器

提供抖音创作者中心的视频上传功能，支持：
- Cookie 验证与生成
- 视频上传
- 定时发布
- 封面上传
- 地理位置设置
- 同步到头条/西瓜视频
"""

from .main import DouYinVideo, douyin_setup, cookie_auth

__all__ = ['DouYinVideo', 'douyin_setup', 'cookie_auth']
