#!/usr/bin/env python
"""
打开微信视频号登录浏览器
使用此脚本可以预先打开浏览器并保持登录状态，然后手动上传视频
"""

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from conf import BASE_DIR as PROJECT_BASE_DIR
from uploader.tencent_uploader.main import weixin_setup, set_init_script


async def open_logged_in_browser():
    """打开已登录的浏览器"""
    account_file = str(PROJECT_BASE_DIR / "cookies" / "tencent_uploader" / "account.json")
    
    if not os.path.exists(account_file):
        print(f"错误: 账号文件不存在: {account_file}")
        print("请先运行 examples/get_tencent_cookie.py 获取cookie")
        return
    
    print("="*60)
    print("打开微信视频号浏览器")
    print("="*60)
    print("\n提示:")
    print("  • 浏览器将保持打开状态")
    print("  • 您可以手动上传视频或进行其他操作")
    print("  • 完成后直接关闭浏览器窗口即可")
    print("  • 按 Ctrl+C 可以终止此脚本（不会影响浏览器）")
    print("="*60 + "\n")
    
    async with async_playwright() as playwright:
        # 启动浏览器
        try:
            browser = await playwright.chromium.launch(
                headless=False,
                channel="chrome"
            )
        except Exception as e:
            print(f"启动 Chrome 失败: {e}")
            print("尝试使用 Chromium...")
            browser = await playwright.chromium.launch(headless=False)
        
        # 创建上下文
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        
        # 创建页面并打开视频号
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        
        print("✅ 浏览器已打开并登录")
        print("   您可以手动操作浏览器上传视频")
        print("   关闭浏览器窗口或按 Ctrl+C 结束此脚本\n")
        
        # 等待浏览器关闭或用户按 Ctrl+C
        try:
            # 保持脚本运行
            while True:
                # 检查浏览器是否还开着
                try:
                    pages = context.pages
                    if len(pages) == 0:
                        print("\n浏览器已关闭，脚本退出")
                        break
                    await asyncio.sleep(1)
                except Exception:
                    print("\n浏览器连接断开，脚本退出")
                    break
        except KeyboardInterrupt:
            print("\n\n收到 Ctrl+C，关闭浏览器...")
        finally:
            try:
                await context.close()
                await browser.close()
            except Exception:
                pass
            print("脚本已退出")


if __name__ == "__main__":
    try:
        asyncio.run(open_logged_in_browser())
    except KeyboardInterrupt:
        print("\n脚本被用户中断")
        sys.exit(0)
