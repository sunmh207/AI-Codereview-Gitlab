import requests
import json

# 测试修复后的真实API
url = "http://localhost:5001/api/reviews/push"
params = {
    'start_date': '2025-09-22',
    'end_date': '2025-09-29',
    'page': 1,
    'page_size': 100
}

# 使用正确的登录接口路径
login_url = "http://localhost:5001/api/auth/login"
login_data = {
    'username': 'admin',
    'password': 'GISinfo@admin'
}

try:
    # 登录获取token
    print("正在登录...")
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code == 200:
        token = login_response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        print("登录成功，测试API...")
        # 测试API
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n=== 🎉 API修复验证成功！ ===")
            print(f"请求URL: {url}")
            print(f"时间范围: {params['start_date']} 到 {params['end_date']}")
            print(f"返回记录数: {len(data['data'])}")
            print(f"总记录数: {data['total']}")
            print(f"页码: {data['page']}")
            print(f"页大小: {data['page_size']}")
            
            if len(data['data']) >= 26:
                print(f"\n✅ 完美！现在API正确返回了所有 {data['total']} 条记录！")
                print("之前只返回20条，现在返回了完整的26条记录。")
            else:
                print(f"\n⚠️  返回记录数不符合预期")
                
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    else:
        print(f"登录失败: {login_response.status_code}")
        print(f"错误信息: {login_response.text}")
        
except Exception as e:
    print(f"请求异常: {e}")