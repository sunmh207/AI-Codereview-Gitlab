import requests
import json

# 先登录获取token
login_data = {
    "username": "admin",
    "password": "GISinfo@admin"
}

try:
    # 登录
    login_response = requests.post("http://localhost:5001/api/auth/login", json=login_data)
    
    if login_response.status_code == 200:
        token = login_response.json().get('access_token')
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试具体的API调用
        params = {
            "start_date": "2025-09-22",
            "end_date": "2025-09-29", 
            "page": 1,
            "page_size": 100
        }
        
        response = requests.get("http://localhost:5001/api/reviews/push", 
                              headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"API响应:")
            print(f"  返回记录数: {len(data.get('data', []))}")
            print(f"  总数: {data.get('total', 'N/A')}")
            print(f"  页数: {data.get('page', 'N/A')}")
            print(f"  页大小: {data.get('page_size', 'N/A')}")
            print(f"  总页数: {data.get('total_pages', 'N/A')}")
            
            # 显示前几条记录的时间
            records = data.get('data', [])
            if records:
                print(f"\n前5条记录的时间:")
                for i, record in enumerate(records[:5]):
                    print(f"  {i+1}. {record.get('updated_at', 'N/A')} - {record.get('author', 'N/A')}")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
    else:
        print(f"登录失败: {login_response.text}")
        
except Exception as e:
    print(f"请求错误: {e}")