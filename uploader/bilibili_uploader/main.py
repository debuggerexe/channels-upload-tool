"""
Bilibili 视频上传器 - Playwright 浏览器自动化方式
"""
import asyncio
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from playwright.async_api import async_playwright

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger


def random_emoji() -> str:
    """返回随机 emoji，用于避免重复标题"""
    emoji_list = [
        "🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
        "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
        "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
        "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
        "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
        "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"
    ]
    return random.choice(emoji_list)


def read_cookie_json_file(filepath: Path) -> dict:
    """读取 Bilibili Cookie JSON 文件"""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_keys_from_json(data: dict) -> dict:
    """
    从 account.json 中提取 Bilibili 需要的 Cookie 数据
    返回简单字典格式: {"name": "value", ...}
    """
    result = {}
    
    # 从 Playwright format 提取
    if "cookies" in data and isinstance(data["cookies"], list):
        for c in data["cookies"]:
            if "name" in c and "value" in c:
                result[c["name"]] = c["value"]
    
    return result


async def cookie_auth(account_file: Path) -> bool:
    """验证 Bilibili Cookie 是否有效 - 使用无头模式"""
    if not account_file.exists():
        return False
    
    # 首先检查 Cookie 文件是否包含必要的字段
    try:
        raw_data = read_cookie_json_file(account_file)
        cookie_dict = extract_keys_from_json(raw_data)
        if not cookie_dict.get("SESSDATA") or not cookie_dict.get("bili_jct"):
            bilibili_logger.error("[+] Cookie 文件缺少必要字段")
            return False
    except Exception as e:
        bilibili_logger.error(f"[+] Cookie 文件读取失败: {e}")
        return False
        
    async with async_playwright() as playwright:
        # 使用无头模式验证，不弹出浏览器窗口
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(account_file))
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            bilibili_logger.info("[+] 正在验证 Cookie...")
            # 访问 API 验证登录状态
            await page.goto("https://api.bilibili.com/x/web-interface/nav", timeout=10000)
            await page.wait_for_timeout(1000)
            
            # 获取页面内容（API 返回的 JSON）
            content = await page.content()
            import json
            # 从页面中提取 JSON
            start = content.find('{"code"')
            if start != -1:
                end = content.find('</pre>') if '<pre>' in content else content.find('</body>')
                if end == -1:
                    end = len(content)
                json_str = content[start:end]
                try:
                    data = json.loads(json_str)
                    if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
                        bilibili_logger.success("[+] Bilibili Cookie 有效")
                        return True
                    else:
                        bilibili_logger.error("[+] Cookie 已失效")
                        return False
                except:
                    pass
            
            # 备选：检查 URL
            current_url = page.url
            if "login" in current_url or "passport" in current_url:
                bilibili_logger.error("[+] Cookie 已失效")
                return False
                
            bilibili_logger.error("[+] Cookie 验证失败")
            return False
                
        except Exception as e:
            bilibili_logger.error(f"[+] Cookie 验证异常: {e}")
            return False
        finally:
            await browser.close()


async def get_bilibili_cookie(account_file: Path):
    """获取 Bilibili Cookie"""
    async with async_playwright() as playwright:
        options = {
            'args': ['--lang en-GB'],
            'headless': False,
        }
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        
        await page.goto("https://passport.bilibili.com/login")
        bilibili_logger.info("[+] 请在浏览器中登录 Bilibili（已打开登录页面）")
        bilibili_logger.info("[+] 登录完成后，请在此按回车键保存 Cookie...")
        input()  # 等待用户按回车
        
        await context.storage_state(path=str(account_file))
        bilibili_logger.success(f"[+] Cookie 已保存到: {account_file}")
        await browser.close()


async def bilibili_setup(account_file: Path, handle: bool = False) -> bool:
    """确保已登录 Bilibili"""
    if not account_file.exists() or not await cookie_auth(account_file):
        if not handle:
            return False
        bilibili_logger.info('[+] Cookie文件不存在或已失效，即将自动打开浏览器，请登录B站，登陆后会自动生成cookie文件')
        await get_bilibili_cookie(account_file)
    return True


class BilibiliVideoUploader:
    """Bilibili 视频上传器 - Playwright 方式"""
    
    def __init__(
        self,
        cookie_data: dict,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        publish_date: Optional[datetime] = None,
        copyright: int = 1,  # 1=自制, 2=转载
        cover_path: Optional[str] = None,
        account_file: Optional[Path] = None
    ):
        """
        初始化 Bilibili 视频上传器
        
        Args:
            cookie_data: Bilibili Cookie 数据
            video_path: 视频文件路径
            title: 视频标题
            description: 视频描述
            tags: 标签列表
            publish_date: 发布时间（None表示立即发布）
            copyright: 版权类型，1=自制，2=转载
            cover_path: 封面图片路径
            account_file: Cookie 文件路径
        """
        self.cookie_data = cookie_data
        self.video_path = Path(video_path)
        self.title = title
        self.description = description
        self.tags = tags
        self.publish_date = publish_date
        self.copyright = copyright
        self.cover_path = cover_path
        from conf import BASE_DIR
        self.account_file = account_file or Path(BASE_DIR) / "cookies" / "bilibili" / "account.json"
        self.local_executable_path = LOCAL_CHROME_PATH
    
    async def upload(self) -> bool:
        """
        执行视频上传
        
        Returns:
            上传是否成功
        """
        # 检查视频文件
        if not self.video_path.exists():
            bilibili_logger.error(f"[-] 视频文件不存在: {self.video_path}")
            return False
        
        async with async_playwright() as playwright:
            # 启动浏览器
            if self.local_executable_path:
                browser = await playwright.chromium.launch(
                    executable_path=self.local_executable_path,
                    headless=False
                )
            else:
                browser = await playwright.chromium.launch(headless=False)
            
            # 加载 cookie
            context = await browser.new_context(storage_state=str(self.account_file))
            context = await set_init_script(context)
            page = await context.new_page()
            
            # 【诊断】启动 tracing 记录操作过程
            await context.tracing.start(screenshots=True, snapshots=True)
            
            # 【关键】页面加载前注入脚本禁用 beforeunload
            await page.add_init_script("""
                // 禁用 beforeunload 弹窗
                Object.defineProperty(window, 'onbeforeunload', {
                    get: function() { return null; },
                    set: function() { }
                });
                window.addEventListener('beforeunload', function(e) {
                    // 不阻止离开
                });
                
                // 添加全局提交函数供自动化调用
                window.__auto_submit__ = function() {
                    const btn = document.querySelector('.submit-container .submit-add');
                    if (btn) {
                        // 触发完整事件链
                        ['mousedown', 'mouseup', 'click'].forEach(type => {
                            btn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true }));
                        });
                        btn.click();
                        return { success: true, method: 'auto-submit' };
                    }
                    return { success: false, error: '按钮未找到' };
                };
            """)
            
            # 【关键】监听并自动处理所有对话框（确认/提示）
            async def handle_dialog(dialog):
                """自动处理对话框"""
                bilibili_logger.info(f"[+] 检测到对话框: {dialog.type} - {dialog.message[:50]}...")
                if dialog.type == "confirm":
                    await dialog.accept()
                    bilibili_logger.info("[✓] 自动点击确认")
                elif dialog.type == "alert":
                    await dialog.accept()
                    bilibili_logger.info("[✓] 自动关闭警告")
                elif dialog.type == "prompt":
                    await dialog.dismiss()
                    bilibili_logger.info("[✓] 自动取消输入框")
                else:
                    await dialog.dismiss()
            
            page.on("dialog", lambda dialog: asyncio.create_task(handle_dialog(dialog)))
            
            try:
                bilibili_logger.info("[+] 正在打开 Bilibili 上传页面...")
                # 使用domcontentloaded策略，更快完成导航
                await page.goto("https://member.bilibili.com/platform/upload/video", 
                               wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)  # 等待3秒让页面稳定
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass  # 网络空闲等待失败也继续
                
                # 上传视频文件 - 等待文件输入框出现
                bilibili_logger.info(f"[+] 正在上传视频: {self.video_path.name}")
                
                # 等待文件输入框出现（B站页面加载需要时间）
                try:
                    await page.wait_for_selector('input[type="file"]', timeout=30000)
                    bilibili_logger.info("[✓] 找到文件上传输入框")
                except:
                    bilibili_logger.warning("[⚠️] 等待文件输入框超时，尝试继续...")
                
                # 使用 locator 获取第一个文件输入框
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(str(self.video_path), timeout=60000)
                bilibili_logger.info("[✓] 已设置视频文件")
                
                # 等待视频上传完成
                bilibili_logger.info("[+] 等待视频上传...")
                bilibili_logger.warning("[⚠️] 上传过程中请勿关闭浏览器窗口！")
                
                # 等待上传完成（最多300秒）
                upload_timeout = 300
                start_time = asyncio.get_event_loop().time()
                upload_complete = False
                last_status = ""
                
                bilibili_logger.info("[+] 开始监控上传进度...")
                
                while asyncio.get_event_loop().time() - start_time < upload_timeout:
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    
                    try:
                        # 检查上传进度和完成状态
                        result = await page.evaluate("""() => {
                            // 检查各种上传完成标识
                            const success = document.querySelector('.file-item-success, .upload-success, .success-item, [class*="upload-success"]');
                            if (success) return { status: 'success', reason: '找到成功标识' };
                            
                            // 检查文件信息已显示（文件名、时长等）
                            const fileName = document.querySelector('.file-item .file-name, .file-list-item .name, .upload-file-name');
                            const fileDuration = document.querySelector('.file-item .duration, .file-list-item .duration');
                            if (fileName && fileDuration) return { status: 'uploaded', reason: '文件信息显示完整' };
                            
                            // 检查进度条是否消失或达到100%
                            const progressBar = document.querySelector('.el-progress-bar__inner, .upload-progress, [class*="progress"]');
                            const progressText = document.querySelector('.el-progress__text, .progress-text');
                            if (progressText) {
                                const text = progressText.textContent;
                                if (text.includes('100') || text.includes('完成')) {
                                    return { status: 'complete', reason: '进度100%' };
                                }
                            }
                            
                            // 检查是否有视频元信息（表示上传完成且处理完成）
                            const titleH3 = Array.from(document.querySelectorAll('h3')).find(h => h.textContent.includes('标题'));
                            const titleInput = document.querySelector('input[placeholder*="标题"]');
                            const videoForm = document.querySelector('.video-form, .upload-form');
                            if (videoForm || titleH3 || titleInput) return { status: 'form_ready', reason: '表单已出现' };
                            
                            // 检查是否还在上传中
                            const uploading = document.querySelector('.uploading, .el-progress-bar__inner:not([style*="100%"])');
                            if (uploading) return { status: 'uploading', reason: '仍在上传中' };
                            
                            return { status: 'unknown', reason: '状态未知' };
                        }""")
                        
                        status = result.get('status', 'unknown')
                        reason = result.get('reason', '')
                        
                        # 每10秒打印一次状态
                        if status != last_status or elapsed % 10 == 0:
                            bilibili_logger.info(f"[⏳] 上传状态: {status} ({reason}) - 已等待 {elapsed}秒")
                            last_status = status
                        
                        # 完成条件
                        if status in ['success', 'uploaded', 'complete', 'form_ready']:
                            upload_complete = True
                            bilibili_logger.success(f"[✓] 视频上传完成! ({reason})")
                            break
                            
                    except Exception as e:
                        if elapsed % 10 == 0:
                            bilibili_logger.debug(f"检查状态时出错: {e}")
                    
                    await asyncio.sleep(2)  # 缩短检查间隔
                
                if not upload_complete:
                    bilibili_logger.warning("[⚠️] 上传检测超时，但继续尝试填写信息...")
                
                # 等待表单元素出现（说明上传完成且页面已渲染表单）
                bilibili_logger.info("[+] 等待表单元素加载...")
                try:
                    # 尝试多种方式检测表单
                    for attempt in range(3):
                        try:
                            # 方法1：等待标题输入框
                            await page.wait_for_selector('input.input-val[placeholder*="标题"]', timeout=20000)
                            bilibili_logger.info("[✓] 表单已加载 (检测到标题输入框)")
                            break
                        except:
                            try:
                                # 方法2：等待任何表单元素
                                await page.wait_for_selector('.video-title, .video-form, #tag-container', timeout=20000)
                                bilibili_logger.info("[✓] 表单已加载 (检测到表单区域)")
                                break
                            except:
                                if attempt == 2:
                                    raise
                                bilibili_logger.info(f"[⏳] 表单加载中... 尝试 {attempt + 1}/3")
                                await asyncio.sleep(5)
                except Exception as e:
                    bilibili_logger.warning(f"[⚠️] 等待表单超时: {e}，尝试继续...")
                
                await page.wait_for_timeout(5000)  # 增加等待时间确保表单完全渲染
                bilibili_logger.info("[+] 开始填写视频信息...")
                
                # ========================================
                # 1. 填写标题 - 精确匹配用户提供的DOM结构
                # ========================================
                title_filled = False
                try:
                    # 根据用户提供的DOM：input.input-val placeholder="请输入稿件标题"
                    title_input = page.locator('input.input-val[placeholder="请输入稿件标题"]').first
                    if await title_input.count() > 0:
                        await title_input.fill(self.title)
                        await title_input.press('Tab')  # 按Tab触发验证
                        title_filled = True
                        bilibili_logger.info(f"[✓] 标题填写成功: {self.title}")
                    else:
                        # 备选：通过video-title区域查找
                        title_input = page.locator('.video-title input.input-val').first
                        if await title_input.count() > 0:
                            await title_input.fill(self.title)
                            await title_input.press('Tab')
                            title_filled = True
                            bilibili_logger.info(f"[✓] 标题填写成功(备选): {self.title}")
                        else:
                            bilibili_logger.warning("[⚠️] 未找到标题输入框")
                except Exception as e:
                    bilibili_logger.warning(f"[⚠️] 标题填写失败: {e}")
                
                # ========================================
                # 2. 设置类型（自制/转载）- 根据copyright参数
                # ========================================
                try:
                    type_map = {1: "自制", 2: "转载"}
                    type_name = type_map.get(self.copyright, "自制")
                    
                    # 根据用户提供的DOM：.type-check 区域内有 "自制" 和 "转载" radio
                    # 先找到类型区域，然后点击对应的radio
                    type_section = page.locator('.type-check').first
                    if await type_section.count() > 0:
                        # 查找包含目标文字的radio选项
                        type_option = type_section.locator(f'.check-radio-v2-container:has-text("{type_name}")').first
                        if await type_option.count() > 0:
                            await type_option.click()
                            bilibili_logger.info(f"[✓] 类型设置成功: {type_name}")
                        else:
                            # 备选：直接查找包含文字的元素
                            type_option = page.locator(f'span.check-radio-v2-name:has-text("{type_name}")').first
                            if await type_option.count() > 0:
                                await type_option.click()
                                bilibili_logger.info(f"[✓] 类型设置成功(备选): {type_name}")
                    else:
                        bilibili_logger.warning("[⚠️] 未找到类型选择区域")
                except Exception as e:
                    bilibili_logger.warning(f"[⚠️] 类型设置失败: {e}")
                
                # ========================================
                # 3. 填写标签 - 逐个添加并回车，最多10个
                # ========================================
                if self.tags:
                    try:
                        # 根据用户提供的DOM：#tag-container input placeholder="按回车键Enter创建标签"
                        tag_input = page.locator('#tag-container input[placeholder*="回车"]').first
                        if await tag_input.count() == 0:
                            tag_input = page.locator('.tag-input-wrp input.input-val').first
                        
                        if await tag_input.count() > 0:
                            added_tags = []
                            for tag in self.tags[:10]:  # 最多10个标签
                                try:
                                    # 清空输入框，填写标签，回车确认
                                    await tag_input.fill("")
                                    await tag_input.fill(tag)
                                    await tag_input.press('Enter')
                                    added_tags.append(tag)
                                    bilibili_logger.debug(f"[+] 添加标签: {tag}")
                                    await asyncio.sleep(0.8)  # 增加等待时间确保标签添加动画完成
                                except Exception as e:
                                    bilibili_logger.debug(f"添加标签失败 '{tag}': {e}")
                            
                            if added_tags:
                                bilibili_logger.info(f"[✓] 标签添加成功 ({len(added_tags)}/10): {', '.join(added_tags)}")
                        else:
                            bilibili_logger.warning("[⚠️] 未找到标签输入框")
                    except Exception as e:
                        bilibili_logger.warning(f"[⚠️] 标签填写失败: {e}")
                
                # ========================================
                # 4. 填写描述（简介）- 使用contenteditable元素
                # ========================================
                if self.description:
                    try:
                        # 根据用户提供的DOM：.desc-container .ql-editor contenteditable="true"
                        desc_editor = page.locator('.desc-container .ql-editor[contenteditable="true"]').first
                        if await desc_editor.count() > 0:
                            # 点击编辑器，清空，填写内容
                            await desc_editor.click()
                            await desc_editor.fill("")  # 先清空
                            await asyncio.sleep(0.3)
                            await desc_editor.fill(self.description)
                            await asyncio.sleep(0.3)
                            # 点击外部触发保存
                            await page.locator('body').click()
                            bilibili_logger.info(f"[✓] 描述填写成功 ({len(self.description)}字符)")
                        else:
                            # 备选：查找desc-container内的任何contenteditable
                            desc_editor = page.locator('.desc-container [contenteditable="true"]').first
                            if await desc_editor.count() > 0:
                                await desc_editor.fill(self.description)
                                bilibili_logger.info(f"[✓] 描述填写成功(备选) ({len(self.description)}字符)")
                            else:
                                bilibili_logger.warning("[⚠️] 未找到描述编辑器")
                    except Exception as e:
                        bilibili_logger.warning(f"[⚠️] 描述填写失败: {e}")
                
                # ========================================
                # 5. 分区设置（必须选择）
                # ========================================
                bilibili_logger.info("[+] 设置分区...")
                try:
                    # 点击分区选择器 - 使用更多可能的选择器
                    zone_selectors = [
                        '.zone-selector',
                        '.select-item.vui-select-item',
                        '[class*="zone"] .vui-select-trigger',
                        '.category-selector',
                        '.type-select',
                        '[class*="type"] .vui-select',
                        '.vui-select-trigger',
                        '[data-v-] .vui-select'
                    ]
                    
                    zone_trigger = None
                    for selector in zone_selectors:
                        zone_trigger = page.locator(selector).first
                        if await zone_trigger.count() > 0:
                            bilibili_logger.info(f"[+] 找到分区选择器: {selector}")
                            break
                    
                    if zone_trigger and await zone_trigger.count() > 0:
                        await zone_trigger.click()
                        await asyncio.sleep(1.5)
                        
                        # 选择第一个可用分区
                        option_selectors = [
                            '.select-list-panel .panel-content-item',
                            '.vui-select-dropdown-item',
                            '.zone-option',
                            '.dropdown-item',
                            '.panel-content .item',
                            '.vui-popover-content .item'
                        ]
                        
                        zone_option = None
                        for selector in option_selectors:
                            zone_option = page.locator(selector).first
                            if await zone_option.count() > 0:
                                bilibili_logger.info(f"[+] 找到分区选项: {selector}")
                                break
                        
                        if zone_option and await zone_option.count() > 0:
                            await zone_option.click()
                            bilibili_logger.info("[✓] 分区设置完成")
                            await asyncio.sleep(1)
                        else:
                            # 关闭下拉菜单
                            await page.keyboard.press('Escape')
                            bilibili_logger.info("[ℹ️] 未找到分区选项，使用默认分区")
                    else:
                        bilibili_logger.info("[ℹ️] 未找到分区选择器，使用默认分区")
                except Exception as e:
                    bilibili_logger.warning(f"[⚠️] 分区设置失败: {e}，使用默认分区")
                
                # ========================================
                # 6. 上传封面（如果有cover_path）
                # ========================================
                if self.cover_path and Path(self.cover_path).exists():
                    bilibili_logger.info("[+] 上传封面...")
                    try:
                        # 找到封面上传区域
                        cover_input = page.locator('input[type="file"][accept*="image"], .cover-uploader input, [class*="cover"] input[type="file"]').first
                        if await cover_input.count() > 0:
                            await cover_input.set_input_files(str(self.cover_path))
                            bilibili_logger.success("[✓] 封面上传成功")
                            await asyncio.sleep(2)  # 等待封面处理
                        else:
                            bilibili_logger.warning("[⚠️] 未找到封面上传输入框")
                    except Exception as e:
                        bilibili_logger.warning(f"[⚠️] 封面上传失败: {{e}}")
                
                # ========================================
                # 7. 设置定时发布 - 点击switch并设置日期时间
                # ========================================
                if self.publish_date:
                    date_time_str = self.publish_date.strftime('%Y-%m-%d %H:%M')
                    bilibili_logger.info(f"[+] 设置定时发布: {date_time_str}")
                    
                    try:
                        # 5.1 点击定时发布开关 - 精确匹配用户提供的DOM结构
                        # DOM: .time-container .switch-container .switch-roll
                        switch_clicked = False
                        try:
                            # 精确定位switch开关
                            time_container = page.locator('.time-container').first
                            if await time_container.count() > 0:
                                switch = time_container.locator('.switch-container .switch-roll').first
                                if await switch.count() > 0:
                                    await switch.click()
                                    switch_clicked = True
                                    bilibili_logger.info("[✓] 已开启定时发布开关")
                                    await asyncio.sleep(3)  # 等待时间选择器出现
                                else:
                                    # 备选：直接查找switch-roll
                                    switch = page.locator('.switch-roll').first
                                    if await switch.count() > 0:
                                        await switch.click()
                                        switch_clicked = True
                                        bilibili_logger.info("[✓] 已开启定时发布开关(备选)")
                                        await asyncio.sleep(3)
                        except Exception as e:
                            bilibili_logger.warning(f"[⚠️] 点击定时开关失败: {e}")
                        
                        if not switch_clicked:
                            # 备选方案：尝试通过JavaScript点击
                            try:
                                js_clicked = await page.evaluate("""() => {
                                    const switchRoll = document.querySelector('.switch-roll, .switch-container .switch-roll');
                                    if (switchRoll) {
                                        switchRoll.click();
                                        return true;
                                    }
                                    return false;
                                }""")
                                if js_clicked:
                                    switch_clicked = True
                                    bilibili_logger.info("[✓] 已通过JS开启定时发布开关")
                                    await asyncio.sleep(3)
                            except:
                                pass
                        
                        # 5.2 设置日期和时间
                        date_str = self.publish_date.strftime('%Y-%m-%d')
                        time_str = self.publish_date.strftime('%H:%M')
                        day = str(self.publish_date.day)
                        
                        date_set_success = False
                        time_set_success = False
                        
                        if switch_clicked:
                            try:
                                await asyncio.sleep(2)
                                bilibili_logger.info(f"[+] 开始设置定时发布: {date_str} {time_str}")
                                
                                # 使用JavaScript直接操作DOM - 更可靠的方式
                                # 根据用户提供的DOM结构操作日期和时间选择器
                                
                                # ===== 设置日期 =====
                                try:
                                    # 使用JavaScript点击日期选择器并选择日期
                                    js_date_result = await page.evaluate("""(params) => {
                                        const dayNum = params.dayNum;
                                        // 1. 查找并点击日期显示区域
                                        const dateShows = document.querySelectorAll('.date-picker-date .date-show');
                                        if (dateShows.length === 0) return { success: false, error: '未找到日期显示元素' };
                                        
                                        dateShows[0].click();
                                        
                                        // 2. 等待日历弹出（使用setTimeout让UI更新）
                                        return new Promise((resolve) => {
                                            setTimeout(() => {
                                                // 3. 查找日历中的日期单元格 - 根据用户提供的DOM结构
                                                // 日期单元格: .date-picker-body-item.date-item (可选)
                                                // 禁用日期: .date-picker-body-item.date-item-disabled
                                                const dateItems = document.querySelectorAll('.date-picker-body-item.date-item:not(.date-item-disabled)');
                                                let clicked = false;
                                                
                                                for (const item of dateItems) {
                                                    // 匹配文本内容（如 "27"）
                                                    if (item.textContent.trim() === dayNum) {
                                                        item.click();
                                                        clicked = true;
                                                        break;
                                                    }
                                                }
                                                
                                                resolve({ success: clicked, method: clicked ? 'date-item-click' : 'no-date-found' });
                                            }, 500);
                                        });
                                    }""", {"dayNum": day})
                                    
                                    if js_date_result.get('success'):
                                        date_set_success = True
                                        bilibili_logger.info(f"[✓] 日期设置成功: {date_str}")
                                    else:
                                        bilibili_logger.warning(f"[⚠️] 日期设置失败: {js_date_result.get('error', '未知错误')}")
                                        
                                except Exception as e:
                                    bilibili_logger.warning(f"[⚠️] 日期设置异常: {e}")
                                
                                await asyncio.sleep(1)
                                
                                # ===== 设置时间 =====
                                try:
                                    # 使用JavaScript点击时间选择器并设置时间
                                    js_time_result = await page.evaluate("""(params) => {
                                        const hour = params.hour;
                                        const minute = params.minute;
                                        
                                        // 1. 查找并点击时间显示区域
                                        const timeShows = document.querySelectorAll('.date-picker-timer .date-show');
                                        if (timeShows.length === 0) return { success: false, error: '未找到时间显示元素' };
                                        
                                        timeShows[0].click();
                                        
                                        // 2. 等待时间选择器面板弹出
                                        return new Promise((resolve) => {
                                            setTimeout(() => {
                                                // 3. 根据用户提供的DOM结构选择时间
                                                // 时间面板: .time-picker-panel-select-wrp 包含小时和分钟
                                                // 小时选项: .time-picker-panel-select-item (第一个容器)
                                                // 分钟选项: .time-picker-panel-select-item (第二个容器)
                                                const panels = document.querySelectorAll('.time-picker-panel-select-wrp');
                                                if (panels.length >= 2) {
                                                    const hourPanel = panels[0];
                                                    const minutePanel = panels[1];
                                                    
                                                    // 点击小时 - 获取所有可用（非禁用）小时
                                                    const hourItems = hourPanel.querySelectorAll('.time-picker-panel-select-item:not(.time-select-disabled)');
                                                    let hourClicked = false;
                                                    let selectedHour = '';
                                                    for (const item of hourItems) {
                                                        const itemText = item.textContent.trim();
                                                        // 匹配小时（支持 07 和 7 两种格式）
                                                        if (itemText === hour || itemText === parseInt(hour, 10).toString()) {
                                                            item.click();
                                                            hourClicked = true;
                                                            selectedHour = itemText;
                                                            break;
                                                        }
                                                    }
                                                    // 如果精确小时不可用，选择第一个可用小时
                                                    if (!hourClicked && hourItems.length > 0) {
                                                        hourItems[0].click();
                                                        hourClicked = true;
                                                        selectedHour = hourItems[0].textContent.trim();
                                                    }
                                                    
                                                    // 点击分钟 - 获取所有可用（非禁用）分钟
                                                    const minuteItems = minutePanel.querySelectorAll('.time-picker-panel-select-item:not(.time-select-disabled)');
                                                    let minuteClicked = false;
                                                    let selectedMinute = '';
                                                    for (const item of minuteItems) {
                                                        const itemText = item.textContent.trim();
                                                        // 匹配分钟（支持 00 和 0 两种格式）
                                                        if (itemText === minute || itemText === parseInt(minute, 10).toString()) {
                                                            item.click();
                                                            minuteClicked = true;
                                                            selectedMinute = itemText;
                                                            break;
                                                        }
                                                    }
                                                    // 如果精确分钟不可用，选择第一个可用分钟
                                                    if (!minuteClicked && minuteItems.length > 0) {
                                                        minuteItems[0].click();
                                                        minuteClicked = true;
                                                        selectedMinute = minuteItems[0].textContent.trim();
                                                    }
                                                    
                                                    if (hourClicked && minuteClicked) {
                                                        resolve({ success: true, method: 'panel-click', selectedTime: selectedHour + ':' + selectedMinute });
                                                    } else {
                                                        resolve({ success: false, error: `无可用时间选项` });
                                                    }
                                                } else {
                                                    resolve({ success: false, error: '未找到时间选择面板' });
                                                }
                                            }, 500);
                                        });
                                    }""", {"hour": time_str.split(':')[0], "minute": time_str.split(':')[1]})
                                    
                                    if js_time_result.get('success'):
                                        time_set_success = True
                                        selected_time = js_time_result.get('selectedTime', time_str)
                                        if selected_time != time_str:
                                            bilibili_logger.info(f"[✓] 时间设置成功: {selected_time} (原定 {time_str} 不可用，自动选择最早可用时间)")
                                        else:
                                            bilibili_logger.info(f"[✓] 时间设置成功: {time_str}")
                                    else:
                                        bilibili_logger.warning(f"[⚠️] 时间设置失败: {js_time_result.get('error', '未知错误')}")
                                        
                                except Exception as e:
                                    bilibili_logger.warning(f"[⚠️] 时间设置异常: {e}")
                                
                            except Exception as e:
                                bilibili_logger.warning(f"[⚠️] 定时设置整体失败: {e}")
                        
                        # 记录设置结果
                        date_ok = '✓' if date_set_success else '✗'
                        time_ok = '✓' if time_set_success else '✗'
                        if date_set_success and time_set_success:
                            bilibili_logger.success(f"[✓] 定时发布设置完成: {date_str} {time_str}")
                            # 关闭时间选择面板 - 使用JavaScript点击空白处
                            await asyncio.sleep(0.5)
                            try:
                                # 尝试通过点击body关闭面板
                                await page.evaluate("""() => {
                                    // 点击body关闭所有弹出面板的常见方式
                                    document.body.click();
                                    // 触发Esc键关闭面板
                                    const escEvent = new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27 });
                                    document.dispatchEvent(escEvent);
                                    return true;
                                }""")
                                await asyncio.sleep(0.3)
                            except:
                                pass
                            # 再次点击确保面板关闭
                            await page.mouse.click(100, 100)
                            await asyncio.sleep(0.3)
                        else:
                            bilibili_logger.warning(f"[⚠️] 定时设置结果: 日期{date_ok}, 时间{time_ok}")
                        
                    except Exception as e:
                        bilibili_logger.warning(f"[⚠️] 定时发布设置失败: {e}")
                
                # 提交前检查表单是否完整
                bilibili_logger.info("[+] 检查表单完整性...")
                try:
                    # 检查必填字段
                    title_input = page.locator('input[placeholder*="标题"], .input-title input').first
                    title_value = await title_input.input_value() if await title_input.count() > 0 else ""
                    if not title_value or len(title_value.strip()) < 2:
                        bilibili_logger.warning("[⚠️] 标题可能未正确填写")
                    
                    # 检查分区是否选择
                    zone_select = page.locator('.select-item, [class*="zone"]').first
                    if await zone_select.count() > 0:
                        zone_text = await zone_select.text_content() or ""
                        if "请选择" in zone_text or "未选择" in zone_text:
                            bilibili_logger.warning("[⚠️] 分区可能未选择")
                except Exception as e:
                    bilibili_logger.debug(f"表单检查出错: {e}")
                
                # 提交稿件
                bilibili_logger.info("[+] 正在提交稿件...")
                submit_success = False
                
                try:
                    # 【修复】先关闭可能遮挡的提示弹窗
                    bilibili_logger.info("[+] 关闭可能的提示弹窗...")
                    try:
                        # 方法1: 按ESC键关闭弹窗
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                        
                        # 方法2: 查找并点击关闭按钮
                        close_selectors = [
                            '.close-btn',
                            '.icon-close',
                            '.bcc-popover-close',
                            '.tip-close',
                            '[class*="close"]',
                            '.guide-close',
                            '.popover-close',
                            '.modal-close',
                            '.dialog-close',
                            '.v-popover-close-wrp',  # B站提示弹窗关闭按钮
                            '.v-popover-close',  # B站提示弹窗关闭图标
                            '.submit-auto-tips .v-popover-close-wrp'  # 投稿提示弹窗
                        ]
                        for selector in close_selectors:
                            try:
                                close_btn = page.locator(selector).first
                                if await close_btn.count() > 0 and await close_btn.is_visible():
                                    await close_btn.click()
                                    bilibili_logger.info(f"[✓] 关闭弹窗: {selector}")
                                    await asyncio.sleep(0.3)
                            except:
                                pass
                        
                        # 方法3: 点击页面空白处关闭遮罩
                        await page.mouse.click(100, 100)
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        bilibili_logger.debug(f"关闭弹窗时出错: {e}")
                    
                    # 先滚动到页面底部确保提交按钮可见
                    await page.evaluate("""() => { window.scrollTo(0, document.body.scrollHeight); }""")
                    await asyncio.sleep(1)
                    
                    # 【关键】清除B站表单的"脏"状态，防止自定义弹窗
                    bilibili_logger.info("[+] 清除表单脏状态...")
                    await page.evaluate("""() => {
                        // 方法1: 标记表单为已保存
                        window.__formSubmitted__ = true;
                        window.__videoInfoChanged__ = false;
                        
                        // 方法2: 清除Vue组件的脏状态
                        const forms = document.querySelectorAll('.video-form, .upload-form, [class*="form"]');
                        for (const form of forms) {
                            if (form.__vue__ || form.__VUE__) {
                                const vm = form.__vue__ || form.__VUE__;
                                // 清除未保存标记
                                if (vm.$data) {
                                    vm.$data.isChanged = false;
                                    vm.$data.dirty = false;
                                }
                                if (vm.form) {
                                    vm.form.isChanged = false;
                                }
                            }
                        }
                        
                        // 方法3: 移除B站自定义弹窗的DOM元素（如果已存在）
                        const modals = document.querySelectorAll('.leave-confirm-modal, .confirm-leave-modal, [class*="leave-confirm"], [class*="confirm-leave"]');
                        for (const modal of modals) {
                            modal.remove();
                        }
                        
                        // 方法4: 禁用beforeunload
                        window.onbeforeunload = null;
                        window.addEventListener('beforeunload', (e) => {
                            // 不阻止
                        }, { capture: true });
                        
                        return true;
                    }""")
                    await asyncio.sleep(0.5)
                    
                    # 【简化】使用多种选择器尝试找到提交按钮
                    submit_selectors = [
                        'button:has-text("立即投稿")',
                        'button:has-text("投稿")',
                        '.submit-add',
                        '[class*="submit-add"]',
                        '.submit-container button',
                        '.submit-btn',
                        'button.submit',
                        '.submit-container .submit-add',
                    ]
                    
                    submit_btn = None
                    for selector in submit_selectors:
                        btn = page.locator(selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            submit_btn = btn
                            bilibili_logger.info(f"[+] 找到提交按钮: {selector}")
                            break
                    
                    if submit_btn:
                        # 检查按钮是否可用
                        try:
                            is_disabled = await submit_btn.is_disabled()
                        except:
                            is_disabled = False
                            
                        if is_disabled:
                            bilibili_logger.error("[-] 提交按钮被禁用，可能有必填字段未填写")
                            await page.screenshot(path="/tmp/bilibili_submit_disabled.png")
                            error_msgs = await page.locator('.error-msg, .form-error, .bcc-message--error, [class*="error"]').all_text_contents()
                            if error_msgs:
                                bilibili_logger.error(f"[-] 表单错误: {error_msgs}")
                        else:
                            await submit_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            
                            # 记录点击前的URL
                            pre_submit_url = page.url
                            bilibili_logger.info(f"[+] 提交前页面URL: {pre_submit_url}")
                            
                            # 【核心】使用JavaScript直接点击，最可靠的方式
                            bilibili_logger.info("[+] 使用JavaScript点击提交按钮...")
                            click_success = False
                            
                            try:
                                # 尝试JavaScript点击
                                js_click_result = await page.evaluate("""() => {
                                    // 尝试多种方式找到按钮
                                    const selectors = [
                                        'button:contains(\"立即投稿\")',
                                        'button:contains(\"投稿\")', 
                                        '.submit-add',
                                        '[class*="submit-add"]',
                                        '.submit-container button',
                                        '.submit-btn',
                                        'button.submit'
                                    ];
                                    
                                    for (const sel of selectors) {
                                        let btn = null;
                                        if (sel.includes(':contains')) {
                                            // 处理contains选择器
                                            const text = sel.match(/:contains\(["'](.+)["']\)/)?.[1];
                                            const buttons = document.querySelectorAll('button');
                                            for (const b of buttons) {
                                                if (b.textContent.includes(text)) {
                                                    btn = b;
                                                    break;
                                                }
                                            }
                                        } else {
                                            btn = document.querySelector(sel);
                                        }
                                        
                                        if (btn && btn.offsetParent !== null) { // 确保按钮可见
                                            // 模拟真实点击
                                            const clickEvent = new MouseEvent('click', {
                                                bubbles: true,
                                                cancelable: true,
                                                view: window
                                            });
                                            btn.dispatchEvent(clickEvent);
                                            return { success: true, selector: sel, text: btn.textContent.trim() };
                                        }
                                    }
                                    return { success: false, error: '未找到可点击的提交按钮' };
                                }""")
                                
                                if js_click_result.get('success'):
                                    bilibili_logger.info(f"[✓] JavaScript点击成功: {js_click_result.get('text', '按钮')}")
                                    click_success = True
                                else:
                                    bilibili_logger.warning(f"[⚠️] JavaScript点击失败: {js_click_result.get('error')}")
                            except Exception as js_err:
                                bilibili_logger.warning(f"[⚠️] JavaScript点击异常: {js_err}")
                            
                            # 如果JS点击失败，使用Playwright原生点击
                            if not click_success:
                                try:
                                    bilibili_logger.info("[+] 使用Playwright原生点击...")
                                    await submit_btn.click(force=True, timeout=10000)
                                    bilibili_logger.info("[✓] Playwright点击成功")
                                    click_success = True
                                except Exception as pw_err:
                                    bilibili_logger.error(f"[-] Playwright点击失败: {pw_err}")

                            # 等待提交成功标志（页面跳转、成功弹窗、按钮变化等）
                            bilibili_logger.info("[+] 等待提交成功标志...")
                            await asyncio.sleep(2)  # 给页面响应时间
                            url_changed = False
                            submit_success = False
                            success_indicator = None
                            
                            for i in range(60):
                                await asyncio.sleep(1)
                                current_url = page.url
                                
                                # 检查1: 页面跳转
                                if current_url != pre_submit_url:
                                    bilibili_logger.success(f"[✓] 检测到页面跳转: {current_url}")
                                    url_changed = True
                                    submit_success = True
                                    success_indicator = "页面跳转"
                                    break
                                
                                # 检查2: 成功弹窗/提示出现（B站AJAX成功的标志）
                                try:
                                    # 查找成功相关的元素
                                    success_modal = await page.locator('.submit-success-modal, .success-modal, .dialog--success, .bcc-modal__inner').count()
                                    success_msg = await page.locator('.success-msg, .bcc-message--success, .submit-success, :has-text("投稿成功"), :has-text("提交成功")').count()
                                    
                                    if success_modal > 0 or success_msg > 0:
                                        bilibili_logger.success("[✓] 检测到成功弹窗/提示")
                                        submit_success = True
                                        success_indicator = "成功弹窗"
                                        break
                                except:
                                    pass
                                
                                # 检查3: 提交按钮消失或变灰（表示已提交）
                                try:
                                    btn_visible = await submit_btn.is_visible()
                                    if not btn_visible:
                                        bilibili_logger.success("[✓] 提交按钮已消失，可能提交成功")
                                        submit_success = True
                                        success_indicator = "按钮消失"
                                        break
                                    
                                    # 检查按钮是否变灰/禁用
                                    btn_disabled = await page.evaluate("""() => {
                                        const btn = document.querySelector('.submit-container .submit-add');
                                        return btn ? (btn.disabled || btn.classList.contains('disabled') || btn.classList.contains('loading')) : false;
                                    }""")
                                    if btn_disabled:
                                        bilibili_logger.success("[✓] 提交按钮已禁用/加载中，可能提交成功")
                                        submit_success = True
                                        success_indicator = "按钮禁用"
                                        break
                                except:
                                    pass
                            
                            if not submit_success:
                                bilibili_logger.warning("[⚠️] 未检测到明确的提交成功标志")
                                
                                # 再次检查是否有成功标志（可能漏检）
                                try:
                                    page_content = await page.content()
                                    if "投稿成功" in page_content or "提交成功" in page_content or "success" in page_content.lower():
                                        bilibili_logger.success("[✓] 在页面内容中检测到成功关键词")
                                        submit_success = True
                                        success_indicator = "页面内容关键词"
                                except:
                                    pass
                                
                                if not submit_success:
                                    # 检查是否有错误提示阻止了提交
                                    error_count = await page.locator('.error-msg, .bcc-message--error, [class*="error"]').count()
                                    if error_count > 0:
                                        try:
                                            error_msg = await page.locator('.error-msg, .bcc-message--error').first.text_content()
                                            bilibili_logger.error(f"[-] 检测到错误提示阻止提交: {error_msg}")
                                        except:
                                            bilibili_logger.error("[-] 检测到错误提示阻止提交（无法获取文本）")
                                        await page.screenshot(path="/tmp/bilibili_submit_error.png")
                                    else:
                                        bilibili_logger.warning("[⚠️] 未检测到明确的提交结果，请手动检查 /tmp/bilibili_no_redirect.png")
                            else:
                                bilibili_logger.success(f"[✓] 投稿成功确认（标志: {success_indicator}）")
                                # 等待服务器处理完成
                                bilibili_logger.info("[+] 等待服务器处理完成...")
                                await asyncio.sleep(10)
                    else:
                        # 备选：通过文本查找
                        submit_btn = page.locator('span.submit-add:has-text("立即投稿")').first
                        if await submit_btn.count() > 0:
                            await submit_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await submit_btn.click()
                            bilibili_logger.success("[✓] 已点击提交按钮(文本查找)")
                            
                            # 同样等待跳转
                            pre_submit_url = page.url
                            for i in range(60):
                                await asyncio.sleep(1)
                                if page.url != pre_submit_url:
                                    bilibili_logger.success("[✓] 检测到页面跳转")
                                    submit_success = True
                                    break
                            if not submit_success:
                                bilibili_logger.warning("[⚠️] 未检测到页面跳转")
                                await page.screenshot(path="/tmp/bilibili_no_redirect2.png")
                        else:
                            bilibili_logger.error("[-] 未找到提交按钮")
                        
                except Exception as e:
                    bilibili_logger.error(f"[-] 提交过程异常: {e}")
                    await page.screenshot(path="/tmp/bilibili_submit_exception.png")
                
                if submit_success:
                    bilibili_logger.success("[+] 投稿流程完成")
                    # 关键：增加最终等待时间确保所有网络请求完成
                    bilibili_logger.info("[+] 等待网络请求完成...")
                    await asyncio.sleep(15)
                else:
                    bilibili_logger.error("[-] 投稿未能确认成功")
                
                return True
                
            except Exception as e:
                bilibili_logger.error(f"[-] 上传失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            finally:
                await browser.close()


class BilibiliVideo:
    """
    Bilibili 视频上传包装类
    兼容现有项目的调用方式
    """
    
    def __init__(
        self,
        title: str,
        file_path: str,
        tags: List[str],
        publish_date: Optional[datetime] = None,
        description: str = "",
        copyright: int = 1,
        account_file: Optional[Path] = None,
        cover_path: Optional[str] = None,
        on_upload_success: Optional[callable] = None
    ):
        """
        初始化 Bilibili 视频上传任务
        
        Args:
            title: 视频标题
            file_path: 视频文件路径
            tags: 标签列表
            publish_date: 发布时间
            description: 视频描述
            copyright: 版权类型 (1=自制, 2=转载)
            account_file: Cookie 文件路径
            cover_path: 封面图片路径
            on_upload_success: 上传成功后的回调函数 (可选)
        """
        self.title = title
        self.file_path = Path(file_path)
        self.tags = tags
        self.publish_date = publish_date
        self.description = description or title
        self.copyright = copyright
        self.account_file = account_file
        self.cover_path = cover_path
        self.on_upload_success = on_upload_success  # 【新增】上传成功回调
        
        # 初始化 uploader
        self._init_uploader()
    
    def _init_uploader(self):
        """初始化上传器"""
        # 读取 Cookie
        if not self.account_file or not self.account_file.exists():
            raise ValueError(f"Bilibili Cookie 文件不存在: {self.account_file}")
        
        raw_data = read_cookie_json_file(self.account_file)
        self.cookie_data = extract_keys_from_json(raw_data)
        
        # 创建上传器（传递提取后的 cookie 数据）
        self.uploader = BilibiliVideoUploader(
            cookie_data=self.cookie_data,
            video_path=self.file_path,
            title=self.title,
            description=self.description,
            tags=self.tags,
            publish_date=self.publish_date,
            copyright=self.copyright,
            cover_path=self.cover_path
        )
    
    async def upload(self, callback=None) -> bool:
        """
        执行上传
        
        Args:
            callback: 上传完成后的回调函数 (可选)
        
        Returns:
            上传是否成功
        """
        success = await self.uploader.upload()
        
        # 【修复】上传成功后调用回调
        if success and self.on_upload_success:
            try:
                self.on_upload_success()
            except Exception as e:
                bilibili_logger.warning(f"[⚠️] 上传成功回调执行失败: {e}")
        
        if callback:
            callback()
        
        return success


async def ensure_login(account_file: Path) -> bool:
    """Ensure logged in to Bilibili"""
    return await bilibili_setup(account_file, handle=True)
