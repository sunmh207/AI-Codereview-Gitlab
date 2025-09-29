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
    print(f"登录状态码: {login_response.status_code}")
    
    if login_response.status_code == 200:
        token = login_response.json().get('access_token')
        print(f"获取到token: {token[:50]}...")
        
        # 测试API
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试不同的page_size
        test_cases = [
            {"page_size": 20},
            {"page_size": 50}, 
            {"page_size": 100},
            {"page_size": 10000},
            {}  # 不传page_size
        ]
        
        for params in test_cases:
            response = requests.get("http://localhost:5001/api/reviews/push", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n参数 {params}:")
                print(f"  返回记录数: {len(data.get('data', []))}")
                print(f"  总数: {data.get('total', 'N/A')}")
                print(f"  页数: {data.get('page', 'N/A')}")
                print(f"  页大小: {data.get('page_size', 'N/A')}")
            else:
                print(f"\n参数 {params}: 请求失败 {response.status_code}")
    else:
        print(f"登录失败: {login_response.text}")
        
except Exception as e:
    print(f"请求错误: {e}")