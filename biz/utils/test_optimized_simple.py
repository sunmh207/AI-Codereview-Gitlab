#!/usr/bin/env python3
"""
测试优化后的个人日报功能（简化版，不依赖LLM）
"""

import os
import sys
from dotenv import load_dotenv

from biz.utils.feishu_bitable import FeishuBitableClient

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv(os.path.join(project_root, "../../conf/.env"))

from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.user_matcher import UserMatcher


class SimpleOptimizedReportService:
    """简化的优化日报服务，用于测试"""

    def __init__(self):
        self.feishu_notifier = FeishuNotifier()
        self.user_matcher = UserMatcher()

    def generate_and_send_individual_reports(self, commits):
        """为每个人生成个人日报并发送"""
        if not commits:
            return {
                'success': True,
                'message': '没有提交记录',
                'total_users': 0,
                'reports_generated': 0,
                'messages_sent': 0,
                'errors': [],
                'individual_results': []
            }

        # 按作者分组
        author_commits = {}
        for commit in commits:
            author = commit.get('author', 'Unknown')
            if author not in author_commits:
                author_commits[author] = []
            author_commits[author].append(commit)

        authors = list(author_commits.keys())
        print(f"共有 {len(authors)} 个作者需要生成个人日报")

        results = {
            'success': True,
            'message': f'处理了 {len(authors)} 个作者的个人日报',
            'total_users': len(authors),
            'reports_generated': 0,
            'messages_sent': 0,
            'errors': [],
            'individual_results': []
        }

        # 为每个作者处理
        for author in authors:
            individual_result = self._process_individual_author(author, author_commits[author])
            results['individual_results'].append(individual_result)

            if individual_result['report_generated']:
                results['reports_generated'] += 1

            if individual_result['message_sent']:
                results['messages_sent'] += 1

            if individual_result['errors']:
                results['errors'].extend(individual_result['errors'])

        return results

    def _process_individual_author(self, author, commits):
        """处理单个作者"""
        result = {
            'author': author,
            'commits_count': len(commits),
            'report_generated': False,
            'message_sent': False,
            'report_content': None,
            'errors': []
        }

        try:
            # 生成模拟个人日报
            print(f"为 {author} 生成个人日报 ({len(commits)} 条提交)")
            personal_report = self._generate_mock_personal_report(author, commits)

            # 发送到飞书多维表格
            feishu_client = FeishuBitableClient()
            if feishu_client.enabled:
                success = feishu_client.create_daily_report_record(personal_report, author)
                if success:
                    print(f"  📤 成功发送日报到飞书多维表格")
                else:
                    print(f"  ❌ 发送日报到飞书多维表格失败")
            result['report_content'] = personal_report
            result['report_generated'] = True

            # 匹配用户信息
            user_info = self._match_user_info(author)
            if not user_info:
                error_msg = f"无法匹配用户信息: {author}"
                result['errors'].append(error_msg)
                print(f"  ⚠️  {error_msg}")
                return result

            print(f"  ✅ 匹配到用户: {author}")

            # 发送飞书消息
            if self.feishu_notifier.enabled:
                message_sent = self._send_personal_report(user_info, personal_report, author)
                result['message_sent'] = message_sent

                if message_sent:
                    print(f"  📤 成功发送消息给 {author}")
                else:
                    print(f"  ❌ 发送消息失败: {author}")
                    result['errors'].append(f"发送消息失败: {author}")
            else:
                print(f"  ⚠️  飞书推送未启用，跳过给 {author} 发送消息")

        except Exception as e:
            error_msg = f"生成 {author} 的个人日报失败: {str(e)}"
            print(f"  ❌ {error_msg}")
            result['errors'].append(error_msg)

        return result

    def _generate_mock_personal_report(self, author, commits):
        """生成模拟个人日报"""
        total_commits = len(commits)
        total_additions = sum(commit.get('additions', 0) for commit in commits)
        total_deletions = sum(commit.get('deletions', 0) for commit in commits)

        report = f"""# {author} 的个人工作日报

## 今日工作概要
- 提交次数: {total_commits} 次
- 新增代码: {total_additions} 行
- 删除代码: {total_deletions} 行

## 提交详情
"""

        for i, commit in enumerate(commits, 1):
            report += f"{i}. {commit.get('commit_messages', 'N/A')}\n"
            report += f"   - 项目: {commit.get('project_name', 'N/A')}\n"
            report += f"   - 分支: {commit.get('branch', 'N/A')}\n"
            report += f"   - 新增: {commit.get('additions', 0)} 行, 删除: {commit.get('deletions', 0)} 行\n\n"

        report += f"""## 工作总结
今日共完成 {total_commits} 个功能点的开发，代码质量良好，按计划推进项目进度。

---
这是模拟生成的个人日报，用于测试优化后的功能。"""

        return report

    def _match_user_info(self, author):
        """匹配用户信息"""
        gitlab_users = self.user_matcher.get_all_gitlab_users()

        for user in gitlab_users:
            if user.get('name') == author or user.get('username') == author:
                return user

        return None

    def _send_personal_report(self, user_info, report_content, author):
        """发送个人日报"""
        try:
            from datetime import datetime

            formatted_message = f"""📊 个人工作日报 - {datetime.now().strftime('%Y-%m-%d')}

{report_content}

---
此报告由AI代码审查系统自动生成并发送（测试模式）"""

            # 获取open_id
            open_id = self.user_matcher.get_openid_by_gitlab_user(
                gitlab_username=user_info.get('username'),
                gitlab_name=user_info.get('name'),
                gitlab_email=user_info.get('email')
            )

            if not open_id:
                print(f"    ⚠️  无法获取 {author} 的飞书open_id")
                return False

            # 发送消息
            success = self.feishu_notifier.send_direct_message(
                open_id=open_id,
                content=formatted_message,
                msg_type='text'
            )

            return success

        except Exception as e:
            print(f"    ❌ 发送个人日报给 {author} 时出错: {str(e)}")
            return False


def create_test_commits():
    """创建测试提交数据"""
    real_users = ["庞江川"]

    test_commits = []

    for i, author in enumerate(real_users):
        # 每个作者创建2-3个提交记录
        for j in range(2 + (i % 2)):
            commit = {
                "author": author,
                "commit_messages": f"feat: {author}完成功能模块{j + 1}开发",
                "project_name": "AI-Codereview-Gitlab",
                "branch": "main",
                "updated_at": 1642780800 + i * 3600 + j * 1800,
                "additions": (i + j + 1) * 20,
                "deletions": (i + j + 1) * 5,
                "score": 90 + i + j
            }
            test_commits.append(commit)

    return test_commits


def main():
    """主函数"""
    print("优化后的个人日报功能测试（简化版）")
    print("=" * 50)

    try:
        # 创建测试数据
        test_commits = create_test_commits()
        print(f"创建了 {len(test_commits)} 条测试提交记录")

        # 统计作者
        authors = set(commit['author'] for commit in test_commits)
        print(f"涉及 {len(authors)} 个作者: {', '.join(sorted(authors))}")

        # 创建服务
        service = SimpleOptimizedReportService()

        # 显示服务状态
        user_stats = service.user_matcher.get_user_mapping_stats()
        print(f"\n服务状态:")
        print(f"  飞书启用: {'✅' if service.feishu_notifier.enabled else '❌'}")
        print(f"  飞书用户: {user_stats['feishu_users_count']}个")
        print(f"  GitLab用户: {user_stats['gitlab_users_count']}个")
        print(f"  用户匹配率: {user_stats['name_mappings_count'] / user_stats['gitlab_users_count'] * 100:.1f}%")

        # 执行个人日报生成
        print(f"\n开始生成个人日报...")
        results = service.generate_and_send_individual_reports(test_commits)

        # 显示结果
        print(f"\n处理结果:")
        print(f"  处理状态: {'✅ 成功' if results['success'] else '❌ 失败'}")
        print(f"  处理消息: {results['message']}")
        print(f"  总用户数: {results['total_users']}")
        print(f"  生成报告: {results['reports_generated']}")
        print(f"  发送消息: {results['messages_sent']}")

        if results['errors']:
            print(f"  错误信息:")
            for error in results['errors'][:3]:
                print(f"    - {error}")

        # 显示个人处理详情
        print(f"\n个人处理详情:")
        for individual in results.get('individual_results', []):
            report_status = "✅" if individual['report_generated'] else "❌"
            message_status = "📤" if individual['message_sent'] else "❌"
            print(f"  {report_status} {message_status} {individual['author']} ({individual['commits_count']}条提交)")

            if individual['errors']:
                print(f"    错误: {individual['errors'][0]}")

        print("\n" + "=" * 50)
        print("🎉 测试完成！")

        if results['success']:
            if results['messages_sent'] > 0:
                print("✅ 飞书消息发送功能正常")
            else:
                print("⚠️  飞书消息未发送（可能是权限或配置问题）")

        print(f"\n📊 最终统计:")
        print(f"  处理用户: {results['total_users']}")
        print(f"  生成报告: {results['reports_generated']}")
        print(f"  发送消息: {results['messages_sent']}")
        print(f"  成功率: {results['reports_generated'] / results['total_users'] * 100:.1f}%" if results[
                                                                                                     'total_users'] > 0 else "N/A")

    except Exception as e:
        print(f"❌ 测试过程中出现异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
