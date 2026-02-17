import os
from multiprocessing import Process

from biz.utils.log import logger


def handle_queue(function: callable, data: any, token: str, url: str, url_slug: str):
    process = Process(target=function, args=(data, token, url, url_slug))
    process.start()


def handle_opencode_queue(function: callable, *args):
    """异步执行 opencode review 请求，传入 MR/PR URL 等参数"""
    process = Process(target=function, args=args)
    process.start()
