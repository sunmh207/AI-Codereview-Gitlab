import os
from multiprocessing import Process

from dotenv import load_dotenv
from redis import Redis
from rq import Queue

load_dotenv()
queue_driver = os.getenv('QUEUE_DRIVER', 'async')

if queue_driver == 'rq':
    queues = {}

def handle_queue(function: callable, data: any, gitlab_token: str, gitlab_url: str, gitlab_domain_slug: str):
    if queue_driver == 'rq':
        if gitlab_domain_slug not in queues:
            queues[gitlab_domain_slug] = Queue(gitlab_domain_slug, connection=Redis(os.getenv('REDIS_HOST', '127.0.0.1'), os.getenv('REDIS_PORT', 6379)))

        queues[gitlab_domain_slug].enqueue(function, data, gitlab_token, gitlab_url, gitlab_domain_slug)
    else:
        process = Process(target=function, args=(data, gitlab_token, gitlab_url, gitlab_domain_slug))
        process.start()
