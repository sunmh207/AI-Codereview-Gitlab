"""
日报路由模块
"""
import json
from datetime import datetime
from flask import Blueprint, jsonify

from biz.api import push_review_enabled
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.reporter import Reporter

daily_report_bp = Blueprint('daily_report', __name__)


def _generate_daily_report() -> str | None:
    """
    生成日报核心逻辑，返回日报文本，无数据返回None
    """
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    if push_review_enabled:
        df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
    else:
        df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

    logger.info(f"获取到 {len(df)} 条记录")

    if df.empty:
        logger.info("No data to process.")
        return None

    # 去重：基于 (author, message) 组合
    df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
    # 按照 author 排序
    df_sorted = df_unique.sort_values(by="author")
    # 转换为适合生成日报的格式
    commits = df_sorted.to_dict(orient="records")
    # 生成日报内容
    report_txt = Reporter().generate_report(json.dumps(commits))
    logger.info(f"日报生成成功，内容长度: {len(report_txt)} 字符")

    return report_txt


def daily_report_task():
    """
    日报任务函数，供调度器调用
    """
    try:
        logger.info("开始生成日报...")
        report_txt = _generate_daily_report()
        if report_txt is None:
            return
        # 发送钉钉通知
        notifier.send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")
        logger.info("日报发送成功")
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")


@daily_report_bp.route('/review/daily_report', methods=['GET'])
def daily_report():
    """
    日报路由处理函数
    """
    try:
        logger.info("开始生成日报...")
        report_txt = _generate_daily_report()
        if report_txt is None:
            return jsonify({'message': 'No data to process.'}), 200
        # 发送钉钉通知
        notifier.send_notification(content=report_txt, msg_type="markdown", title="代码提交日报")
        logger.info("日报发送成功")
        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500
