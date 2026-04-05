"""
视频匹配工具模块

提供视频文件与文件夹名的智能匹配算法
支持多视频场景下的最佳匹配选择
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from difflib import SequenceMatcher


def remove_date_prefix(text: str) -> str:
    """
    去除常见的日期前缀
    
    支持的前缀格式：
    - YYMMDD (6位数字，如 260404)
    - MMDD (4位数字，如 0404)
    - DD (2位数字，如 04)
    
    Args:
        text: 原始文本
        
    Returns:
        去除日期前缀后的文本
    """
    # 模式1: YYMMDD (6位数字开头)
    pattern1 = r'^\d{6}'
    # 模式2: MMDD (4位数字开头)
    pattern2 = r'^\d{4}'
    # 模式3: 其他常见前缀（数字+分隔符）
    pattern3 = r'^\d{2,6}[-_\.\s]*'
    
    result = text
    
    # 尝试去除前缀
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.match(pattern, result)
        if match:
            result = result[match.end():].strip()
            break
    
    return result


def calculate_similarity(s1: str, s2: str) -> float:
    """
    计算两个字符串的相似度（基于包含关系）
    
    Args:
        s1: 第一个字符串
        s2: 第二个字符串
        
    Returns:
        0.0 ~ 1.0 的相似度分数
    """
    if not s1 or not s2:
        return 0.0
    
    # 如果一个是另一个的子串，相似度较高
    if s1 in s2:
        return len(s1) / len(s2)
    if s2 in s1:
        return len(s2) / len(s1)
    
    # 计算共同子串比例
    return SequenceMatcher(None, s1, s2).ratio()


def select_best_matching_video(
    video_files: List[Path], 
    folder_name: str,
    verbose: bool = True
) -> Tuple[Optional[Path], float]:
    """
    从多个视频文件中选择与文件夹名最匹配的那个
    
    匹配策略（按优先级排序）：
    1. 完全匹配（去除日期前缀后相等）-> 100分
    2. 包含匹配（一方包含另一方）-> 80分
    3. 相似度匹配 -> 相似度*70分
    
    Args:
        video_files: 候选视频文件列表
        folder_name: 文件夹名称（用于匹配）
        verbose: 是否打印选择结果
        
    Returns:
        Tuple[最佳匹配的视频文件, 匹配得分]
        如果没有匹配则返回 (None, 0.0)
    """
    if not video_files:
        return None, 0.0
    
    if len(video_files) == 1:
        return video_files[0], 100.0
    
    # 清理文件夹名（去除日期前缀）
    folder_name_clean = remove_date_prefix(folder_name)
    
    best_match = None
    best_score = 0.0
    match_details = []  # 记录所有匹配详情，用于调试
    
    for vf in video_files:
        video_name = vf.stem  # 不含扩展名的文件名
        video_name_clean = remove_date_prefix(video_name)
        
        # 计算匹配得分
        score = 0.0
        match_type = ""
        
        if folder_name_clean == video_name_clean:
            # 完全匹配
            score = 100.0
            match_type = "完全匹配"
        elif folder_name_clean in video_name_clean or video_name_clean in folder_name_clean:
            # 包含匹配
            score = 80.0
            match_type = "包含匹配"
        else:
            # 相似度匹配
            score = calculate_similarity(folder_name_clean, video_name_clean) * 70
            match_type = "相似度匹配"
        
        match_details.append((vf.name, video_name_clean, score, match_type))
        
        if score > best_score:
            best_score = score
            best_match = vf
    
    # 打印选择结果
    if verbose and best_match:
        print(f"📁 文件夹 '{folder_name}' 中有 {len(video_files)} 个视频，选择最匹配: '{best_match.name}'")
        # 打印匹配详情（调试信息）
        for name, clean, score, mtype in sorted(match_details, key=lambda x: x[2], reverse=True):
            marker = "✓" if name == best_match.name else "  "
            print(f"   {marker} {name} -> '{clean}' ({mtype}: {score:.1f}分)")
    
    return best_match, best_score


def find_best_match_in_list(
    target: str,
    candidates: List[str],
    threshold: float = 0.6
) -> Tuple[Optional[str], float]:
    """
    在候选列表中查找与目标字符串最匹配的项
    
    匹配策略：
    1. 精确匹配（去除前后空格后相等）-> 1.0
    2. 包含匹配（一方包含另一方）-> 0.8
    3. 相似度匹配 -> 实际相似度（需超过 threshold）
    
    Args:
        target: 目标字符串
        candidates: 候选字符串列表
        threshold: 相似度阈值（默认 0.6）
        
    Returns:
        Tuple[最佳匹配的字符串, 匹配得分]
        如果没有匹配则返回 (None, 0.0)
    """
    clean_target = target.strip()
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        clean_candidate = candidate.strip()
        
        # 策略1：精确匹配
        if clean_target == clean_candidate:
            return candidate, 1.0
        
        # 策略2：包含匹配
        if clean_target in clean_candidate or clean_candidate in clean_target:
            score = 0.8
            if score > best_score:
                best_score = score
                best_match = candidate
            continue
        
        # 策略3：相似度匹配
        similarity = calculate_similarity(clean_target, clean_candidate)
        if similarity > threshold and similarity > best_score:
            best_score = similarity
            best_match = candidate
    
    return best_match, best_score
