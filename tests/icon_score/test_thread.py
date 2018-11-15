import logging
import threading
import random
import time
import unittest


class TestThread(unittest.TestCase):
    cls_thread_safe = None
    cls_thread_safe_unsafe_get = None

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG,
                            format='(%(threadName)-10s) %(message)s', )

    def tearDown(self):
        logging.basicConfig(level=logging.DEBUG,
                            format=logging.BASIC_FORMAT, )

    class MyClassThreadSafeUsingThreadLocal:
        class Data(threading.local):
            def __init__(self, x):
                self.x = x

        def __init__(self, x):
            self.data = self.Data(x)

    class MyClassThreadSafeUnsafeGet:
        def __init__(self, x):
            self.data = threading.local()
            self.data.x = x

    class MyClass:
        class Data:
            def __init__(self, x):
                self.x = x

        def __init__(self, x):
            self.data = self.Data(x)

    def get_global_my_cls_thread_safe(self):
        if self.cls_thread_safe is None:
            self.cls_thread_safe = self.MyClassThreadSafeUsingThreadLocal(999)
        return self.cls_thread_safe

    def get_global_my_cls_thread_safe_unsafe_get(self):
        if self.cls_thread_safe_unsafe_get is None:
            self.cls_thread_safe_unsafe_get = self.MyClassThreadSafeUnsafeGet(999)
        return self.cls_thread_safe_unsafe_get

    def test_thread_set(self):
        for i in range(1, 10):
            t = threading.Thread(target=self.set_value, args=(self.get_global_my_cls_thread_safe, i, ))
            t.start()

    def test_thread_set_unsafe_get(self):
        for i in range(1, 10):
            t = threading.Thread(target=self.set_value, args=(self.get_global_my_cls_thread_safe_unsafe_get, i, ))
            t.start()

    def test_unsafe_set(self):
        mycls = self.MyClass(0)

        for i in range(1, 10):
            t = threading.Thread(target=self.set_value_for_unsafe, args=(mycls, i, ))
            t.start()

    def set_value(self, func, i):
        tmp = i
        time.sleep(random.random())
        mycls = func()

        try:
            logging.error(f"get_value : {mycls.data.x}")
        except:
            logging.error("miss attr")

        mycls.data.x = tmp
        logging.error(f"set_value : {mycls.data.x}")
        time.sleep(random.random())
        self.assertEqual(tmp, mycls.data.x)
        logging.error(f"set_value : {mycls.data.x}")

    def set_value_for_unsafe(self, mycls, i):
        tmp = i
        time.sleep(random.random())
        mycls.data.x = tmp
        time.sleep(random.random())
        logging.error(f"maybe unsafe : {mycls.data.x} != {tmp}")
