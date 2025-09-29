import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()

# 转换时间字符串为时间戳
start_date = "2025-09-22"
end_date = "2025-09-29"

start_timestamp = int(datetime.fromisoformat(start_date + "T00:00:00").timestamp())
end_timestamp = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp())

print(f"查询时间范围: {start_date} 到 {end_date}")
print(f"时间戳范围: {start_timestamp} 到 {end_timestamp}")

# 查询这个时间范围内的记录
cursor.execute('''
    SELECT COUNT(*) FROM push_review_log 
    WHERE updated_at >= ? AND updated_at <= ?
''', (start_timestamp, end_timestamp))

count_in_range = cursor.fetchone()[0]
print(f"时间范围内的记录数: {count_in_range}")

# 查看所有记录的时间分布
cursor.execute('''
    SELECT id, author, project_name, updated_at,
           datetime(updated_at, 'unixepoch') as readable_time
    FROM push_review_log 
    ORDER BY updated_at DESC
''')

all_records = cursor.fetchall()
print(f"\n所有记录的时间分布:")
for record in all_records:
    in_range = start_timestamp <= record[3] <= end_timestamp
    status = "✓" if in_range else "✗"
    print(f"  {status} ID:{record[0]}, 时间:{record[4]}, 作者:{record[1]}")

conn.close()