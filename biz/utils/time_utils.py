"""
时间处理工具模块
提供统一的日期时间转换和处理功能
"""
from datetime import datetime, timezone
from typing import Optional, Union


def parse_datetime_with_timezone(dt_str: Optional[str]) -> Optional[datetime]:
    """
    解析带时区信息的日期时间字符串
    
    Args:
        dt_str: 日期时间字符串，格式如 "2024-01-01T10:00:00+08:00"
        
    Returns:
        解析后的datetime对象，如果输入为None或解析失败则返回None
    """
    if not dt_str:
        return None
    
    try:
        # 处理带时区信息的ISO格式日期时间
        if dt_str.endswith('Z'):
            # UTC时间格式
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        elif '+' in dt_str or dt_str.count('-') > 2:
            # 带时区偏移的格式
            return datetime.fromisoformat(dt_str)
        else:
            # 无时区信息，假设为UTC
            dt = datetime.fromisoformat(dt_str)
            return dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def format_datetime_for_response(dt: Optional[datetime]) -> Optional[str]:
    """
    将datetime对象格式化为API响应格式
    
    Args:
        dt: datetime对象
        
    Returns:
        格式化后的日期时间字符串，如果输入为None则返回None
    """
    if not dt:
        return None
    
    # 确保有时区信息
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()


def convert_date_to_timestamps(start_date: Optional[str], end_date: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """
    将日期字符串转换为时间戳
    
    Args:
        start_date: 开始日期字符串
        end_date: 结束日期字符串
        
    Returns:
        (start_timestamp, end_timestamp) 元组
    """
    start_timestamp = None
    end_timestamp = None
    
    if start_date:
        start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        start_timestamp = int(start_datetime.timestamp())
        
    if end_date:
        # 对于结束日期，如果没有时间部分，添加时间以包含整天 (23:59:59)
        if 'T' not in end_date:
            end_date_with_time = end_date + 'T23:59:59'
        else:
            end_date_with_time = end_date
        end_datetime = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
        end_timestamp = int(end_datetime.timestamp())
    
    return start_timestamp, end_timestamp


def format_dataframe_timestamps(df, column_name: str = 'updated_at'):
    """
    格式化DataFrame中的时间戳列
    
    Args:
        df: pandas DataFrame
        column_name: 时间戳列名
        
    Returns:
        格式化后的DataFrame副本
    """
    if df.empty or column_name not in df.columns:
        return df
    
    df_copy = df.copy()
    df_copy[column_name] = df_copy[column_name].apply(
        lambda ts: datetime.fromtimestamp(ts).isoformat() + 'Z'
        if isinstance(ts, (int, float)) else ts
    )
    return df_copy