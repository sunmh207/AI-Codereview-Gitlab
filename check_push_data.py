import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()

# 查看push_review_log表的总记录数
cursor.execute('SELECT COUNT(*) FROM push_review_log')
total_count = cursor.fetchone()[0]
print(f'Push表总记录数: {total_count}')

# 查看最近几条记录的时间范围
cursor.execute('SELECT MIN(updated_at), MAX(updated_at) FROM push_review_log')
time_range = cursor.fetchone()
print(f'时间范围: {time_range[0]} 到 {time_range[1]}')

# 转换时间戳为可读格式
if time_range[0] and time_range[1]:
    min_time = datetime.fromtimestamp(time_range[0]).strftime('%Y-%m-%d %H:%M:%S')
    max_time = datetime.fromtimestamp(time_range[1]).strftime('%Y-%m-%d %H:%M:%S')
    print(f'可读时间范围: {min_time} 到 {max_time}')

# 查看最近10条记录
cursor.execute('SELECT id, author, project_name, updated_at FROM push_review_log ORDER BY updated_at DESC LIMIT 10')
recent_records = cursor.fetchall()
print('\n最近10条记录:')
for record in recent_records:
    readable_time = datetime.fromtimestamp(record[3]).strftime('%Y-%m-%d %H:%M:%S')
    print(f'  ID: {record[0]}, 作者: {record[1]}, 项目: {record[2]}, 时间: {readable_time}')

# 检查是否有重复记录
cursor.execute('SELECT author, project_name, COUNT(*) as count FROM push_review_log GROUP BY author, project_name HAVING count > 1')
duplicates = cursor.fetchall()
if duplicates:
    print('\n重复记录:')
    for dup in duplicates:
        print(f'  作者: {dup[0]}, 项目: {dup[1]}, 重复次数: {dup[2]}')
else:
    print('\n没有发现重复记录')

conn.close()