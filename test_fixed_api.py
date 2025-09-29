import requests
import json

# 测试修复后的API
url = "http://localhost:5001/api/reviews/push"
params = {
    'start_date': '2025-09-22',
    'end_date': '2025-09-29',
    'page': 1,
    'page_size': 100
}

# 先获取token
login_url = "http://localhost:5001/api/login"
login_data = {
    'username': 'admin',
    'password': 'GISinfo@admin'
}

try:
    # 登录获取token
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code == 200:
        token = login_response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # 测试API
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"=== 修复后的API测试结果 ===")
            print(f"状态码: {response.status_code}")
            print(f"返回记录数: {len(data['data'])}")
            print(f"总记录数: {data['total']}")
            print(f"页码: {data['page']}")
            print(f"页大小: {data['page_size']}")
            print(f"总页数: {data.get('total_pages', 'N/A')}")
            
            if len(data['data']) > 0:
                print(f"\n前3条记录:")
                for i, record in enumerate(data['data'][:3]):
                    print(f"  {i+1}. ID:{record.get('id')}, 作者:{record.get('author')}, 时间:{record.get('updated_at')}")
                    
            print(f"\n=== 成功！现在返回了 {len(data['data'])} 条记录，总共 {data['total']} 条 ===")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    else:
        print(f"登录失败: {login_response.status_code}")
        print(f"错误信息: {login_response.text}")
        
except Exception as e:
    print(f"请求异常: {e}")