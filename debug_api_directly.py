from biz.service.review_service import ReviewService
from datetime import datetime
import pandas as pd

# 模拟API调用的完整流程
start_date = "2025-09-22"
end_date = "2025-09-29"
page = 1
page_size = 100

print(f"=== 调试API流程 ===")
print(f"输入参数: start_date={start_date}, end_date={end_date}, page={page}, page_size={page_size}")

# 1. 转换时间
start_datetime = datetime.fromisoformat(start_date + 'T00:00:00+00:00')
start_timestamp = int(start_datetime.timestamp())
end_datetime = datetime.fromisoformat(end_date + 'T23:59:59+00:00')
end_timestamp = int(end_datetime.timestamp())

print(f"时间转换: {start_timestamp} 到 {end_timestamp}")

# 2. 调用ReviewService
print(f"\n=== 调用ReviewService ===")
df = ReviewService().get_push_review_logs(
    authors=None,
    project_names=None,
    updated_at_gte=start_timestamp,
    updated_at_lte=end_timestamp
)

print(f"ReviewService返回: {len(df)} 条记录")
print(f"DataFrame shape: {df.shape}")

if not df.empty:
    print(f"DataFrame列: {list(df.columns)}")
    print(f"时间范围: {df['updated_at'].min()} 到 {df['updated_at'].max()}")
    
    # 3. 应用得分筛选（这里没有）
    print(f"\n=== 得分筛选后 ===")
    print(f"记录数: {len(df)}")
    
    # 4. 应用排序
    print(f"\n=== 排序后 ===")
    if 'updated_at' in df.columns:
        df = df.sort_values(by='updated_at', ascending=False)
    print(f"记录数: {len(df)}")
    
    # 5. 获取总数
    total = len(df)
    print(f"\n=== 分页前总数 ===")
    print(f"总数: {total}")
    
    # 6. 应用分页
    print(f"\n=== 应用分页 ===")
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    print(f"分页索引: {start_idx} 到 {end_idx}")
    
    df_page = df.iloc[start_idx:end_idx]
    print(f"分页后记录数: {len(df_page)}")
    
    # 7. 转换为记录
    records = df_page.to_dict('records')
    print(f"最终返回记录数: {len(records)}")
    
    print(f"\n=== 最终结果 ===")
    print(f"data: {len(records)} 条")
    print(f"total: {total}")
    print(f"page: {page}")
    print(f"page_size: {page_size}")
    
    # 显示前几条记录
    print(f"\n前5条记录:")
    for i, record in enumerate(records[:5]):
        print(f"  {i+1}. {record.get('updated_at', 'N/A')} - {record.get('author', 'N/A')}")
else:
    print("DataFrame为空！")