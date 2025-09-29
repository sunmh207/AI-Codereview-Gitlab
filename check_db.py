import sqlite3
import os

# 检查数据库文件
db_files = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db') or file.endswith('.sqlite'):
            db_files.append(os.path.join(root, file))

print('找到的数据库文件:')
for db_file in db_files:
    print(f'  {db_file}')

# 检查主数据库
if os.path.exists('data/data.db'):
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'\n数据库表: {[t[0] for t in tables]}')
    
    # 检查所有表的记录数
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'{table_name} 表记录数: {count}')
        
        if count > 0:
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = [col[1] for col in cursor.fetchall()]
            print(f'  列名: {columns}')
            
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 1')
            row = cursor.fetchone()
            print(f'  示例数据: {row}')
    
    conn.close()
else:
    print('数据库文件 data/data.db 不存在')