import os
from multiprocessing import Process

from dotenv import load_dotenv
from redis import Redis
from rq import Queue

load_dotenv()
queue_driver = os.getenv('QUEUE_DRIVER', 'async')

if queue_driver == 'rq':
    queues = {}

def handle_queue(function: callable, data: any, gitlab_token: str, gitlab_url: str, target_queue: str):
    if queue_driver == 'rq':
        if target_queue not in queues:
            queues[target_queue] = Queue(target_queue, connection=Redis(os.getenv('REDIS_HOST', '127.0.0.1'), os.getenv('REDIS_PORT', 6379)))

        queues[target_queue].enqueue(function, data, gitlab_token, gitlab_url)
    else:
        process = Process(target=function, args=(data, gitlab_token, gitlab_url))
        process.start()
