from datetime import datetime
import sqlite3

# 测试时间转换逻辑（模拟API中的转换）
start_date = "2025-09-22"
end_date = "2025-09-29"

# API中的转换逻辑
start_datetime = datetime.fromisoformat(start_date + 'T00:00:00+00:00')
end_datetime = datetime.fromisoformat(end_date + 'T23:59:59+00:00')

start_timestamp = int(start_datetime.timestamp())
end_timestamp = int(end_datetime.timestamp())

print(f"API时间转换:")
print(f"  开始日期: {start_date} -> {start_timestamp} ({start_datetime})")
print(f"  结束日期: {end_date} -> {end_timestamp} ({end_datetime})")

# 查询数据库
conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()

# 使用API相同的查询逻辑
query = """
    SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
    FROM push_review_log
    WHERE updated_at >= ? AND updated_at <= ?
    ORDER BY updated_at DESC
"""

cursor.execute(query, (start_timestamp, end_timestamp))
filtered_records = cursor.fetchall()

print(f"\n数据库查询结果:")
print(f"  筛选后记录数: {len(filtered_records)}")

print(f"\n所有记录的时间对比:")
cursor.execute("SELECT id, updated_at, datetime(updated_at, 'unixepoch') as readable_time, author FROM push_review_log ORDER BY updated_at DESC")
all_records = cursor.fetchall()

for record in all_records:
    in_range = start_timestamp <= record[1] <= end_timestamp
    status = "✓" if in_range else "✗"
    print(f"  {status} ID:{record[0]}, 时间戳:{record[1]}, 时间:{record[2]}, 作者:{record[3]}")

conn.close()