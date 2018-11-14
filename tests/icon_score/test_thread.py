import threading
import random
import time
import unittest


class TestThread(unittest.TestCase):
    class MyClassThreadSafe:
        def __init__(self):
            self.data = threading.local()
            self.data.x = 0

    class MyClass:
        class data:
            pass

        def __init__(self):
            self.data = self.data()
            self.data.x = 0

    def test_thread(self):
        mycls = self.MyClassThreadSafe()

        for i in range(1, 10):
            t = threading.Thread(target=self.set_value, args=(mycls, i, ))
            t.start()

    def test_unsafe(self):
        mycls = self.MyClass()

        for i in range(1, 10):
            t = threading.Thread(target=self.set_value_for_unsafe, args=(mycls, i, ))
            t.start()

    def set_value(self, mycls, i):
        tmp = i
        time.sleep(random.random())
        mycls.data.x = tmp
        time.sleep(random.random())
        self.assertEqual(tmp, mycls.data.x)
        print(mycls.data.x)

    def set_value_for_unsafe(self, mycls, i):
        tmp = i
        time.sleep(random.random())
        mycls.data.x = tmp
        time.sleep(random.random())
        print(f"maybe unsafe : {mycls.data.x} != {tmp}")
