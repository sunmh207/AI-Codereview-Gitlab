#!/bin/bash

# 测试优化后的 API 路由（支持时间范围参数）
# 使用方法: ./test_api_curl.sh

echo "🚀 测试优化后的 API 路由: /review/users_without_review"
echo "============================================================"

# API 端点
BASE_URL="http://localhost:5001/review/users_without_review"

# 测试用例数组
declare -a test_cases=(
    "历史所有记录:$BASE_URL?time_range=all"
    "当天记录:$BASE_URL?time_range=today"
    "近一周记录:$BASE_URL?time_range=week"
    "自定义时间范围:$BASE_URL?start_time=$(date -d '3 days ago' +%s)&end_time=$(date +%s)"
)

# 遍历测试用例
for i in "${!test_cases[@]}"; do
    IFS=':' read -r test_name test_url <<< "${test_cases[$i]}"

    echo ""
    echo "📊 测试 $((i+1)): $test_name"
    echo "📡 请求 URL: $test_url"
    echo "----------------------------------------"

    # 发送请求并格式化输出
    response=$(curl -s -X GET "$test_url" -H "Content-Type: application/json")

    # 检查响应是否为有效 JSON
    if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
        echo "$response" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"✅ 请求成功: {data.get('success', False)}\")
print(f\"📝 消息: {data.get('message', 'N/A')}\")
if 'data' in data:
    d = data['data']
    print(f\"📊 统计信息:\")
    print(f\"   • 飞书总用户数: {d.get('total_feishu_users', 0)}\")
    print(f\"   • 有审查记录用户数: {d.get('total_reviewed_users', 0)}\")
    print(f\"   • 无审查记录用户数: {d.get('total_unreviewed_users', 0)}\")
    print(f\"   • 审查覆盖率: {d.get('review_coverage_rate', 0)}%\")
    print(f\"   • 时间范围: {d.get('time_range', 'N/A')}\")
"
    else
        echo "❌ 响应格式错误或服务不可用"
        echo "$response"
    fi

    echo "----------------------------------------"
done

echo ""
echo "============================================================"
echo "✅ 所有测试完成"
echo ""
echo "📝 使用说明:"
echo "  • 端点: GET /review/users_without_review"
echo "  • 功能: 分析代码审查记录，返回没有审查记录的人员列表"
echo "  • 返回: JSON 格式的用户列表和统计信息"
echo ""
echo "🔧 支持的查询参数:"
echo "  • time_range: 时间范围 (all|today|week)"
echo "    - all: 历史所有记录（默认）"
echo "    - today: 当天记录"
echo "    - week: 近一周记录"
echo "  • start_time: 自定义开始时间戳（Unix时间戳）"
echo "  • end_time: 自定义结束时间戳（Unix时间戳）"
echo ""
echo "📊 返回数据结构:"
echo "  • success: 请求是否成功"
echo "  • message: 响应消息"
echo "  • data.users_with_review: 有审查记录的用户列表"
echo "  • data.users_without_review: 没有审查记录的用户详细信息"
echo "  • data.total_feishu_users: 飞书总用户数"
echo "  • data.total_reviewed_users: 有审查记录的用户数"
echo "  • data.total_unreviewed_users: 没有审查记录的用户数"
echo "  • data.review_coverage_rate: 审查覆盖率(%)"
echo "  • data.time_range: 查询的时间范围描述"
echo "  • data.query_params: 实际使用的查询参数"
echo ""
echo "💡 示例用法:"
echo "  curl 'http://localhost:5001/review/users_without_review?time_range=today'"
echo "  curl 'http://localhost:5001/review/users_without_review?start_time=1690000000&end_time=1690086400'"
