from datetime import datetime

# 测试API中的时间转换逻辑
start_date = "2025-09-22"
end_date = "2025-09-29"

print("=== API中的时间转换逻辑 ===")

# API代码中的逻辑
try:
    start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    start_timestamp = int(start_datetime.timestamp())
    print(f"开始时间转换成功: {start_date} -> {start_timestamp}")
except Exception as e:
    print(f"开始时间转换失败: {e}")

try:
    end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    end_timestamp = int(end_datetime.timestamp())
    print(f"结束时间转换成功: {end_date} -> {end_timestamp}")
except Exception as e:
    print(f"结束时间转换失败: {e}")

# 检查是否会导致None值
print(f"\nstart_timestamp: {start_timestamp if 'start_timestamp' in locals() else 'None'}")
print(f"end_timestamp: {end_timestamp if 'end_timestamp' in locals() else 'None'}")

# 测试不同的时间格式
test_dates = [
    "2025-09-22",
    "2025-09-22Z", 
    "2025-09-22T00:00:00",
    "2025-09-22T00:00:00Z"
]

print(f"\n=== 测试不同时间格式 ===")
for date_str in test_dates:
    try:
        converted = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        timestamp = int(converted.timestamp())
        print(f"✓ {date_str} -> {timestamp} ({converted})")
    except Exception as e:
        print(f"✗ {date_str} -> 错误: {e}")