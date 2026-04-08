"""
终端输出美化工具模块
参考 Claude Code 的界面设计风格
"""

from typing import Optional
import shutil

# 获取终端宽度
TERM_WIDTH = shutil.get_terminal_size().columns

# 统一的图标映射
ICONS = {
    # 状态图标
    'success': '✓',
    'error': '✗',
    'warning': '⚠',
    'info': 'ℹ',
    'pending': '○',
    'running': '◐',
    'done': '✓',
    
    # 操作图标
    'upload': '⬆',
    'download': '⬇',
    'sync': '🔄',
    'search': '🔍',
    'scan': '📁',
    'cloud': '☁',
    'local': '💻',
    'video': '🎬',
    'image': '🖼',
    'folder': '📂',
    'file': '📄',
    'database': '🗄',
    'check': '✓',
    'cross': '✗',
    'arrow': '→',
    'bullet': '•',
    'star': '★',
    
    # 分隔符
    'separator': '─',
    'vertical': '│',
    'corner': '└',
    'branch': '├',
}

# 颜色代码（ANSI）
class Colors:
    """ANSI 颜色代码"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


def get_term_width() -> int:
    """获取终端宽度，最小返回 60"""
    return max(shutil.get_terminal_size().columns, 60)


def header(text: str, icon: str = '', color: str = Colors.BRIGHT_BLUE) -> None:
    """
    打印带分隔线的标题头
    
    Args:
        text: 标题文本
        icon: 前缀图标
        color: 颜色代码
    """
    width = get_term_width()
    prefix = f"{icon} " if icon else ""
    print(f"\n{color}{Colors.BOLD}{prefix}{text}{Colors.RESET}")
    print(f"{Colors.DIM}{ICONS['separator'] * width}{Colors.RESET}")


def section(text: str, icon: str = '') -> None:
    """打印小节标题"""
    prefix = f"{icon} " if icon else ""
    print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}{prefix}{text}{Colors.RESET}")


def item(label: str, value: str, indent: int = 0) -> None:
    """
    打印键值对项目
    
    Args:
        label: 标签
        value: 值
        indent: 缩进级别
    """
    prefix = "  " * indent
    print(f"{prefix}{Colors.BRIGHT_BLACK}{label}:{Colors.RESET} {value}")


def list_item(text: str, icon: str = ICONS['bullet'], indent: int = 0, 
              status: Optional[str] = None) -> None:
    """
    打印列表项
    
    Args:
        text: 文本内容
        icon: 图标
        indent: 缩进级别
        status: 状态（'success', 'error', 'warning', 'pending'）
    """
    prefix = "  " * indent
    
    # 根据状态选择颜色
    if status == 'success':
        icon = ICONS['success']
        color = Colors.BRIGHT_GREEN
    elif status == 'error':
        icon = ICONS['error']
        color = Colors.BRIGHT_RED
    elif status == 'warning':
        icon = ICONS['warning']
        color = Colors.BRIGHT_YELLOW
    elif status == 'pending':
        icon = ICONS['pending']
        color = Colors.BRIGHT_BLACK
    else:
        color = Colors.RESET
    
    print(f"{prefix}{color}{icon} {Colors.RESET}{text}")


def success(text: str, indent: int = 0) -> None:
    """成功消息"""
    prefix = "  " * indent
    print(f"{prefix}{Colors.BRIGHT_GREEN}{ICONS['success']} {text}{Colors.RESET}")


def error(text: str, indent: int = 0) -> None:
    """错误消息"""
    prefix = "  " * indent
    print(f"{prefix}{Colors.BRIGHT_RED}{ICONS['error']} {text}{Colors.RESET}")


def warning(text: str, indent: int = 0) -> None:
    """警告消息"""
    prefix = "  " * indent
    print(f"{prefix}{Colors.BRIGHT_YELLOW}{ICONS['warning']} {text}{Colors.RESET}")


def info(text: str, indent: int = 0) -> None:
    """信息消息"""
    prefix = "  " * indent
    print(f"{prefix}{Colors.BRIGHT_BLUE}{ICONS['info']} {text}{Colors.RESET}")


def progress(text: str, current: int, total: int, indent: int = 0) -> None:
    """
    打印进度信息
    
    Args:
        text: 描述文本
        current: 当前数量
        total: 总数
        indent: 缩进级别
    """
    prefix = "  " * indent
    pct = (current / total * 100) if total > 0 else 0
    print(f"{prefix}{Colors.BRIGHT_CYAN}{ICONS['running']} {text} ({current}/{total}, {pct:.0f%}){Colors.RESET}")


def result_summary(success: int, failed: int, skipped: int = 0) -> None:
    """打印结果汇总"""
    width = get_term_width()
    print(f"\n{Colors.DIM}{ICONS['separator'] * width}{Colors.RESET}")
    print(f"{Colors.BOLD}执行结果汇总{Colors.RESET}")
    
    if success > 0:
        print(f"  {Colors.BRIGHT_GREEN}{ICONS['success']} 成功: {success}{Colors.RESET}")
    if failed > 0:
        print(f"  {Colors.BRIGHT_RED}{ICONS['error']} 失败: {failed}{Colors.RESET}")
    if skipped > 0:
        print(f"  {Colors.BRIGHT_YELLOW}{ICONS['warning']} 跳过: {skipped}{Colors.RESET}")
    
    print(f"{Colors.DIM}{ICONS['separator'] * width}{Colors.RESET}\n")


def mode_badge(mode: str, source: str = '') -> None:
    """
    打印模式徽章
    
    Args:
        mode: 模式名称
        source: 数据源（Notion/Feishu/Local）
    """
    if source:
        print(f"\n{Colors.BRIGHT_BLUE}{Colors.BOLD}[{mode}]{Colors.RESET} {Colors.DIM}via{Colors.RESET} {Colors.BRIGHT_CYAN}{source}{Colors.RESET}")
    else:
        print(f"\n{Colors.BRIGHT_BLUE}{Colors.BOLD}[{mode}]{Colors.RESET}")


def count_badge(label: str, count: int, icon: str = '') -> None:
    """打印数量徽章"""
    icon_str = f"{icon} " if icon else ""
    if count > 0:
        print(f"  {icon_str}{label}: {Colors.BRIGHT_GREEN}{count}{Colors.RESET}")
    else:
        print(f"  {icon_str}{label}: {Colors.BRIGHT_BLACK}{count}{Colors.RESET}")


def empty_state(title: str, suggestions: list = None) -> None:
    """
    打印空状态提示
    
    Args:
        title: 标题
        suggestions: 建议列表
    """
    width = get_term_width()
    print(f"\n{Colors.BRIGHT_BLACK}{ICONS['separator'] * width}{Colors.RESET}")
    print(f"{Colors.BRIGHT_YELLOW}{ICONS['warning']} {title}{Colors.RESET}")
    
    if suggestions:
        print()
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {Colors.DIM}{i}.{Colors.RESET} {suggestion}")
    
    print(f"{Colors.BRIGHT_BLACK}{ICONS['separator'] * width}{Colors.RESET}\n")


def divider(char: str = '─', color: str = Colors.DIM) -> None:
    """打印分隔线"""
    width = get_term_width()
    print(f"{color}{char * width}{Colors.RESET}")


def debug(text: str) -> None:
    """调试信息（暗色显示）"""
    print(f"{Colors.DIM}{text}{Colors.RESET}")


# 便捷函数，兼容旧代码的 print 风格
def log_step(step: str, detail: str = '') -> None:
    """记录步骤"""
    if detail:
        print(f"{Colors.BRIGHT_CYAN}{ICONS['arrow']}{Colors.RESET} {step} {Colors.DIM}{detail}{Colors.RESET}")
    else:
        print(f"{Colors.BRIGHT_CYAN}{ICONS['arrow']}{Colors.RESET} {step}")


def log_found(what: str, count: int) -> None:
    """记录发现数量"""
    if count == 0:
        print(f"  {Colors.BRIGHT_BLACK}{ICONS['bullet']} 未发现 {what}{Colors.RESET}")
    elif count == 1:
        print(f"  {Colors.BRIGHT_GREEN}{ICONS['bullet']} 发现 1 个 {what}{Colors.RESET}")
    else:
        print(f"  {Colors.BRIGHT_GREEN}{ICONS['bullet']} 发现 {count} 个 {what}{Colors.RESET}")


def log_skip(what: str, reason: str) -> None:
    """记录跳过原因"""
    print(f"  {Colors.BRIGHT_YELLOW}{ICONS['warning']} 跳过 {what}{Colors.RESET}")
    if reason:
        print(f"    {Colors.DIM}原因: {reason}{Colors.RESET}")


def log_download(name: str, size_mb: float = 0) -> None:
    """记录下载完成"""
    size_str = f" ({size_mb:.2f} MB)" if size_mb > 0 else ""
    print(f"  {Colors.BRIGHT_GREEN}{ICONS['download']} 已下载 {name}{Colors.RESET}{Colors.DIM}{size_str}{Colors.RESET}")


# ==================== 数据源终端输出模板（公共封装）====================

def print_data_source_header(source_name: str) -> None:
    """
    阶段1：打印数据源头部信息
    
    Args:
        source_name: 数据源名称（Notion/飞书）
    """
    print(f"📡 从 {source_name} 获取视频数据...")


def print_records_returned(count: int) -> None:
    """
    打印返回记录数量
    
    Args:
        count: 记录数量
    """
    print(f"  • {count} 条记录")


def print_pending_videos(count: int, source_name: str = "") -> None:
    """
    阶段2：打印待上传视频列表头部
    
    Args:
        count: 待上传视频数量
        source_name: 数据源名称前缀（如"Notion中"）
    """
    prefix = f"{source_name}中" if source_name else ""
    print(f"\n📋 {prefix}待上传的视频 ({count} 个)：")


def print_pending_video_item(name: str, status: str, date_str: str, indent: int = 2) -> None:
    """
    打印单个待上传视频项
    
    Args:
        name: 视频名称
        status: 发布状态
        date_str: 发布日期字符串
        indent: 缩进空格数
    """
    print(f"{' ' * indent}• {name} [{status}] {date_str}")


def print_skipped_non_pending(count: int) -> None:
    """
    打印跳过的非待发布视频数量
    
    Args:
        count: 跳过数量
    """
    print(f"\n⏭️  跳过 {count} 个非待发布视频")


def print_no_videos_warning() -> None:
    """打印无视频警告"""
    print("\n⚠️ 没有待上传的视频")


def print_scan_local_videos(count: int) -> None:
    """
    阶段3：打印本地视频扫描结果
    
    Args:
        count: 本地视频文件数量
    """
    print(f"\n📁 扫描本地视频...")
    print(f"  找到 {count} 个本地视频文件")


def print_match_summary(
    local_count: int,
    download_count: int,
    no_source_count: int = 0,
    local_names: list = None,
    download_names: list = None,
    no_source_names: list = None
) -> None:
    """
    阶段4：打印匹配结果汇总
    
    Args:
        local_count: 本地已有视频数量
        download_count: 需要下载的视频数量
        no_source_count: 无视频来源的数量
        local_names: 本地视频名称列表（可选）
        download_names: 需下载视频名称列表（可选）
        no_source_names: 无来源视频名称列表（可选）
    """
    print(f"\n📊 匹配结果：")
    print(f"  ✅ 本地已有: {local_count} 个")
    if local_names:
        for name in local_names:
            print(f"     • {name}")
    
    print(f"  ⬇️  需要下载: {download_count} 个")
    if download_names:
        for name in download_names:
            print(f"     • {name}")
    
    if no_source_count > 0:
        print(f"  ⚠️  无视频来源: {no_source_count} 个")
        if no_source_names:
            for name in no_source_names:
                print(f"     • {name}")


def print_final_video_summary(videos: list) -> None:
    """
    阶段5：打印最终视频汇总列表
    
    Args:
        videos: VideoInfo 对象列表，需要有 name_for_match, publish_date, video_path 属性
    """
    # 按日期排序
    videos.sort(key=lambda x: x.publish_date, reverse=False)
    
    print(f"\n🎬 共 {len(videos)} 个视频准备上传（按日期排序）：")
    for v in videos:
        source = "本地" if v.video_path else "云端"
        date_str = v.publish_date.strftime('%Y-%m-%d') if hasattr(v.publish_date, 'strftime') else str(v.publish_date)
        print(f"  • {v.name_for_match} ({date_str}) [{source}]")
