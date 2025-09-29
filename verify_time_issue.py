import sqlite3
from datetime import datetime

# API中的错误时间转换
start_date = "2025-09-22"
end_date = "2025-09-29"

# API当前的转换逻辑（有问题）
start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
start_timestamp = int(start_datetime.timestamp())
end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))  # 这里有问题！
end_timestamp = int(end_datetime.timestamp())

print(f"=== API当前的时间转换（有问题）===")
print(f"开始时间: {start_date} -> {start_timestamp} ({start_datetime})")
print(f"结束时间: {end_date} -> {end_timestamp} ({end_datetime})")

# 查询数据库
conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT COUNT(*) FROM push_review_log 
    WHERE updated_at >= ? AND updated_at <= ?
''', (start_timestamp, end_timestamp))

count_with_bug = cursor.fetchone()[0]
print(f"API当前逻辑查询结果: {count_with_bug} 条")

# 正确的时间转换
correct_end_datetime = datetime.fromisoformat(end_date + 'T23:59:59+00:00')
correct_end_timestamp = int(correct_end_datetime.timestamp())

print(f"\n=== 正确的时间转换 ===")
print(f"结束时间应该是: {end_date} -> {correct_end_timestamp} ({correct_end_datetime})")

cursor.execute('''
    SELECT COUNT(*) FROM push_review_log 
    WHERE updated_at >= ? AND updated_at <= ?
''', (start_timestamp, correct_end_timestamp))

count_correct = cursor.fetchone()[0]
print(f"正确逻辑查询结果: {count_correct} 条")

# 显示被过滤掉的记录
print(f"\n=== 被错误过滤掉的记录 ===")
cursor.execute('''
    SELECT id, author, datetime(updated_at, 'unixepoch') as readable_time, updated_at
    FROM push_review_log 
    WHERE updated_at > ? AND updated_at <= ?
    ORDER BY updated_at DESC
''', (end_timestamp, correct_end_timestamp))

filtered_out = cursor.fetchall()
print(f"被过滤掉的记录数: {len(filtered_out)}")
for record in filtered_out:
    print(f"  ID:{record[0]}, 作者:{record[1]}, 时间:{record[2]}, 时间戳:{record[3]}")

conn.close()