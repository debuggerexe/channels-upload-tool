# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from playwright.async_api import Playwright, async_playwright, Page # 在这里添加 Page
import os
import asyncio
import random

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tencent_logger


def format_str_for_short_title(origin_title: str) -> str:
    # 定义允许的特殊字符 (根据用户描述更新)
    # 书名号《》, 引号", 冒号：, 加号+, 问号?, 百分号%, 摄氏度°
    allowed_special_chars = '《》":+?%°' # 更新：添加冒号，修正引号表示

    # 重写过滤逻辑以提高清晰度并处理两种逗号
    filtered_chars = []
    for char in origin_title:
        if char.isalnum() or char in allowed_special_chars:
            filtered_chars.append(char)
        elif char == ',' or char == '，': # 处理英文和中文逗号
            filtered_chars.append(' ')
        # 其他所有不符合条件的字符（包括不允许的符号和Emoji）会被自动忽略

    formatted_string = ''.join(filtered_chars)

    # 视频号短标题要求至少6个字，不足补空格，超出截断
    if len(formatted_string) > 16:
        formatted_string = formatted_string[:16]
    # 在截断后检查长度是否小于6
    if len(formatted_string) < 6:
        formatted_string += ' ' * (6 - len(formatted_string)) # 补空格

    # 返回处理后的字符串，平台通常会自动处理首尾空格，这里不再strip
    return formatted_string


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 等待5秒 cookie 失效")
            return False
        except:
            tencent_logger.success("[+] cookie 有效")
            return True


async def get_tencent_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        # Use default Chromium browser
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


async def weixin_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tencent_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        tencent_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_tencent_cookie(account_file)
    return True


class TencentVideo(object):
    def __init__(self, short_title, title_and_tags, file_path, publish_date: datetime, account_file, category=None, original_declaration=True, cover_position='top', thumbnail_path=None, keep_open=False, publish_mode='1', collections=None, on_upload_success=None, location='平台默认'):
        self.short_title = short_title  # 短标题
        self.title_and_tags = title_and_tags  # 标题和话题内容
        self.file_path = file_path
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category
        self.local_executable_path = LOCAL_CHROME_PATH
        self.original_declaration = original_declaration  # 添加原创声明配置
        self.cover_position = cover_position  # 封面选取位置：'top'/'middle'/'bottom'
        self.thumbnail_path = thumbnail_path  # 新增：外部传入的封面路径
        self.keep_open = keep_open  # 是否保持浏览器打开
        self.publish_mode = publish_mode  # 发布模式：'1'=定时发布, '2'=保存草稿
        self.collections = collections if collections else []  # 合集名称列表（可选）
        self.on_upload_success = on_upload_success  # 【新增】上传成功后的回调函数
        self.location = location  # 【新增】位置设置："不显示位置" | "平台默认"

    async def set_schedule_time_tencent(self, page, publish_date):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = str(publish_date.month) if publish_date.month > 9 else "0" + str(publish_date.month)
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click('button.weui-desktop-btn__icon__right')

        # 获取页面元素
        elements = await page.query_selector_all('table.weui-desktop-picker__table a')

        # 遍历元素并点击匹配的元素
        for element in elements:
            if 'weui-desktop-picker__disabled' in await element.evaluate('el => el.className'):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 选择时间（鼠标点选小时和分钟）
        await page.click('input[placeholder="请选择时间"]')
        await page.wait_for_selector('ol.weui-desktop-picker__time__hour', timeout=3000)
        # 点击目标小时
        hour_str = f"{publish_date.hour:02d}"
        hour_ol = page.locator('ol.weui-desktop-picker__time__hour')
        hour_count = await hour_ol.locator('li').count()
        for i in range(hour_count):
            li = hour_ol.locator('li').nth(i)
            if await li.inner_text() == hour_str:
                await li.click()
                break
        # 点击目标分钟
        minute_str = f"{publish_date.minute:02d}"
        minute_ol = page.locator('ol.weui-desktop-picker__time__minute')
        minute_count = await minute_ol.locator('li').count()
        for i in range(minute_count):
            li = minute_ol.locator('li').nth(i)
            if await li.inner_text() == minute_str:
                await li.click()
                break
        # 点击空白处，令选择生效
        await page.click("body")

    async def handle_upload_error(self, page):
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)

    async def upload_cover(self, page: Page, cover_path: str):
        """上传封面图片"""
        try:
            # 【修复】等待视频封面元素完全加载（有时视频上传完成但封面预览还未生成）
            tencent_logger.info("等待视频封面预览加载...")
            cover_ready = False
            for attempt in range(10):  # 最多等待10秒
                cover_preview_selectors = [
                    '.cover-img-vertical img',
                    '.vertical-img-size.cover-img-vertical img',
                    'img[alt="封面"]',
                    '.cover-preview img',
                    '.cover-wrap img',
                    '[class*="cover"] img',
                ]
                for selector in cover_preview_selectors:
                    try:
                        cover_img = await page.query_selector(selector)
                        if cover_img:
                            # 检查图片是否已加载（有src属性且不为空）
                            src = await cover_img.get_attribute('src')
                            if src and src.strip():
                                cover_ready = True
                                tencent_logger.info(f"视频封面预览已就绪: {selector}")
                                break
                    except:
                        continue
                if cover_ready:
                    break
                await asyncio.sleep(1)
            
            if not cover_ready:
                tencent_logger.warning("视频封面预览未就绪，继续尝试...")
            
            # 先尝试点击封面图片进入编辑模式
            cover_preview_selectors = [
                '.cover-img-vertical img',
                '.vertical-img-size.cover-img-vertical img',
                'img[alt="封面"]',
                '.cover-preview img',
                '.cover-wrap img',
                '[class*="cover"] img',
            ]
            
            cover_clicked = False
            for selector in cover_preview_selectors:
                try:
                    cover_img = await page.query_selector(selector)
                    if cover_img:
                        await cover_img.click()
                        tencent_logger.info(f"已点击封面图片进入编辑模式: {selector}")
                        cover_clicked = True
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            # 如果点击封面图片失败，尝试查找"更换封面"按钮
            if not cover_clicked:
                btn_selectors = [
                    'div.finder-tag-wrap.btn .tag-inner:text("更换封面")',
                    'div.tag-inner:text("更换封面")',
                    'span:text("更换封面")',
                    'div:text("更换封面")',
                    'button:text("更换封面")',
                    '.cover-edit-btn',
                    '.btn:has-text("更换封面")',
                    '[class*="cover"]:has-text("更换")',
                ]
                
                btn = None
                for attempt in range(30):
                    for selector in btn_selectors:
                        try:
                            candidate = await page.query_selector(selector)
                            if candidate:
                                is_disabled = False
                                try:
                                    parent_class = await candidate.evaluate('el => el.parentElement?.className || ""')
                                    if 'disabled' in parent_class or 'is-disabled' in parent_class:
                                        is_disabled = True
                                except:
                                    pass
                                
                                if not is_disabled:
                                    btn = candidate
                                    tencent_logger.info(f"找到封面按钮: {selector}")
                                    break
                        except:
                            continue
                    
                    if btn:
                        break
                    await asyncio.sleep(1)
                
                if not btn:
                    tencent_logger.warning("未找到封面编辑入口，跳过封面处理")
                    return
                
                await btn.click()
                await asyncio.sleep(1)
            
            # 等待封面编辑对话框出现（悬浮窗形式）
            try:
                # 等待对话框标题或内容出现
                dialog_selectors = [
                    '.ant-modal:has-text("编辑封面")',
                    '.ant-modal:has-text("封面")',
                    '.weui-desktop-dialog:has-text("编辑封面")',
                    '[class*="modal"]:has-text("封面")',
                    '.ant-modal-content',
                ]
                
                dialog_found = False
                for selector in dialog_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        tencent_logger.info(f"封面编辑对话框已打开: {selector}")
                        dialog_found = True
                        break
                    except:
                        continue
                
                if not dialog_found:
                    # 如果没找到特定对话框，等待一下继续
                    await asyncio.sleep(2)
                    
            except Exception as e:
                tencent_logger.warning(f"等待封面编辑对话框: {e}")

            # 如果有封面图，上传到"上传封面"区域
            if cover_path:
                # 根据 cover_position 处理封面裁剪
                processed_cover_path = cover_path
                if self.cover_position in ['top', 'bottom']:
                    try:
                        from utils.cover_cropper import crop_cover_to_34
                        processed_cover_path = crop_cover_to_34(cover_path, self.cover_position)
                        if processed_cover_path != cover_path:
                            tencent_logger.info(f"封面已裁剪为3:4比例({self.cover_position}): {processed_cover_path}")
                    except Exception as e:
                        tencent_logger.warning(f"封面裁剪失败，使用原图: {e}")
                
                try:
                    # 等待对话框完全加载
                    await asyncio.sleep(2)
                    
                    tencent_logger.info(f"准备上传封面: {processed_cover_path}")
                    
                    # 直接查找文件输入框（不点击+号，避免打开系统对话框）
                    file_input_selectors = [
                        '.weui-desktop-dialog input[type="file"]',
                        '.weui-desktop-dialog .ant-upload input[type="file"]',
                        '.ant-modal input[type="file"]',
                        '.ant-modal .ant-upload input[type="file"]',
                        '.ant-upload input[type="file"]',
                        '.ant-upload-drag input[type="file"]',
                    ]
                    
                    file_input = None
                    for selector in file_input_selectors:
                        try:
                            # 使用 locator 查找，更稳定
                            locator = page.locator(selector)
                            count = await locator.count()
                            if count > 0:
                                # 检查是否可见
                                try:
                                    await locator.wait_for(state="visible", timeout=3000)
                                    file_input = locator
                                    tencent_logger.info(f"找到文件输入框: {selector}")
                                    break
                                except:
                                    continue
                        except:
                            continue
                    
                    if file_input:
                        await file_input.set_input_files(processed_cover_path)
                        tencent_logger.info(f"已上传封面图片: {processed_cover_path}")
                        # 等待图片上传和预览生成
                        await asyncio.sleep(3)
                    else:
                        tencent_logger.warning("未找到文件输入框，尝试查找所有input[type='file']")
                        # 备用方案：查找所有文件输入框
                        try:
                            all_inputs = page.locator('input[type="file"]')
                            count = await all_inputs.count()
                            if count > 0:
                                # 使用最后一个（通常是最新创建的）
                                last_input = all_inputs.last
                                await last_input.set_input_files(processed_cover_path)
                                tencent_logger.info(f"已通过备用方案上传封面: {processed_cover_path}")
                                await asyncio.sleep(3)
                            else:
                                tencent_logger.error("找不到任何文件输入框")
                        except Exception as e2:
                            tencent_logger.error(f"所有上传方式都失败: {e2}")
                    
                except Exception as e:
                    tencent_logger.warning(f"上传封面图片失败: {e}")
            
            # 点击确认按钮关闭对话框
            confirm_selectors = [
                '.ant-modal .ant-btn-primary:has-text("确认")',
                '.ant-modal button:has-text("确认")',
                '.weui-desktop-dialog button:has-text("确认")',
                'button:has-text("确认")',
                '.ant-btn-primary',
            ]
            
            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    confirm_btn = await page.query_selector(selector)
                    if confirm_btn:
                        is_visible = await confirm_btn.is_visible()
                        if is_visible:
                            await confirm_btn.click()
                            tencent_logger.info("已点击确认按钮关闭封面编辑")
                            confirm_clicked = True
                            break
                except:
                    continue
            
            if not confirm_clicked:
                tencent_logger.warning("未找到确认按钮")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            tencent_logger.error(f"处理封面失败: {e}")
            await page.screenshot(path="cover_upload_error.png")

    async def set_location(self, page):
        """
        设置视频位置
        
        Args:
            page: Playwright 页面对象
        
        根据 self.location 的值决定如何处理位置：
        - "不显示位置": 点击位置区域，选择"不显示位置"
        - "平台默认": 跳过，保持平台默认加载的内容
        """
        # 如果设置为平台默认，跳过位置设置
        if self.location == "平台默认":
            tencent_logger.info("位置设置为'平台默认'，跳过位置设置")
            return
        
        # 不显示位置：执行原有的设置逻辑
        try:
            # 1. 点击"位置"区域，弹出下拉框
            await page.click('div.label:has-text("位置") + div .position-display-wrap')
            await page.wait_for_timeout(500)  # 等待下拉框弹出
            # 2. 点击"不显示位置"选项
            await page.wait_for_selector('div.common-option-list-wrap', timeout=2000)
            await page.click('div.option-item .name:text("不显示位置")')
            tencent_logger.info("已设置为不显示位置")
        except Exception as e:
            tencent_logger.error(f"设置不显示位置失败: {e}")

    async def set_no_location(self, page):
        """兼容旧方法，调用 set_location"""
        await self.set_location(page)

    async def upload_cover_image(self, page):
        """查找并上传封面图片"""
        # 优先使用外部传入的thumbnail_path
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
            tencent_logger.info(f"  [-] 使用外部传入的封面图: {self.thumbnail_path}")
            await self.upload_cover(page, self.thumbnail_path)
            return
        # 否则自动查找同名封面
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        exts = [".png", ".jpeg", ".jpg", ".webp"]
        cover_path = None
        video_dir = os.path.dirname(self.file_path)
        for ext in exts:
            candidate = os.path.join(video_dir, f"{base_name}{ext}")
            if os.path.exists(candidate):
                cover_path = candidate
                break
        if cover_path:
            tencent_logger.info(f"  [-] 找到封面图，准备上传: {cover_path}")
            await self.upload_cover(page, cover_path)
        else:
            tencent_logger.info(f"  [-] 未找到与视频同名的封面图片: {base_name}.[png/jpeg/jpg/webp]，依然进入封面裁剪界面。")
            await self.upload_cover(page, None)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium (这里使用系统内浏览器，用chromium 会造成h264错误
        # Use Chrome for better H.264 support
        try:
            browser = await playwright.chromium.launch(
                headless=False,
                channel="chrome"  # Use Chrome which includes H.264 support
            )
        except Exception as e:
            tencent_logger.warning(f"Failed to launch Chrome, falling back to Chromium: {str(e)}")
            # Fall back to Chromium if Chrome is not available
            browser = await playwright.chromium.launch(headless=False)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        
        try:
            # 访问指定的 URL
            await page.goto("https://channels.weixin.qq.com/platform/post/create")
            tencent_logger.info(f'[+]正在上传-------{self.title_and_tags}.mp4')
            # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
            await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
            # await page.wait_for_selector('input[type="file"]', timeout=10000)
            file_input = page.locator('input[type="file"]')
            await file_input.set_input_files(self.file_path)
            
            # 【优化】并行执行：等待上传完成 + 填写表单（封面除外）
            tencent_logger.info("  [-] 开始并行处理：视频上传 + 表单填写（封面等待上传完成后处理）")
            upload_task = asyncio.create_task(self.detect_upload_status(page))
            fill_form_task = asyncio.create_task(self.fill_form_during_upload(page))
            
            # 等待两个任务完成
            await asyncio.gather(upload_task, fill_form_task)
            tencent_logger.info("  [-] 视频上传完成，表单填写完成")
            
            # 视频上传完成后处理封面（封面必须等视频解析完成才能处理）
            await self.upload_cover_image(page)
            
            # 根据发布模式执行不同操作
            if self.publish_mode == '2':
                # 保存草稿模式：不设置定时，直接保存草稿
                tencent_logger.info("  [-] 保存草稿模式，直接保存")
                await self.click_save_draft(page)
            else:
                # 定时发布模式（默认）
                # 默认定时发布：无论publish_date是否为0都定时，若为0则设为次日9点
                if not self.publish_date or self.publish_date == 0:
                    now = datetime.now()
                    self.publish_date = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                await self.set_schedule_time_tencent(page, self.publish_date)
                # 点击发表
                await self.click_publish(page)

            await context.storage_state(path=f"{self.account_file}")  # 保存cookie
            tencent_logger.success('  [-]cookie更新完毕！')
            await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
            
        except (KeyboardInterrupt, asyncio.CancelledError):
            tencent_logger.warning('\n[!] 用户中断了上传')
            # 尝试保存 cookie
            try:
                await context.storage_state(path=f"{self.account_file}")
                print('  [-] cookie已保存')
            except Exception:
                pass
            # 不尝试保持浏览器打开，因为 Playwright 限制无法做到
            # 直接返回失败状态
            return False
        
        # 【修复】在关闭/暂停浏览器前执行回调（文件移动等）
        if self.on_upload_success:
            try:
                tencent_logger.info("  [-] 执行上传成功回调...")
                await self.on_upload_success()
                tencent_logger.info("  [-] 回调执行完成")
            except Exception as e:
                tencent_logger.error(f"  [-] 回调执行失败: {e}")
        
        # 关闭浏览器上下文和浏览器实例（如果 keep_open 为 False）
        if not self.keep_open:
            await context.close()
            await browser.close()
        else:
            tencent_logger.info('  [-]浏览器保持打开状态（最后一个视频）')
            print("\n" + "="*60)
            print("🎉 所有视频上传完成！浏览器将保持打开状态")
            print("   您可以手动操作浏览器或查看上传结果")
            print("   关闭 Playwright Inspector 窗口即可关闭浏览器")
            print("="*60 + "\n")
            # 使用 page.pause() 保持浏览器打开，并打开 Playwright Inspector
            await page.pause()
        
        return True  # 返回成功状态

    async def fill_form_during_upload(self, page):
        """
        在视频上传期间填写表单（封面除外）
        
        此方法与 detect_upload_status 并行执行，充分利用上传等待时间
        """
        try:
            # 等待页面元素加载（短暂延迟确保表单元素可用）
            await asyncio.sleep(1)
            
            # 1. 填写标题和话题
            tencent_logger.info("  [-] 正在填写标题和话题...")
            await self.add_title_tags(page)
            
            # 2. 添加短标题
            tencent_logger.info("  [-] 正在添加短标题...")
            await self.add_short_title(page)
            
            # 3. 添加合集
            tencent_logger.info("  [-] 正在添加合集...")
            await self.add_collection(page)
            
            # 4. 声明原创
            if self.original_declaration:
                tencent_logger.info("  [-] 正在执行原创声明...")
                await self.add_original(page)
            
            # 5. 设置位置
            tencent_logger.info("  [-] 正在设置位置信息...")
            await self.set_location(page)
            
            tencent_logger.info("  [-] 表单填写完成（封面等待上传完成后处理）")
            
        except Exception as e:
            tencent_logger.error(f"  [-] 表单填写过程中出错: {e}")
            # 不抛出异常，让上传流程继续

    async def add_title_tags(self, page):
        await page.locator("div.input-editor").click()
        await page.keyboard.type(self.title_and_tags)
        tencent_logger.info("已填写标题和话题")

    async def add_short_title(self, page):
        short_title_element = page.get_by_text("短标题", exact=True).locator("..") \
            .locator("xpath=following-sibling::div").locator('span input[type="text"]')
        if await short_title_element.count():
            await short_title_element.fill(self.short_title)

    async def click_publish(self, page):
        while True:
            try:
                publish_buttion = page.locator('div.form-btns button:has-text("发表")')
                if await publish_buttion.count():
                    await publish_buttion.click()
                await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=3000)
                tencent_logger.success("  [-]视频发布成功")
                break
            except Exception as e:
                current_url = page.url
                if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                    tencent_logger.success("  [-]视频发布成功")
                    break
                else:
                    tencent_logger.info("  [-] 视频正在发布中...")
                    await asyncio.sleep(0.5)

    async def click_save_draft(self, page):
        """点击保存草稿按钮，等待保存成功提示"""
        try:
            draft_button = page.locator('div.form-btns button:has-text("保存草稿")')
            if await draft_button.count():
                await draft_button.click()
                tencent_logger.success("  [-]已点击保存草稿")
            
            # 等待保存成功提示出现（最多等待5秒）
            try:
                # 等待"保存成功"文字出现
                await page.wait_for_selector('text=保存成功', timeout=5000)
                tencent_logger.success("  [-]草稿保存成功")
            except:
                # 如果没找到提示，等待3秒让操作完成
                await asyncio.sleep(3)
                tencent_logger.success("  [-]草稿已保存")
        except Exception as e:
            tencent_logger.error(f"  [-] 保存草稿失败: {e}")
            raise

    async def detect_upload_status(self, page):
        retry_count = 0
        max_retries = 3
        while True:
            try:
                # 匹配删除按钮，代表视频上传完毕
                if "weui-desktop-btn_disabled" not in await page.get_by_role("button", name="发表").get_attribute('class'):
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    tencent_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    # 出错了视频出错
                    if await page.locator('div.status-msg.error').count() and await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count():
                        retry_count += 1
                        if retry_count > max_retries:
                            tencent_logger.error(f"  [-] 上传失败已达最大重试次数（{max_retries}次），终止流程。")
                            raise Exception("视频上传失败，重试次数过多，已终止。")
                        tencent_logger.error(f"  [-] 发现上传出错了...准备重试（第{retry_count}次）")
                        await self.handle_upload_error(page)
            except Exception as e:
                tencent_logger.info(f"  [-] 正在上传视频中...（异常：{e}）")
                await asyncio.sleep(2)

    async def add_collection(self, page):
        """添加视频到合集
        
        流程：
        1. 点击"选择合集"弹出下拉框
        2. 加载合集列表
        3. 匹配任意一个合集名称（Notion中的任意合集与平台任意合集匹配即可）
        4. 匹配成功则点击选择，全部未匹配则提示用户手动创建
        """
        # 如果没有配置合集，直接跳过
        if not self.collections or len(self.collections) == 0:
            return
        
        try:
            tencent_logger.info(f"开始添加合集，候选合集: {self.collections}")
            
            # 1. 点击"选择合集"按钮，弹出下拉框
            collection_trigger = page.locator('.post-album-display-wrap .display-text:has-text("选择合集")')
            if await collection_trigger.count() == 0:
                tencent_logger.warning("找不到'选择合集'按钮，跳过合集添加")
                return
            
            await collection_trigger.click()
            tencent_logger.info("已点击'选择合集'按钮")
            
            # 等待下拉框加载（等待 loading 消失或选项列表出现）
            await asyncio.sleep(1)
            
            # 2. 获取所有合集选项
            option_items = page.locator('.option-list-wrap .option-item')
            option_count = await option_items.count()
            
            if option_count == 0:
                tencent_logger.warning("未找到任何合集选项，跳过合集添加")
                return
            
            tencent_logger.info(f"找到 {option_count} 个合集选项")
            
            # 3. 遍历查找匹配的合集名称（任意一个匹配即可）
            matched = False
            matched_collection = None
            
            for i in range(option_count):
                option = option_items.nth(i)
                name_locator = option.locator('.name')
                
                if await name_locator.count() > 0:
                    name_text = await name_locator.text_content()
                    name_text = name_text.strip() if name_text else ""
                    
                    tencent_logger.info(f"  合集选项 {i+1}: {name_text}")
                    
                    # 检查是否与任意一个候选合集匹配（完全匹配）
                    for candidate in self.collections:
                        if name_text == candidate.strip():
                            await option.click()
                            tencent_logger.success(f"  [-]已选择合集: {name_text}")
                            matched = True
                            matched_collection = name_text
                            
                            # 等待选择完成（下拉框关闭）
                            await asyncio.sleep(0.5)
                            break
                    
                    if matched:
                        break
            
            # 4. 未匹配到，提示用户手动创建
            if not matched:
                tencent_logger.warning(f"⚠️ 未找到匹配的合集 {self.collections}，请在视频号后台手动创建")
                # 点击其他地方关闭下拉框
                await page.keyboard.press('Escape')
                
        except Exception as e:
            tencent_logger.error(f"添加合集时出错: {e}")
            # 不抛出异常，继续后续流程

    async def add_original(self, page: Page):
        """声明原创"""
        try:
            tencent_logger.info("开始原创声明流程...")
            
            # 多种选择器尝试找到原创声明复选框
            checkbox_selectors = [
                '.declare-original-checkbox .ant-checkbox-input',
                '.ant-checkbox-input',  # 更通用的 ant design 选择器
                'input[type="checkbox"].ant-checkbox-input',
                '.ant-checkbox-wrapper input[type="checkbox"]',
            ]
            
            original_checkbox = None
            for selector in checkbox_selectors:
                try:
                    checkbox = page.locator(selector)
                    await checkbox.wait_for(state="visible", timeout=3000)
                    original_checkbox = checkbox
                    tencent_logger.info(f"使用选择器: {selector}")
                    break
                except:
                    continue
            
            if not original_checkbox:
                tencent_logger.warning("找不到原创声明复选框，跳过原创声明")
                return
            
            await original_checkbox.click(timeout=5000)
            tencent_logger.info("已勾选原创声明复选框")
            
            # 等待对话框出现
            dialog_selectors = [
                '.weui-desktop-dialog:has-text("原创权益")',
                '.weui-desktop-dialog:has-text("原创")',
                '.ant-modal:has-text("原创")',
            ]
            
            dialog = None
            for selector in dialog_selectors:
                try:
                    d = page.locator(selector).first
                    await d.wait_for(state="visible", timeout=5000)
                    dialog = d
                    tencent_logger.info(f"对话框使用选择器: {selector}")
                    break
                except:
                    continue
            
            if not dialog:
                tencent_logger.warning("找不到原创声明对话框，跳过")
                return
            
            tencent_logger.info("原创权益弹窗已出现")
            
            # 同意协议复选框
            agreement_selectors = [
                '.original-proto-wrapper .ant-checkbox-input',
                '.ant-checkbox-input',
                'input[type="checkbox"]',
            ]
            
            agreement_checkbox = None
            for selector in agreement_selectors:
                try:
                    checkbox = dialog.locator(selector)
                    await checkbox.wait_for(state="visible", timeout=3000)
                    agreement_checkbox = checkbox
                    tencent_logger.info(f"协议复选框使用选择器: {selector}")
                    break
                except:
                    continue
            
            if agreement_checkbox:
                await agreement_checkbox.click(timeout=5000)
                tencent_logger.info("已同意原创声明协议")
            
            # 确认按钮
            confirm_selectors = [
                '.weui-desktop-dialog__ft .weui-desktop-btn_primary:has-text("声明原创")',
                'button:has-text("声明原创")',
                '.ant-btn:has-text("声明")',
            ]
            
            confirm_button = None
            for selector in confirm_selectors:
                try:
                    btn = dialog.locator(selector)
                    await btn.wait_for(state="visible", timeout=3000)
                    confirm_button = btn
                    tencent_logger.info(f"确认按钮使用选择器: {selector}")
                    break
                except:
                    continue
            
            if confirm_button:
                await confirm_button.click(timeout=5000)
                tencent_logger.info("已点击声明原创按钮")
            
            try:
                await dialog.wait_for(state="hidden", timeout=10000)
            except:
                pass
            
            tencent_logger.success("原创声明流程完成")
        except Exception as e:
            tencent_logger.error(f"原创声明过程出错: {e}")
            # 不抛出异常，继续后续流程

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
