#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取抖音 Cookie

用法：
    python examples/get_douyin_cookie.py

说明：
    运行后会自动打开浏览器并跳转到抖音创作者中心登录页面。
    请使用抖音 APP 扫码登录。
    登录完成后，在浏览器开发者工具中点击继续，Cookie 将自动保存。

Cookie 保存位置：
    cookies/douyin/account.json
"""

import sys
import asyncio
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup, DOUYIN_ACCOUNT_FILE


if __name__ == '__main__':
    # 确保目录存在
    DOUYIN_ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("抖音 Cookie 获取工具")
    print("=" * 60)
    print(f"\nCookie 将保存到: {DOUYIN_ACCOUNT_FILE}")
    print("\n操作步骤:")
    print("1. 即将自动打开浏览器并跳转到抖音创作者中心")
    print("2. 使用抖音 APP 扫码登录")
    print("3. 登录成功后，在浏览器开发者工具中点击继续")
    print("4. Cookie 将自动保存到指定位置")
    print("=" * 60)
    
    # 执行登录流程
    cookie_setup = asyncio.run(douyin_setup(str(DOUYIN_ACCOUNT_FILE), handle=True))
    
    if cookie_setup:
        print("\n✅ Cookie 获取成功！")
        print(f"您可以运行上传脚本了: python upload_douyin_videos.py --mode local")
    else:
        print("\n❌ Cookie 获取失败，请重试")
