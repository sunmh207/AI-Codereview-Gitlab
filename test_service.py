from biz.service.review_service import ReviewService
import pandas as pd

# 测试获取所有push记录
df = ReviewService.get_push_review_logs()
print(f"ReviewService返回的记录数: {len(df)}")
print(f"DataFrame shape: {df.shape}")

if not df.empty:
    print("\n前5条记录:")
    print(df.head())
    
    print(f"\n列名: {list(df.columns)}")
    
    # 检查是否有时间筛选问题
    print(f"\n时间范围:")
    if 'updated_at' in df.columns:
        print(f"最小时间戳: {df['updated_at'].min()}")
        print(f"最大时间戳: {df['updated_at'].max()}")