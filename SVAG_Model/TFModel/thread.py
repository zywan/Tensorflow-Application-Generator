"""
implement TaskManager as a Singleton. So that there is only one instance of TaskManager in the program.
"""
import threading
import logging
from threading import Thread
from queue import Queue
from web import update_task_info


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# Class TaskManager is a Singleton
class TaskManager(object, metaclass=Singleton):
    def __init__(self, thread_num=1):
        self.task_queue = Queue()
        self.thread_num = thread_num
        self.__init_threading_pool(self.thread_num)
        self.task_dict = {}
        self.logger = logging.getLogger('task_manager')

    def get_task_info(self, task_id):
        """
        return task information by task id
        :param task_id: task id from HTTP GET Request
        :return: task information
        """
        return self.task_dict.get(task_id, {})

    def __init_threading_pool(self, thread_num):
        """
        Init and run thread_num threads
        :param thread_num: how many threads needed
        :return:
        """
        for i in range(thread_num):
            thread = TaskThread(self.task_queue)
            thread.start()

    def add_job(self, task_info):
        """
        add new task to the queue
        :param task_info: task information
        :return:
        """
        self.task_dict[task_info['taskId']] = {
            'thread': '',
            'progress': 0,
            'userId': task_info['userId'],
            'projectId': task_info['projectId'],
            'projectDir': task_info['projectDir'],
            'trainType': task_info['trainType'],
            'state': 'pending',
            'modelPath': ''
        }
        self.logger.info("[task Manager]recv and add a new task: {}".format(task_info['taskId']))
        self.task_queue.put(task_info['taskId'])


# class BottleneckProducer(object):
#     def __init__(self, thread_num=1):
#         self.task_queue = Queue()
#         self.thread_num = thread_num
#         self.__init_threading_pool(self.thread_num)
#         self.logger = logging.getLogger('task_manager')
#
#     def __init_threading_pool(self, thread_num):
#         """
#         Init and run thread_num threads
#         :param thread_num: how many threads needed
#         :return:
#         """
#         for i in range(thread_num):
#             thread = TaskThread(self.task_queue)
#             thread.start()


from train import train
from server import get_debug_mode


class TaskThread(Thread):
    def __init__(self, task_queue):
        Thread.__init__(self)
        self.task_queue = task_queue
        self.daemon = True
        self.task_id = ''
        self.logger = logging.getLogger('task_manager')
        self.thread_name = threading.current_thread().getName()

    def run(self):
        """
        handle task: training a model
        :return:
        """
        while True:
            self.task_id = self.task_queue.get()
            self.logger.info("get task({})".format(self.task_id))
            TaskManager().task_dict[self.task_id]['state'] = 'processing'
            method = TaskManager().task_dict[self.task_id]['trainType']
            user_dir = TaskManager().task_dict[self.task_id]['projectDir']
            self.logger.info("start training...")
            update_task_info(self.task_id, TaskManager().task_dict[self.task_id])
            model_file_path = ""
            if get_debug_mode():
                import time
                time.sleep(30)
            else:
                model_file_path = train(self.task_id, method, user_dir)
            self.logger.info("training finished")
            if model_file_path is None:
                TaskManager().task_dict[self.task_id]['state'] = 'done with error'
                TaskManager().task_dict[self.task_id]['modelPath'] = ""
            else:
                TaskManager().task_dict[self.task_id]['state'] = 'done'
                TaskManager().task_dict[self.task_id]['modelPath'] = model_file_path
            TaskManager().task_dict[self.task_id]['progress'] = 100
            self.logger.info("updating task info to web server")
            update_task_info(self.task_id, TaskManager().task_dict[self.task_id])
            self.task_queue.task_done()

# class BottleneckThread(Thread):
#     def __init__(self, task_queue):
#         Thread.__init__(self)
#         self.task_queue = task_queue
#         self.daemon = True
#         self.logger = logging.getLogger('task_manager')
#         self.thread_name = threading.current_thread().getName()
#
#     def run(self):
#         """
#         handle task: training a model
#         :return:
#         """
#         while True:
#             bottleneck_ = self.task_queue.get()