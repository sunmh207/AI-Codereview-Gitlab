import os
from multiprocessing import Process

from redis import Redis
from rq import Queue

from biz.utils.log import logger

queue_driver = os.getenv('QUEUE_DRIVER', 'async')

if queue_driver == 'rq':
    queues = {}


def handle_queue(function: callable, data: any, token: str, url: str, url_slug: str):
    if queue_driver == 'rq':
        if url_slug not in queues:
            logger.info(f'REDIS_HOST: {os.getenv("REDIS_HOST", "127.0.0.1")}，REDIS_PORT: {os.getenv("REDIS_PORT", 6379)}')
            queues[url_slug] = Queue(url_slug, connection=Redis(os.getenv('REDIS_HOST', '127.0.0.1'),
                                                                              os.getenv('REDIS_PORT', 6379)))

        queues[url_slug].enqueue(function, data, token, url, url_slug)
    else:
        process = Process(target=function, args=(data, token, url, url_slug))
        process.start()
