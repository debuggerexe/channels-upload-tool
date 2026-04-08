"""
飞书多维表格数据源实现
从飞书Bitable获取视频信息和文件，支持混合模式（优先本地，无本地则从云端下载）
"""

import os
import re
import json
import time
import aiohttp
import asyncio
from datetime import datetime, date
from typing import List, Tuple, Optional, Union
from pathlib import Path

from .data_source import VideoDataSource, VideoInfo
from conf import BASE_DIR
from utils.match_utils import (
    remove_date_prefix,
    calculate_similarity,
    select_best_matching_video,
    find_best_match_in_list,
    match_local_video,
    match_local_cover
)
from utils.text_utils import (
    assemble_description,
    sanitize_short_title,
    parse_publish_date,
    calculate_publish_mode,
    parse_collections,
    extract_date_from_folder
)
from utils.output_utils import (
    print_data_source_header,
    print_records_returned,
    print_pending_videos,
    print_pending_video_item,
    print_skipped_non_pending,
    print_no_videos_warning,
    print_scan_local_videos,
    print_match_summary,
    print_final_video_summary
)

# 导入飞书SDK
from lark_oapi import Client
from lark_oapi.api.bitable.v1 import *

# 添加 requests 用于原生 HTTP 调用
import requests

class FeishuDataSource(VideoDataSource):
    """飞书多维表格数据源"""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__()  # 调用基类__init__设置temp_dir和videos_dir
        self.config = config or {}
        
        # 从配置获取飞书应用凭证
        self.app_id = self.config.get('feishu_app_id', '').strip()
        self.app_secret = self.config.get('feishu_app_secret', '').strip()
        self.app_token = self.config.get('feishu_bitable_token', '').strip()
        self.table_id = self.config.get('feishu_table_id', '').strip()
        self.view_id = self.config.get('feishu_view_id', '').strip() or None
        
        # 设置videos_dir
        from conf import BASE_DIR
        self.videos_dir = Path(BASE_DIR) / "videos"
        
        # 验证必要配置
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "未配置飞书应用凭证。\n"
                "请在 config.json 中配置：\n"
                "  - feishu_app_id: 应用ID\n"
                "  - feishu_app_secret: 应用密钥\n"
                "获取方式：飞书开放平台 → 创建应用 → 应用凭证"
            )
        
        if not self.app_token:
            raise ValueError(
                "未配置飞书多维表格Token。\n"
                "请在 config.json 中配置：\n"
                "  - feishu_bitable_token: 多维表格Token\n"
                "获取方式：打开目标多维表格 → 复制URL中的 app_token"
            )
        
        # 初始化飞书客户端
        self.client = Client.builder().app_id(self.app_id).app_secret(self.app_secret).build()
        
        self.videos_dir = Path(BASE_DIR) / "videos"
        
        # 【简化】使用固定的默认发布时间 09:00，不再从本地配置读取
        # 混合模式下，发布时间应完全从飞书/Notion 获取
        self.default_hour = 9
        self.default_minute = 0
    
    def _get_access_token(self) -> str:
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            raise Exception(f"获取访问令牌失败: {result}")
    
    def _query_bitable_records(self, filter_status: Optional[Union[str, List[str]]] = None, max_retries: int = 3) -> List[dict]:
        """查询飞书多维表格记录
        
        Args:
            filter_status: 筛选状态，可以是单个状态字符串或状态列表
            max_retries: 最大重试次数
        """
        # 获取访问令牌
        try:
            token = self._get_access_token()
        except Exception as e:
            print(f"❌ 获取访问令牌失败: {e}")
            return []
        
        # 重试循环
        for attempt in range(1, max_retries + 1):
            try:
                url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8"
                }
                
                request_body = {"page_size": 500}
                if self.view_id:
                    request_body["view_id"] = self.view_id
                
                # 不添加API筛选，改为本地筛选（避免API格式问题）
                
                response = requests.post(url, headers=headers, json=request_body, timeout=30)
                
                # 检查响应
                if 'application/json' not in response.headers.get('Content-Type', ''):
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return []
                
                result = response.json()
                
                # 检查响应
                if result.get("code") != 0:
                    if result.get("code") == 1254302:
                        print(f"\n⚠️ 飞书权限不足，请将应用添加为表格协作者\n")
                        return []
                    
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return []
                
                records = result.get("data", {}).get("items", [])
                return records
                
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    return []
        
        return []
    
    def _extract_field(self, record: dict, field_name: str) -> any:
        """从记录中提取字段值（支持所有飞书多维表格字段类型）"""
        fields = record.get('fields', {})
        value = fields.get(field_name)
        
        if value is None:
            return None
        
        # 处理不同类型的值
        if isinstance(value, list):
            # 多选、人员、附件等数组类型
            if len(value) == 0:
                return None
            
            # 附件类型：提取文件URL
            if field_name in ['视频', '封面'] and isinstance(value[0], dict):
                file_info = value[0]
                url = file_info.get('url') or file_info.get('tmp_url') or file_info.get('file_url')
                name = file_info.get('name') or file_info.get('file_name') or 'unknown'
                file_type = file_info.get('type') or file_info.get('file_type') or 'unknown'
                
                return {'name': name, 'url': url, 'type': file_type}
            
            # 多选类型：提取所有选项文本
            texts = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get('text', '') or item.get('name', '') or item.get('label', '')
                    # 【修复】描述字段保留空行，其他字段过滤空值
                    if field_name in ['描述', '说明', '详情']:
                        # 去除行尾空格，避免额外的空行
                        texts.append(text.rstrip() if text else '')
                    elif text:
                        texts.append(text)
                elif isinstance(item, str):
                    # 【修复】描述字段保留空行（空字符串），但去除行尾空格
                    if field_name in ['描述', '说明', '详情']:
                        texts.append(item.rstrip())
                    elif item:
                        texts.append(item)
            # 【修复】对于描述等多行文本字段，应该用换行符连接，而不是逗号
            # 飞书的多行文本字段是以列表形式返回的，每个元素是一行
            if field_name in ['描述', '说明', '详情']:
                return '\n'.join(texts) if texts else None
            return ', '.join(texts) if texts else None
        
        elif isinstance(value, dict):
            # 单选、日期等对象类型
            if 'text' in value:
                return value['text']
            elif 'name' in value:
                return value['name']
            elif 'date' in value:
                return value['date']
            elif 'value' in value:
                return value['value']
            else:
                # 对于未知结构，返回第一个字符串值
                for key in ['label', 'title', 'content']:
                    if key in value and isinstance(value[key], str):
                        return value[key]
                return str(value)
        
        else:
            # 文本、数字、布尔等简单类型
            return value
    
    def get_videos_hybrid(self, status_filter: Union[str, List[str]] = ["待发布", "发布失败"]) -> List[VideoInfo]:
        """
        【混合模式】从飞书多维表格读取视频信息，匹配本地视频文件
        
        此模式下：
        1. 从飞书多维表格读取视频元数据（标题、描述、发布日期等）
        2. 从本地 videos/ 文件夹匹配对应的视频文件
        3. 本地没有时，从飞书附件下载
        
        Args:
            status_filter: 状态筛选（默认["待发布", "发布失败"]）
            
        Returns:
            VideoInfo 列表
            
        Raises:
            Exception: 飞书获取失败时抛出异常
        """
        # 从飞书获取记录（支持多个状态）
        records = self._query_bitable_records()
        return self._process_feishu_records(records, status_filter)
    
    def _process_feishu_records(self, records: List[dict], status_filter=None) -> List[VideoInfo]:
        """
        【统一5阶段模板】处理飞书记录，优先本地视频，无本地则从飞书下载
        
        阶段1：数据获取 - 从飞书获取记录
        阶段2：状态筛选 - 按状态筛选待上传视频
        阶段3：本地扫描 - 扫描本地 videos/ 文件夹
        阶段4：匹配结果 - 显示本地/下载/无来源分布
        阶段5：上传汇总 - 按日期排序输出最终列表
        """
        from datetime import datetime
        
        # ========== 阶段1：数据获取（已在外层完成，这里记录数量） ==========
        print_records_returned(len(records))
        
        # ========== 阶段2：按日期排序并筛选待上传视频 ==========
        # 本地状态筛选
        if status_filter:
            status_list = [status_filter] if isinstance(status_filter, str) else status_filter
            all_records = records
            records = [r for r in records if self._extract_field(r, "发布状态") in status_list]
            skipped_count = len(all_records) - len(records)
        else:
            skipped_count = 0
        
        def get_record_date(record):
            date_str = self._extract_field(record, "发布日期")
            if date_str:
                try:
                    dt = parse_publish_date(date_str, 9, 0)
                    if dt:
                        return dt
                except:
                    pass
            return datetime.max
        
        # 按发布日期排序记录
        records.sort(key=get_record_date)
        
        # 阶段2：输出待上传视频列表
        if records:
            print_pending_videos(len(records), "飞书")
            for record in records:
                name = self._extract_field(record, "Name") or "未知"
                status = self._extract_field(record, "发布状态") or "待发布"
                date_val = self._extract_field(record, "发布日期")
                # 修复日期格式：时间戳转日期字符串
                if date_val and isinstance(date_val, (int, float)):
                    try:
                        date_str = datetime.fromtimestamp(date_val / 1000).strftime("%Y-%m-%d")
                    except:
                        date_str = str(date_val)
                elif date_val and isinstance(date_val, str):
                    date_str = date_val[:10] if len(date_val) > 10 else date_val
                else:
                    date_str = "无日期"
                print_pending_video_item(name, status, date_str)
        print_skipped_non_pending(skipped_count)
        
        # ========== 阶段3：扫描本地视频 ==========
        video_items = self._scan_videos()
        print_scan_local_videos(len(video_items))
        
        # 建立本地视频索引
        local_videos = {}
        for video_file, container_name in video_items:
            clean_name = remove_date_prefix(container_name)
            local_videos[clean_name] = (video_file, container_name)
            local_videos[container_name] = (video_file, container_name)
        
        # ========== 阶段4：匹配本地/云端/标记无来源 ==========
        local_matched = []      # (video_info, name)
        need_download = []      # (video_info, name)
        skipped_no_source = []  # 无本地也无云端
        
        for record in records:
            try:
                # 提取字段
                name_for_match = self._extract_field(record, "Name")
                short_title = self._extract_field(record, "短标题")
                title = self._extract_field(record, "标题")
                description = self._extract_field(record, "描述")
                tags = self._extract_field(record, "标签")
                collections_str = self._extract_field(record, "合集")
                date_str = self._extract_field(record, "发布日期")
                
                # 配置项
                cover_position = self._extract_field(record, "封面裁剪") or "middle"
                original_declaration = self._extract_field(record, "声明原创")
                if original_declaration is None:
                    original_declaration = True
                location = self._extract_field(record, "位置") or "平台默认"
                
                # 发布方式
                publish_mode_field = self._extract_field(record, "发布方式")
                has_publish_date = bool(date_str)
                publish_mode = calculate_publish_mode(publish_mode_field, has_publish_date)
                
                if not name_for_match or not date_str:
                    continue
                
                # 尝试匹配本地视频
                local_video = None
                local_cover = None
                for local_name in [name_for_match, remove_date_prefix(name_for_match)]:
                    if local_name in local_videos:
                        local_video, _ = local_videos[local_name]
                        local_cover = match_local_cover(local_video)
                        break
                
                # 解析日期和其他字段
                publish_date = parse_publish_date(date_str, self.default_hour, self.default_minute)
                if not publish_date:
                    continue
                
                final_short_title = sanitize_short_title(short_title if short_title else "")
                full_description = assemble_description(title, description, tags, verbose=False)
                collections = parse_collections(collections_str)
                
                video_info = VideoInfo(
                    title=title if title else short_title,
                    short_title=final_short_title,
                    description=full_description,
                    tags=tags,
                    video_path=str(local_video) if local_video else None,
                    cover_path=str(local_cover) if local_cover else None,
                    video_url=None,
                    cover_url=None,
                    publish_date=publish_date,
                    collections=collections,
                    original_declaration=bool(original_declaration) if original_declaration is not None else True,
                    cover_position=cover_position,
                    location=location,
                    name_for_match=name_for_match,
                    folder_name=name_for_match,
                    source_mode="feishu_hybrid",
                    notion_page_id=record.get('record_id'),
                    publish_mode=publish_mode
                )
                
                if local_video:
                    local_matched.append((video_info, name_for_match))
                else:
                    # 本地没有，尝试获取云端URL
                    video_attachment = self._extract_attachment_url(record, "视频")
                    cover_attachment = self._extract_attachment_url(record, "封面")
                    
                    if video_attachment:
                        video_info.video_url = video_attachment.get('url')
                        if cover_attachment:
                            video_info.cover_url = cover_attachment.get('url')
                        need_download.append((video_info, name_for_match))
                    else:
                        skipped_no_source.append(name_for_match)
                
            except Exception as e:
                print(f"⚠️ 处理记录时出错: {e}")
                continue
        
        # ========== 阶段4：显示匹配结果 ==========
        print_match_summary(
            local_count=len(local_matched),
            download_count=len(need_download),
            no_source_count=len(skipped_no_source),
            local_names=[name for _, name in local_matched],
            download_names=[name for _, name in need_download],
            no_source_names=skipped_no_source
        )
        
        # ========== 阶段5：汇总并返回 ==========
        videos = [v for v, _ in local_matched] + [v for v, _ in need_download]
        
        # 使用公共函数打印最终汇总
        print_final_video_summary(videos)
        
        return videos
    
    def _extract_attachment_url(self, record: dict, field_name: str) -> Optional[dict]:
        """从记录中提取附件URL"""
        fields = record.get('fields', {})
        value = fields.get(field_name)
        
        if not value or not isinstance(value, list) or len(value) == 0:
            return None
        
        file_info = value[0]
        if not isinstance(file_info, dict):
            return None
        
        # 飞书附件可能的URL字段
        url = file_info.get('url') or file_info.get('tmp_url') or file_info.get('file_url') or file_info.get('preview_url')
        name = file_info.get('name') or file_info.get('file_name') or 'unknown'
        
        if url:
            return {'url': url, 'name': name}
        
        return None
    
    async def _download_file_async(self, file_url: str, filename: str, progress_callback=None, max_retries: int = 3) -> str:
        """
        从飞书 URL 异步下载文件到临时目录（带重试机制）
        自动添加飞书认证头
        """
        temp_dir = Path(BASE_DIR) / "temp" / "feishu_downloads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        local_path = temp_dir / filename
        
        # 获取飞书访问令牌
        token = self._get_access_token()
        
        for attempt in range(1, max_retries + 1):
            try:
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Authorization': f'Bearer {token}'
                    }
                    
                    async with session.get(file_url, headers=headers, timeout=aiohttp.ClientTimeout(total=300)) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"   ❌ HTTP {response.status}: {error_text[:200]}")
                            raise Exception(f"下载失败，HTTP {response.status}")
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if progress_callback and total_size > 0:
                                    progress = int((downloaded / total_size) * 100)
                                    progress_callback(filename, progress)
                
                # 验证文件大小
                if local_path.exists() and local_path.stat().st_size > 0:
                    print(f"✅ 下载完成: {local_path} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)")
                    return str(local_path)
                else:
                    raise Exception("下载文件为空")
                    
            except Exception as e:
                print(f"❌ 下载失败 {filename} (尝试 {attempt}/{max_retries}): {e}")
                if local_path.exists():
                    local_path.unlink()
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"   ⏳ {wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise Exception("下载失败，超出最大重试次数")
    
    async def download_video_files(self, videos: List[VideoInfo], progress_callback=None) -> List[VideoInfo]:
        """
        批量下载云端视频文件到本地临时目录
        【混合模式】优先使用本地 videos/ 文件夹中的文件，没有则从云端下载
        """
        async def download_single_video(video: VideoInfo) -> VideoInfo:
            try:
                # 【本地优先】先检查 videos/ 文件夹是否有匹配的文件
                local_video_path = match_local_video(video.name_for_match, self.videos_dir)
                local_cover_path = None
                
                if local_video_path:
                    video.video_path = str(local_video_path)
                    print(f"📁 使用本地视频: {local_video_path.name}")
                    
                    local_cover_path = match_local_cover(local_video_path)
                    if local_cover_path:
                        video.cover_path = str(local_cover_path)
                        print(f"📁 使用本地封面: {Path(local_cover_path).name}")
                else:
                    # 本地没有，从云端下载
                    if video.video_url:
                        video_filename = f"{video.name_for_match or 'video'}_{video.publish_date.strftime('%Y%m%d')}.mp4"
                        video.temp_local_video_path = await self._download_file_async(
                            video.video_url, 
                            video_filename,
                            progress_callback,
                            max_retries=3
                        )
                        video.video_path = video.temp_local_video_path
                
                # 封面处理
                if not video.cover_path and video.cover_url:
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(video.cover_url)
                        cover_ext = Path(parsed_url.path).suffix or '.jpg'
                        cover_filename = f"{video.name_for_match or 'cover'}_{video.publish_date.strftime('%Y%m%d')}{cover_ext}"
                        video.temp_local_cover_path = await self._download_file_async(
                            video.cover_url,
                            cover_filename,
                            progress_callback,
                            max_retries=2
                        )
                        video.cover_path = video.temp_local_cover_path
                    except Exception as cover_error:
                        print(f"⚠️ 封面下载失败: {cover_error}")
                        video.cover_url = None
                
                return video
                
            except Exception as e:
                print(f"❌ 处理失败 {video.name_for_match}: {e}")
                raise
        
        tasks = [download_single_video(v) for v in videos]
        processed_videos = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_videos = []
        for v in processed_videos:
            if isinstance(v, Exception):
                continue
            successful_videos.append(v)
        
        return successful_videos
    
    def get_videos(self, date_range: Optional[Tuple[date, date]] = None) -> List[VideoInfo]:
        """
        获取视频列表（实现基类接口）
        飞书模式下默认使用云端模式
        """
        return self.get_videos_hybrid(status_filter=["待发布", "发布失败"])
    
    def get_videos_count(self, date_range: Optional[Tuple[date, date]] = None) -> int:
        """获取视频数量"""
        return len(self.get_videos(date_range))
    
    def update_publish_status(self, record_id: str, status: str) -> bool:
        """
        更新视频的发布状态
        
        Args:
            record_id: 飞书记录ID
            status: 新状态（"已发布"或"发布失败"）
            
        Returns:
            是否更新成功
        """
        try:
            # 构建更新请求
            fields = {
                "发布状态": status
            }
            
            request = UpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .request_body(AppTableRecord.builder().fields(fields).build()) \
                .build()
            
            # 发送请求
            response = self.client.bitable.v1.app_table_record.update(request)
            
            if response.success():
                print(f"✅ 已更新发布状态: {status}")
                return True
            else:
                print(f"⚠️ 更新状态失败: {response.msg}")
                return False
                
        except Exception as e:
            print(f"❌ 更新发布状态失败: {e}")
            return False
    
    def create_record(self, fields: dict) -> Optional[str]:
        """
        创建新的飞书多维表格记录
        
        Args:
            fields: 字段数据字典，如 {"Name": "视频名称", "标题": "视频标题"}
            
        Returns:
            新记录的 record_id，失败返回 None
        """
        try:
            # 使用 SDK 创建记录
            from lark_oapi.api.bitable.v1 import CreateAppTableRecordRequest, AppTableRecord
            
            request = CreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(AppTableRecord.builder().fields(fields).build()) \
                .build()
            
            # 发送请求
            response = self.client.bitable.v1.app_table_record.create(request)
            
            if response.success():
                record_id = response.data.record.record_id
                print(f"✅ 创建记录成功: {record_id}")
                return record_id
            else:
                print(f"⚠️ 创建记录失败: {response.msg}")
                return None
                
        except Exception as e:
            print(f"❌ 创建记录失败: {e}")
            return None
    
    def create_video_record(self, name: str, title: str, short_title: str = "", 
                           description: str = "", tags: str = "", 
                           publish_date: str = "", status: str = "待发布") -> Optional[str]:
        """
        创建视频记录（快捷方法）
        
        Args:
            name: 视频名称（Name字段）
            title: 视频标题
            short_title: 短标题
            description: 描述
            tags: 标签
            publish_date: 发布日期（格式：YYYY-MM-DD）
            status: 发布状态（默认"待发布"）
            
        Returns:
            新记录的 record_id
        """
        fields = {
            "Name": name,
            "标题": title,
            "短标题": short_title,
            "描述": description,
            "标签": tags,
            "发布日期": publish_date,
            "发布状态": status
        }
        
        # 移除空值字段
        fields = {k: v for k, v in fields.items() if v}
        
        return self.create_record(fields)
    
    def _scan_videos(self) -> List[Tuple[Path, str]]:
        """
        扫描 videos 目录，返回所有视频文件列表
        
        支持两种存放方式：
        1. 子文件夹形式: videos/文件夹名/视频.mp4 -> (视频路径, 文件夹名)
           - 如果文件夹中有多个视频，选择与文件夹名最匹配的那个
        2. 直接存放: videos/视频.mp4 -> (视频路径, 视频文件名不含扩展名)
        
        Returns:
            List[Tuple[Path, str]]: [(视频文件路径, 用于匹配的名称)]
        """
        video_items = []
        
        if not self.videos_dir.exists():
            return video_items
        
        # 方式1: 扫描子文件夹
        for item in self.videos_dir.iterdir():
            if item.is_dir():
                # 在子文件夹中查找视频文件
                video_files = list(item.glob("*.mp4"))
                if not video_files:
                    continue
                
                # 清理文件夹名（去除日期前缀）
                folder_name_clean = remove_date_prefix(item.name)
                
                if len(video_files) == 1:
                    # 只有一个视频，直接使用
                    video_items.append((video_files[0], item.name))
                else:
                    # 多个视频：选择与文件夹名最匹配的那个
                    best_match, _ = select_best_matching_video(video_files, item.name, verbose=False)
                    if best_match:
                        video_items.append((best_match, item.name))
        
        # 方式2: 扫描直接放在 videos 目录下的视频文件
        for video_file in self.videos_dir.glob("*.mp4"):
            if video_file.is_file():
                # 使用视频文件名（不含扩展名）进行匹配
                video_name = video_file.stem
                video_items.append((video_file, video_name))
        
        return video_items


if __name__ == "__main__":
    # 测试代码
    from conf import BASE_DIR
    import json
    
    config_path = Path(BASE_DIR) / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        try:
            source = FeishuDataSource(config)
            videos = source.get_videos_from_cloud()
            print(f"\n找到 {len(videos)} 个视频:")
            for v in videos:
                print(f"- {v.title} ({v.publish_date.date()})")
        except Exception as e:
            print(f"错误: {e}")
    else:
        print("未找到 config.json")
