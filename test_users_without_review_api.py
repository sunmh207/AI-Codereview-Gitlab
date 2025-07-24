#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试未审查用户API接口
"""

import requests
import json
import time

# API 基础地址
BASE_URL = "http://localhost:5001"

def test_users_without_review_default():
    """测试获取未审查用户接口（默认参数）"""
    print("👥 测试获取未审查用户接口（默认参数）...")
    
    response = requests.get(f"{BASE_URL}/review/users_without_review")
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('success') and 'data' in result:
            data = result['data']
            required_fields = ['users_without_review', 'total_developers', 'total_unreviewed_users', 'review_coverage_rate', 'time_range']
            
            if all(field in data for field in required_fields):
                print("✅ 获取未审查用户成功")
                print(f"   总开发者数: {data['total_developers']}")
                print(f"   未审查用户数: {data['total_unreviewed_users']}")
                print(f"   审查覆盖率: {data['review_coverage_rate']}%")
                print(f"   时间范围: {data['time_range']}")
                return True
            else:
                print("❌ 响应数据字段不完整")
                return False
        else:
            print("❌ 响应格式错误")
            return False
    else:
        print("❌ 获取未审查用户失败")
        return False

def test_users_without_review_week():
    """测试获取未审查用户接口（近一周）"""
    print("\n📅 测试获取未审查用户接口（近一周）...")
    
    params = {'time_range': 'week'}
    response = requests.get(f"{BASE_URL}/review/users_without_review", params=params)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('success') and 'data' in result:
            data = result['data']
            if '近一周' in data.get('time_range', ''):
                print("✅ 近一周未审查用户获取成功")
                return True
            else:
                print("❌ 时间范围不正确")
                return False
        else:
            print("❌ 响应格式错误")
            return False
    else:
        print("❌ 近一周未审查用户获取失败")
        return False

def test_users_without_review_today():
    """测试获取未审查用户接口（当天）"""
    print("\n📅 测试获取未审查用户接口（当天）...")
    
    params = {'time_range': 'today'}
    response = requests.get(f"{BASE_URL}/review/users_without_review", params=params)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('success') and 'data' in result:
            data = result['data']
            if '当天' in data.get('time_range', ''):
                print("✅ 当天未审查用户获取成功")
                return True
            else:
                print("❌ 时间范围不正确")
                return False
        else:
            print("❌ 响应格式错误")
            return False
    else:
        print("❌ 当天未审查用户获取失败")
        return False

def test_users_without_review_custom_time():
    """测试自定义时间范围的未审查用户接口"""
    print("\n📅 测试自定义时间范围的未审查用户接口...")
    
    # 测试自定义时间范围（最近30天）
    end_time = int(time.time())
    start_time = end_time - (30 * 24 * 60 * 60)  # 30天前
    
    params = {
        'start_time': start_time,
        'end_time': end_time
    }
    
    response = requests.get(f"{BASE_URL}/review/users_without_review", params=params)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('success') and 'data' in result:
            data = result['data']
            if '自定义时间范围' in data.get('time_range', ''):
                print("✅ 自定义时间范围未审查用户获取成功")
                print(f"   时间范围: {data['time_range']}")
                return True
            else:
                print("❌ 自定义时间范围格式错误")
                return False
        else:
            print("❌ 响应格式错误")
            return False
    else:
        print("❌ 自定义时间范围未审查用户获取失败")
        return False

def test_invalid_time_range():
    """测试无效的时间范围参数"""
    print("\n❌ 测试无效的时间范围参数...")
    
    params = {'time_range': 'invalid'}
    response = requests.get(f"{BASE_URL}/review/users_without_review", params=params)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 400:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if not result.get('success') and 'time_range 参数无效' in result.get('message', ''):
            print("✅ 无效时间范围参数正确被拒绝")
            return True
        else:
            print("❌ 错误消息不正确")
            return False
    else:
        print("❌ 无效时间范围参数未返回400状态码")
        return False

def test_invalid_timestamp():
    """测试无效的时间戳格式"""
    print("\n❌ 测试无效的时间戳格式...")
    
    params = {
        'start_time': 'invalid',
        'end_time': '123'
    }
    
    response = requests.get(f"{BASE_URL}/review/users_without_review", params=params)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 400:
        result = response.json()
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if not result.get('success') and '时间戳格式错误' in result.get('message', ''):
            print("✅ 无效时间戳格式正确被拒绝")
            return True
        else:
            print("❌ 错误消息不正确")
            return False
    else:
        print("❌ 无效时间戳格式未返回400状态码")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试未审查用户API接口")
    print("=" * 60)
    
    # 测试服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API 服务器运行正常 (状态码: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 API 服务器，请确保服务器正在运行")
        print("请运行: python api.py")
        return
    
    # 执行各项测试
    tests = [
        test_users_without_review_default,
        test_users_without_review_week,
        test_users_without_review_today,
        test_users_without_review_custom_time,
        test_invalid_time_range,
        test_invalid_timestamp
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 出现异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎉 未审查用户API测试完成！")
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("✅ 所有测试通过！未审查用户API功能正常")
    else:
        print("❌ 部分测试失败，请检查实现")
    
    print("\n💡 提示:")
    print("1. 确保后端API服务正在运行")
    print("2. 确保developer.json文件存在且包含开发者信息")
    print("3. 现在可以在Vue3前端的'未审查用户'标签页中查看界面")
    print("4. Vue3前端地址: http://localhost:3000")

if __name__ == "__main__":
    main()
