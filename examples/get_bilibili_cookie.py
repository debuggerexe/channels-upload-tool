#!/usr/bin/env python3
"""
获取 Bilibili Cookie 示例脚本

使用方法:
    python examples/get_bilibili_cookie.py

说明:
    1. 脚本会打开浏览器访问 Bilibili 登录页面
    2. 手动登录你的 Bilibili 账号
    3. 登录成功后，按回车键保存 Cookie
    4. Cookie 将保存到 cookies/bilibili/account.json

注意:
    - 需要安装 playwright: pip install playwright
    - 需要安装浏览器: playwright install chromium
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# 添加项目根目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from conf import BASE_DIR


def save_cookies(context, save_path: Path):
    """保存浏览器存储状态（包含 Cookie）"""
    # 获取存储状态
    storage_state = context.storage_state()
    
    # 确保目录存在
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存到文件
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(storage_state, f, indent=2, ensure_ascii=False)
    
    print(f"Cookie 已保存到: {save_path}")


def main():
    cookie_path = Path(BASE_DIR) / "cookies" / "bilibili" / "account.json"
    
    print("=" * 60)
    print("Bilibili Cookie 获取工具")
    print("=" * 60)
    print()
    print("操作步骤:")
    print("1. 浏览器将自动打开 Bilibili 登录页面")
    print("2. 请手动登录你的 Bilibili 账号")
    print("3. 登录成功后，返回此窗口按回车键保存 Cookie")
    print()
    print(f"Cookie 将保存到: {cookie_path}")
    print("=" * 60)
    print()
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        
        # 创建新的浏览器上下文
        context = browser.new_context()
        
        # 创建新页面
        page = context.new_page()
        
        # 访问 Bilibili 登录页面
        print("正在打开 Bilibili 登录页面...")
        page.goto("https://www.bilibili.com")
        
        # 等待用户登录
        print("请在新打开的浏览器窗口中登录 Bilibili 账号")
        print("登录完成后，按回车键保存 Cookie...")
        input()
        
        # 验证登录状态
        try:
            # 检查是否有登录标识
            page.goto("https://api.bilibili.com/x/web-interface/nav")
            time.sleep(2)
            
            # 保存 Cookie
            save_cookies(context, cookie_path)
            
            print()
            print("✅ Cookie 保存成功!")
            print(f"路径: {cookie_path}")
            print()
            print("你现在可以使用 upload_bilibili_videos.py 上传视频了")
            
        except Exception as e:
            print(f"❌ 保存 Cookie 时出错: {e}")
        
        finally:
            # 关闭浏览器
            browser.close()


if __name__ == "__main__":
    main()
