"""
测试调度器配置的脚本
"""
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv("conf/.env")

def test_job():
    print(f"[{datetime.now()}] Test job executed!")

def test_scheduler():
    """测试调度器配置"""
    crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
    print(f"Cron expression: {crontab_expression}")
    
    cron_parts = crontab_expression.split()
    cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts
    
    print(f"Parsed cron components:")
    print(f"  - minute: {cron_minute}")
    print(f"  - hour: {cron_hour}")
    print(f"  - day: {cron_day}")
    print(f"  - month: {cron_month}")
    print(f"  - day_of_week: {cron_day_of_week}")
    
    scheduler = BackgroundScheduler()
    
    job = scheduler.add_job(
        test_job,
        trigger=CronTrigger(
            minute=cron_minute,
            hour=cron_hour,
            day=cron_day,
            month=cron_month,
            day_of_week=cron_day_of_week
        ),
        id='test_job'
    )
    
    scheduler.start()
    
    print(f"\nScheduler started!")
    print(f"Next run time: {job.next_run_time}")
    print(f"Current time: {datetime.now()}")
    
    # 列出所有已调度的任务
    print("\nScheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"  - {job.id}: next run at {job.next_run_time}")
    
    scheduler.shutdown()
    print("\nScheduler test completed!")

if __name__ == '__main__':
    test_scheduler()
