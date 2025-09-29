# 开发工具目录

这个目录包含了项目的调试脚本和测试文件，不应该部署到生产环境。

## 目录结构

### debug/
包含各种调试脚本：
- `check_db.py` - 数据库检查脚本
- `check_push_data.py` - Push数据检查脚本
- `debug_api_directly.py` - API直接调试脚本
- `debug_time_filter.py` - 时间过滤调试脚本
- `verify_time_issue.py` - 时间问题验证脚本

### tests/
包含各种测试脚本：
- `test_api.py` - API测试脚本
- `test_fixed_api.py` - 修复后的API测试
- `test_fixed_api_simple.py` - 简化的API测试
- `test_real_api.py` - 真实API测试
- `test_service.py` - 服务测试
- `test_specific_api.py` - 特定API测试
- `test_time_conversion.py` - 时间转换测试
- `test_time_filter.py` - 时间过滤测试

## 使用说明

1. 这些脚本仅用于开发和调试目的
2. 不应该在生产环境中运行
3. 在提交代码时，请确保这些文件不会被包含在主分支中

## 注意事项

- 运行这些脚本前请确保已经配置好开发环境
- 某些脚本可能需要特定的环境变量或配置文件
- 请在安全的开发环境中运行，避免影响生产数据