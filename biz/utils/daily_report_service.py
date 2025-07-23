import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from biz.utils.reporter import Reporter
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.user_matcher import UserMatcher
from biz.utils.feishu_bitable import FeishuBitableClient
from biz.utils.log import logger


class DailyReportService:
    """优化后的日报生成和发送服务 - 每个人生成自己的日报"""

    def __init__(self):
        """初始化日报服务"""
        self.reporter = Reporter()
        self.feishu_notifier = FeishuNotifier()
        self.user_matcher = UserMatcher()

    def generate_and_send_individual_reports(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        为每个人生成个人日报并发送飞书消息
        :param commits: 提交记录列表
        :return: 处理结果统计
        """
        if not commits:
            logger.info("没有提交记录，跳过日报生成")
            return {
                'success': True,
                'message': '没有提交记录',
                'total_users': 0,
                'reports_generated': 0,
                'messages_sent': 0,
                'errors': []
            }

        # 按作者分组commits
        author_commits = self._group_commits_by_author(commits)
        authors = list(author_commits.keys())

        # 初始化结果统计
        results = {
            'success': True,
            'message': f'处理了 {len(authors)} 个作者的个人日报',
            'total_users': len(authors),
            'reports_generated': 0,
            'messages_sent': 0,
            'errors': [],
            'individual_results': []
        }

        # 为每个作者生成个人日报
        for author in authors:
            try:
                individual_result = self._process_individual_author(author, author_commits[author])
                results['individual_results'].append(individual_result)

                if individual_result['report_generated']:
                    results['reports_generated'] += 1

                if individual_result['message_sent']:
                    results['messages_sent'] += 1

                if individual_result['errors']:
                    results['errors'].extend(individual_result['errors'])

            except Exception as e:
                error_msg = f"处理作者 {author} 时出错: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['success'] = False

        logger.info(f"个人日报处理完成: 生成{results['reports_generated']}份报告, 发送{results['messages_sent']}条消息")
        return results

    def _group_commits_by_author(self, commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按作者分组提交记录"""
        author_commits = {}
        for commit in commits:
            author = commit.get('author', 'Unknown')
            if author not in author_commits:
                author_commits[author] = []
            author_commits[author].append(commit)
        return author_commits

    def _process_individual_author(self, author: str, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理单个作者的个人日报
        :param author: 作者名称
        :param commits: 该作者的提交记录
        :return: 处理结果
        """
        result = {
            'author': author,
            'commits_count': len(commits),
            'report_generated': False,
            'message_sent': False,
            'report_content': None,
            'errors': []
        }

        try:
            # 生成个人日报
            personal_report = self.reporter.generate_report(json.dumps(commits))

            # 发送到飞书多维表格
            try:
                feishu_client = FeishuBitableClient(self.user_matcher)
                feishu_client.create_daily_report_record(personal_report, author)
            except Exception as e:
                logger.error(f"飞书多维表格数据插入失败: {str(e)}")

            result['report_content'] = personal_report
            result['report_generated'] = True

            # 匹配用户信息
            user_info = self._match_user_info(author)
            if not user_info:
                error_msg = f"无法匹配用户信息: {author}"
                result['errors'].append(error_msg)
                logger.warning(error_msg)
                return result

            # 发送飞书消息
            if self.feishu_notifier.enabled:
                message_sent = self._send_personal_report(user_info, personal_report, author)
                result['message_sent'] = message_sent

                if not message_sent:
                    result['errors'].append(f"发送消息失败: {author}")
            else:
                logger.info(f"飞书推送未启用，跳过给 {author} 发送消息")

        except Exception as e:
            error_msg = f"生成 {author} 的个人日报失败: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        return result

    def _match_user_info(self, author: str) -> Optional[Dict[str, str]]:
        """
        匹配用户信息
        :param author: 作者名称
        :return: 用户信息字典或None
        """
        # 尝试匹配GitLab用户信息
        gitlab_users = self.user_matcher.get_all_gitlab_users()

        for user in gitlab_users:
            if user.get('name') == author or user.get('username') == author:
                return user

        # 如果没有匹配到，返回None
        logger.warn(f"未找到作者 {author} 的 gitlab 用户信息")
        return None

    def _send_personal_report(self, user_info: Dict[str, str], report_content: str, author: str) -> bool:
        """
        发送个人日报
        :param user_info: 用户信息
        :param report_content: 报告内容
        :param author: 作者名称
        :return: 发送是否成功
        """
        try:
            # 获取用户的open_id
            open_id = self.user_matcher.get_openid_by_gitlab_user(
                gitlab_username=user_info.get('username'),
                gitlab_name=user_info.get('name'),
                gitlab_email=user_info.get('email')
            )

            if not open_id:
                return False

            # 发送消息
            success = self.feishu_notifier.send_direct_message(
                open_id=open_id,
                content=report_content,
                msg_type='text'
            )

            if not success:
                logger.warning(f"发送个人日报给 {author} 失败")

            return success

        except Exception as e:
            logger.error(f"发送个人日报给 {author} 时出错: {str(e)}")
            return False

    def generate_summary_report(self, individual_results: List[Dict[str, Any]]) -> str:
        """
        生成汇总报告
        :param individual_results: 个人处理结果列表
        :return: 汇总报告内容
        """
        total_authors = len(individual_results)
        successful_reports = sum(1 for r in individual_results if r['report_generated'])
        successful_messages = sum(1 for r in individual_results if r['message_sent'])
        total_commits = sum(r['commits_count'] for r in individual_results)

        summary = f"""# 每日汇总 - {datetime.now().strftime('%Y-%m-%d')}

## 处理统计
- 总作者数: {total_authors}
- 总提交数: {total_commits}

## 作者列表
"""

        for result in individual_results:
            status_icon = "✅" if result['report_generated'] else "❌"
            message_icon = "📤" if result['message_sent'] else "❌"
            summary += f"- {status_icon} {message_icon} {result['author']} ({result['commits_count']}条提交)\n"

        # 添加错误信息
        all_errors = []
        for result in individual_results:
            all_errors.extend(result.get('errors', []))

        if all_errors:
            summary += f"\n## 错误信息\n"
            for error in all_errors[:10]:  # 只显示前10个错误
                summary += f"- {error}\n"
            if len(all_errors) > 10:
                summary += f"... 还有 {len(all_errors) - 10} 个错误\n"

        summary += f"\n---\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return summary
