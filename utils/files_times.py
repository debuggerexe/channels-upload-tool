import os
from datetime import datetime, timedelta, date
from pathlib import Path
import pytz
# --- 修改开始 ---
# 移除对特定 uploader 的导入
# from uploader.tencent_uploader.main import format_str_for_short_title
# --- 修改结束 ---
import json # 确保 json 被导入，因为 get_publish_date 需要它

from conf import BASE_DIR


def get_absolute_path(file_path, uploader_name):
    """获取文件的绝对路径，如果不是绝对路径，则相对于 BASE_DIR/uploader_name 构建"""
    relative_path = Path(file_path)
    if relative_path.is_absolute():
        return str(relative_path)
    else:
        # --- 修改开始 ---
        # 使用正确的参数名 uploader_name 替换 base_dir
        absolute_path = Path(BASE_DIR) / uploader_name / relative_path
        # --- 修改结束 ---
        return str(absolute_path)


def get_title_and_hashtags(video_path: str):
    """
    从与视频同名的 .txt 文件中读取原始的短标题（第一行）和标题/话题内容（剩余行）。
    不进行特定平台的格式化。
    """
    txt_path = Path(video_path).with_suffix('.txt')
    raw_short_title = "" # 返回原始短标题
    title_and_tags = ""
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                # --- 修改开始 ---
                # 获取第一行作为原始短标题，移除首尾空白
                raw_short_title = lines[0].strip()
                # --- 修改结束 ---
                if len(lines) > 1:
                    # 保留换行符，只移除首尾空白
                    title_and_tags = ''.join(lines[1:]).strip()
                # 如果只有一行，title_and_tags 保持为空字符串或可以设为 raw_short_title
                # else:
                #    title_and_tags = raw_short_title # 或者保持为空，取决于业务逻辑
            else:
                # 如果文件为空，使用视频文件名（不含扩展名）作为默认值
                raw_short_title = Path(video_path).stem
                title_and_tags = Path(video_path).stem
    else:
        # 如果txt文件不存在，使用视频文件名（不含扩展名）作为默认值
        raw_short_title = Path(video_path).stem
        title_and_tags = Path(video_path).stem

    # 返回原始的短标题和内容
    return raw_short_title, title_and_tags


def generate_schedule_time_next_day(total_videos, videos_per_day, daily_times=None, timestamps=False, start_days=0):
    """
    Generate a schedule for video uploads, starting from a specified day at fixed times.
    
    Args:
        total_videos (int): Total number of videos to schedule
        videos_per_day (int): Number of videos to publish per day
        daily_times (list): List of hours when videos should be published (default: [6, 9, 12, 15, 18, 21])
        timestamps (bool): Whether to return timestamps instead of datetime objects
        start_days (int): Number of days to offset from tomorrow (0 means tomorrow, 1 means day after tomorrow, etc.)
    
    Returns:
        list: List of datetime objects or timestamps for scheduled uploads
    """
    from datetime import time, datetime, timedelta

    if videos_per_day <= 0:
        raise ValueError("videos_per_day should be a positive integer")

    if daily_times is None:
        daily_times = [6, 9, 12, 15, 18, 21]  # Default publish times
    
    if videos_per_day > len(daily_times):
        raise ValueError("videos_per_day should not exceed the length of daily_times")

    # Sort daily times to ensure chronological order
    daily_times.sort()
    
    # Calculate start date (tomorrow + offset days)
    start_date = datetime.now().date() + timedelta(days=1 + start_days)
    
    # Calculate how many days we need based on total videos and videos per day
    total_days = (total_videos + videos_per_day - 1) // videos_per_day
    
    schedule = []
    current_date = start_date
    videos_scheduled = 0
    
    # Generate schedule for each day until we have enough slots for all videos
    for day in range(total_days):
        # For each day, take only the first videos_per_day time slots
        day_times = daily_times[:videos_per_day]
        for hour in day_times:
            if videos_scheduled < total_videos:
                schedule_time = datetime.combine(current_date, time(hour=hour))
                schedule.append(schedule_time)
                videos_scheduled += 1
        current_date += timedelta(days=1)

    if timestamps:
        schedule = [int(dt.timestamp()) for dt in schedule]
    
    return schedule


def get_publish_date(config_path):
    """从配置文件获取发布日期"""
    if not config_path.exists():
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f) # 需要导入 json

    if "publish_date" in config:
        try:
            return datetime.strptime(config["publish_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            print(f"错误：config.json 中的 publish_date '{config['publish_date']}' 格式无效或类型错误。")
            return None
    return None


def generate_schedule_times(start_date_str: str, daily_times: list[str], num_videos: int) -> list[datetime]:
    """
    根据 config.json 中的起始日期和每日时间点生成发布时间列表。

    Args:
        start_date_str: 起始日期字符串 (YYYY-MM-DD)。
        daily_times: 包含每日发布小时的列表 (例如 [12, 18])。
        num_videos: 需要安排发布的视频总数。

    Returns:
        一个包含 datetime 对象的列表，表示每个视频的预定发布时间。
    """
    schedule_times = []
    try:
        current_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"错误：config.json 中的 publish_date '{start_date_str}' 格式无效，应为 YYYY-MM-DD。将使用今天的日期。")
        current_date = date.today() # 提供一个回退机制

    if not daily_times:
        print("错误：config.json 中的 publish_times 为空。无法生成时间表。")
        now = datetime.now()
        return [now + timedelta(hours=i) for i in range(num_videos)]

    time_index = 0
    for _ in range(num_videos):
        if time_index >= len(daily_times):
            time_index = 0
            current_date += timedelta(days=1)

        time_str = daily_times[time_index]
        try:
            hour, minute = map(int, time_str.split(':'))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                dt = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                schedule_times.append(dt)
            else:
                print(f"警告：config.json 中的时间 '{time_str}' 无效，已跳过。小时应在 0 到 23 之间。")
                default_hour = 12
                dt = datetime.combine(current_date, datetime.min.time().replace(hour=default_hour))
                schedule_times.append(dt)
        except ValueError as e:
            print(f"警告：处理时间字符串 {time_str} 时出错: {e}。已跳过。")
            default_hour = 12
            dt = datetime.combine(current_date, datetime.min.time().replace(hour=default_hour))
            schedule_times.append(dt)

        time_index += 1

    return schedule_times


def parse_schedule(schedule_str: str) -> datetime:
    """解析 YYYY-MM-DD HH:MM 格式的日期时间字符串"""
    try:
        return datetime.strptime(schedule_str, '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        print(f"错误：无法解析计划时间字符串 '{schedule_str}'。应为 'YYYY-MM-DD HH:MM' 格式。")
        return None # 或者返回当前时间 datetime.now()，或抛出异常
