import sqlite3
from datetime import datetime

# 直接测试数据库查询，验证修复效果
print("=== 测试时间转换修复效果 ===")

# 模拟API修复前的逻辑（错误）
start_date = "2025-09-22"
end_date = "2025-09-29"

# 错误的转换（API修复前）
start_datetime_old = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
start_timestamp_old = int(start_datetime_old.timestamp())
end_datetime_old = datetime.fromisoformat(end_date.replace('Z', '+00:00'))  # 问题在这里
end_timestamp_old = int(end_datetime_old.timestamp())

# 正确的转换（API修复后）
start_datetime_new = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
start_timestamp_new = int(start_datetime_new.timestamp())
end_date_with_time = end_date + 'T23:59:59'  # 修复：添加时间
end_datetime_new = datetime.fromisoformat(end_date_with_time.replace('Z', '+00:00'))
end_timestamp_new = int(end_datetime_new.timestamp())

print(f"修复前 - 开始时间: {start_datetime_old} ({start_timestamp_old})")
print(f"修复前 - 结束时间: {end_datetime_old} ({end_timestamp_old})")
print(f"修复后 - 开始时间: {start_datetime_new} ({start_timestamp_new})")
print(f"修复后 - 结束时间: {end_datetime_new} ({end_timestamp_new})")

# 查询数据库
conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()

# 修复前的查询结果
cursor.execute('''
    SELECT COUNT(*) FROM push_review_log 
    WHERE updated_at >= ? AND updated_at <= ?
''', (start_timestamp_old, end_timestamp_old))
count_old = cursor.fetchone()[0]

# 修复后的查询结果
cursor.execute('''
    SELECT COUNT(*) FROM push_review_log 
    WHERE updated_at >= ? AND updated_at <= ?
''', (start_timestamp_new, end_timestamp_new))
count_new = cursor.fetchone()[0]

print(f"\n=== 查询结果对比 ===")
print(f"修复前API逻辑: {count_old} 条记录")
print(f"修复后API逻辑: {count_new} 条记录")
print(f"修复效果: 增加了 {count_new - count_old} 条记录")

conn.close()

if count_new > count_old:
    print(f"\n✅ 修复成功！API现在能正确返回所有 {count_new} 条记录了！")
else:
    print(f"\n❌ 修复可能有问题，请检查")