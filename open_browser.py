#!/usr/bin/env python
"""
打开微信视频号或抖音创作者中心浏览器
使用此脚本可以预先打开浏览器并保持登录状态，然后手动上传视频

用法:
    python open_browser.py [platform]
    
参数:
    platform: 平台名称，可选 'tencent'(默认) 或 'douyin'

示例:
    python open_browser.py           # 打开视频号
    python open_browser.py tencent   # 打开视频号
    python open_browser.py douyin    # 打开抖音
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from conf import BASE_DIR as PROJECT_BASE_DIR


# 平台配置
PLATFORMS = {
    'tencent': {
        'name': '微信视频号',
        'cookie_file': 'cookies/tencent/account.json',
        'cookie_example': 'examples/get_tencent_cookie.py',
        'url': 'https://channels.weixin.qq.com/platform/post/create',
        'setup_func': None,  # 将在函数内动态导入
    },
    'douyin': {
        'name': '抖音创作者中心',
        'cookie_file': 'cookies/douyin/account.json',
        'cookie_example': 'examples/get_douyin_cookie.py',
        'url': 'https://creator.douyin.com/creator-micro/content/upload',
        'setup_func': None,
    }
}


async def open_browser(platform: str):
    """打开已登录的浏览器"""
    config = PLATFORMS.get(platform)
    if not config:
        print(f"错误: 不支持的平台: {platform}")
        print(f"支持的平台: {', '.join(PLATFORMS.keys())}")
        return
    
    account_file = str(PROJECT_BASE_DIR / config['cookie_file'])
    
    if not os.path.exists(account_file):
        print(f"错误: 账号文件不存在: {account_file}")
        print(f"请先运行 {config['cookie_example']} 获取cookie")
        return
    
    # 动态导入对应平台的 set_init_script
    if platform == 'tencent':
        from uploader.tencent_uploader.main import set_init_script
    else:
        from uploader.douyin_uploader.main import set_init_script
    
    print("="*60)
    print(f"打开{config['name']}浏览器")
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
        
        # 创建页面并打开目标网站
        page = await context.new_page()
        await page.goto(config['url'])
        
        print("✅ 浏览器已打开并登录")
        print(f"   当前平台: {config['name']}")
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


def select_platform():
    """交互式选择平台"""
    print("="*60)
    print("请选择要打开的平台:")
    print("="*60)
    print("1. 微信视频号")
    print("2. 抖音创作者中心")
    print("="*60)
    
    while True:
        choice = input("\n请输入选项 (1/2): ").strip()
        if choice == '1':
            return 'tencent'
        elif choice == '2':
            return 'douyin'
        else:
            print("无效选项，请重新输入")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='打开已登录的浏览器，支持视频号和抖音')
    parser.add_argument('--tencent', action='store_true', help='打开微信视频号')
    parser.add_argument('--douyin', action='store_true', help='打开抖音创作者中心')
    args = parser.parse_args()
    
    # 判断平台选择
    if args.tencent:
        platform = 'tencent'
    elif args.douyin:
        platform = 'douyin'
    else:
        # 如果没有传参数，进入交互选择
        platform = select_platform()
    
    try:
        asyncio.run(open_browser(platform))
    except KeyboardInterrupt:
        print("\n脚本被用户中断")
        sys.exit(0)
