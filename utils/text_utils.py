"""
文本处理工具函数 - 用于统一飞书和Notion的描述组装逻辑
"""
from typing import Optional
from datetime import datetime
import re


def parse_publish_date(
    date_str,
    default_hour: int = 9,
    default_minute: int = 0
) -> Optional[datetime]:
    """
    统一解析发布日期字符串
    
    支持格式：
    1. ISO格式带时间："2024-01-15T10:30:00+00:00" 或 "2024-01-15T10:30"
    2. 空格分隔日期时间："2024-01-15 10:30" 或 "2024-01-15 10:30:00"
    3. 纯日期字符串："2024-01-15"
    4. 毫秒时间戳：1705312800000
    5. 日期对象
    
    Args:
        date_str: 日期字符串或时间戳
        default_hour: 默认小时（仅当日期不含时间时使用）
        default_minute: 默认分钟（仅当日期不含时间时使用）
        
    Returns:
        datetime 对象，解析失败返回 None
    """
    if not date_str:
        return None
    
    try:
        if isinstance(date_str, str):
            date_str = date_str.strip()
            
            # 【新增】毫秒时间戳字符串（纯数字）
            if date_str.isdigit():
                timestamp_ms = int(date_str)
                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                return dt
            
            # ISO格式带时间 (2024-01-15T10:30:00 或 2024-01-15T10:30:00+00:00)
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            
            # 空格分隔日期时间 (2024-01-15 10:30 / 2024/01/15 10:30 / 2024-01-15 10:30:00)
            elif ' ' in date_str:
                parts = date_str.split(' ')
                if len(parts) == 2:
                    date_part_str, time_part_str = parts
                    # 支持横杠或斜杠分隔的日期
                    if '/' in date_part_str:
                        date_part = datetime.strptime(date_part_str, '%Y/%m/%d')
                    else:
                        date_part = datetime.strptime(date_part_str, '%Y-%m-%d')
                    # 解析时间部分
                    if ':' in time_part_str:
                        time_parts = time_part_str.split(':')
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                        return date_part.replace(hour=hour, minute=minute, second=second)
                    else:
                        # 没有时间分隔符，使用默认时间
                        return date_part.replace(hour=default_hour, minute=default_minute)
                else:
                    # 多个空格，尝试整体解析（支持横杠或斜杠日期）
                    if '/' in date_str:
                        dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')
                    else:
                        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    return dt
            
            else:
                # 纯日期字符串，补充默认时间（支持横杠或斜杠）
                if '/' in date_str:
                    date_part = datetime.strptime(date_str, '%Y/%m/%d')
                else:
                    date_part = datetime.strptime(date_str, '%Y-%m-%d')
                return date_part.replace(hour=default_hour, minute=default_minute)
        
        elif isinstance(date_str, int):
            # 毫秒时间戳转秒，保留原始时间
            dt = datetime.fromtimestamp(date_str / 1000)
            return dt
        
        elif isinstance(date_str, datetime):
            return date_str.replace(hour=default_hour, minute=default_minute)
        
    except Exception:
        return None
    
    return None


def calculate_publish_mode(
    publish_mode_field: Optional[str],
    has_publish_date: bool
) -> str:
    """
    统一计算发布方式（根据数据源字段值）
    
    优先级逻辑：
    - 发布方式 = 保存草稿 → 保存草稿 ("2")
    - 发布方式 = 定时发布 + 有发布日期 → 定时发布 ("1")
    - 发布方式 = 定时发布 + 无发布日期 → 降级为保存草稿 ("2")
    - 发布方式 = 空 + 有发布日期 → 默认定时发布 ("1")
    - 发布方式 = 空 + 无发布日期 → 默认保存草稿 ("2")
    
    Args:
        publish_mode_field: 数据源中的"发布方式"字段值
        has_publish_date: 是否有发布日期
        
    Returns:
        "1" (定时发布) 或 "2" (保存草稿)
    """
    if not publish_mode_field:
        # 未设置发布方式
        return '1' if has_publish_date else '2'
    
    if '保存草稿' in str(publish_mode_field):
        return '2'
    elif '定时发布' in str(publish_mode_field):
        return '1' if has_publish_date else '2'
    else:
        # 其他情况默认定时发布（如果有日期）
        return '1' if has_publish_date else '2'


def parse_collections(collections_str: Optional[str]) -> list:
    """
    统一解析合集字符串为列表
    
    Args:
        collections_str: 逗号分隔的合集名称字符串
        
    Returns:
        合集名称列表
    """
    if not collections_str:
        return []
    return [c.strip() for c in collections_str.split(",") if c.strip()]


def extract_date_from_folder(folder_name: str) -> Optional[datetime]:
    """
    从文件夹名中提取日期 (YYMMDD 格式)
    
    支持格式：
    - 240815_文件夹名 -> 2024-08-15
    - 240815文件夹名 -> 2024-08-15
    
    Args:
        folder_name: 文件夹名称
        
    Returns:
        datetime 对象，解析失败返回 None
    """
    match = re.match(r'^(\d{6})', folder_name)
    if not match:
        return None
    
    date_str = match.group(1)
    try:
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return None


def sanitize_short_title(title: str) -> str:
    """
    清理短标题，按视频号平台规则处理
    
    处理流程：
    1. 逗号替换：中英文逗号替换为空格
    2. 过滤：仅保留中文、英文、数字和指定符号
       允许符号：书名号《》、引号"、冒号：、加号+、问号?、百分号%、摄氏度°
    3. 填充：不足6字用空格补充到6字
    4. 截断：超过16字强行截断到16字
    
    Args:
        title: 原始短标题
        
    Returns:
        清理后的短标题
    """
    if not title:
        return "      "  # 6个空格
    
    # 步骤1：逗号替换为空格（中英文逗号）
    cleaned = title.replace(',', ' ').replace('，', ' ')
    
    # 步骤2：过滤非法字符
    # 允许的字符：中文、英文、数字、空格、指定符号《》":+?%°
    allowed_chars = r'a-zA-Z0-9\s\u4e00-\u9fa5《》":+?%°'
    cleaned = re.sub(rf'[^{allowed_chars}]', '', cleaned)
    
    # 步骤3：不足6字用空格补充
    if len(cleaned) < 6:
        cleaned = cleaned + ' ' * (6 - len(cleaned))
    
    # 步骤4：超过16字强行截断
    if len(cleaned) > 16:
        cleaned = cleaned[:16]
    
    return cleaned


def assemble_description(
    title: Optional[str],
    description: Optional[str],
    tags: Optional[str],
    verbose: bool = False
) -> str:
    """
    统一组装视频描述文本
    
    组装规则：
    1. 标题（如果有） -> 第一行
    2. 描述（如果有） -> 追加
    3. 标签（如果有，且描述中未包含） -> 格式化为 #tag1 #tag2 并追加
    
    标签去重逻辑：
    - 检查描述中是否已有以 # 开头的行
    - 检查格式化后的标签是否已在描述中
    - 检查描述中是否包含任何 # 字符
    如果以上任一条件满足，则跳过追加标签
    
    Args:
        title: 视频标题
        description: 视频描述
        tags: 标签字符串（逗号或中文逗号分隔）
        verbose: 是否打印调试信息
        
    Returns:
        组装后的完整描述文本
    """
    description_parts = []
    
    # 1. 添加标题（如果有）
    if title:
        description_parts.append(title.strip())
    
    # 2. 转换标签格式
    formatted_tags = ""
    if tags:
        tag_list = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
        # 【修复】检查标签是否已经有#前缀，有则不再添加
        formatted_tags = ' '.join([f"#{tag}" if not tag.startswith('#') else tag for tag in tag_list])
    
    # 3. 添加描述和标签
    if description:
        # 【修复】去除首尾空白但保留内部的空行和段落结构
        desc_clean = description.strip('\n\r\t ')
        description_parts.append(desc_clean)
        
        # 检查描述中是否已包含标签
        lines = desc_clean.split('\n')
        # 检测是否有任何行以 # 开头（去除前后空白后）
        has_tag_line = any(line.strip().startswith('#') for line in lines)
        # 检测格式化后的标签是否已完整存在于描述中
        has_formatted_tags = formatted_tags and formatted_tags in desc_clean

        if verbose:
            print(f"   [调试] 描述行数: {len(lines)}, 检测到有#开头的行: {has_tag_line}")
            for i, line in enumerate(lines[-3:]):  # 显示最后3行
                print(f"   [调试] 行{i}: {line[:50]}...")
            if has_tag_line:
                print("📝 描述中已有以#开头的行，跳过追加标签")
            elif has_formatted_tags:
                print("📝 描述中已包含格式化标签，跳过追加")
            elif '#' in desc_clean:
                print(f"📝 描述中包含#字符但不是在行首")

        # 如果描述中没有以#开头的行，且有待追加的标签
        if not has_tag_line and formatted_tags:
            description_parts.append(formatted_tags)
            if verbose:
                print(f"📝 已追加标签: {formatted_tags}")
                
    elif formatted_tags:
        # 没有描述但有标签，只添加标签
        description_parts.append(formatted_tags)
        if verbose:
            print(f"📝 已添加标签: {formatted_tags}")
    
    return '\n'.join(description_parts) if description_parts else ""


def format_tags(tags: Optional[str]) -> str:
    """
    将逗号分隔的标签格式化为 #tag 格式
    
    Args:
        tags: 逗号或中文逗号分隔的标签字符串
        
    Returns:
        格式化后的标签字符串（如 "#tag1 #tag2 #tag3"）
    """
    if not tags:
        return ""
    
    tag_list = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
    # 【修复】检查标签是否已经有#前缀，有则不再添加
    return ' '.join([f"#{tag}" if not tag.startswith('#') else tag for tag in tag_list])


def has_tags_in_description(description: Optional[str], formatted_tags: str = "") -> bool:
    """
    检查描述中是否已包含标签

    检查逻辑：
    1. 是否有以 # 开头的行
    2. 格式化后的标签是否已在描述中
    3. 是否有真正的话题标签格式（#在行首、空格后、或换行后）

    Args:
        description: 描述文本
        formatted_tags: 格式化后的标签（用于精确匹配）

    Returns:
        如果描述中已包含标签则返回 True
    """
    if not description:
        return False

    desc_clean = description.strip()
    lines = desc_clean.split('\n')

    has_tag_line = any(line.strip().startswith('#') for line in lines)
    has_formatted_tags = formatted_tags and formatted_tags in desc_clean
    # 【修复】检查是否有真正的话题标签格式（行首、空格后、或换行后的#）
    has_real_tag = bool(re.search(r'(^|\s|\n)#[^#\s]', desc_clean))

    return has_tag_line or has_formatted_tags or has_real_tag
