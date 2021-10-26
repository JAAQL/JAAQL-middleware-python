import unittest
import time
import inspect
import sys


class BaseTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)

        self.passed = 0
        self.failed = 0

    def start_profiler(self):
        self.start_time = round(time.time() * 1000)

    def print_profiler(self, part):
        cur_time = round(time.time() * 1000)
        print("'" + part + "' took " + str(cur_time - self.start_time) + "ms")
        self.start_time = cur_time

    def reset_profiler(self):
        self.start_time = round(time.time() * 1000)

    def pause_profiler(self):
        self.pause_time = round(time.time() * 1000)

    def unpause_profiler(self):
        self.start_time += round(time.time() * 1000) - self.pause_time

    def run_test(self, expected, actual, name: str, output_val: bool = False, require_exact_column_order: bool = False):
        try:
            calling_frame = inspect.currentframe().f_back.f_code.co_name + ": "
        except:
            calling_frame = ""

        ret = expected == actual

        success_message = "Test (" + self.__class__.__name__ + ") '" + calling_frame + name + "' passed." + ((" Value '" + str(expected) + "' received") if output_val else "")
        error_message = "Test (" + self.__class__.__name__ + ") '" + calling_frame + name + "' failed." + (" Expected '" + str(expected) + "', received '" + str(actual) + "'")
        if ret:
            print(success_message)
            self.passed += 1
        else:
            print(error_message, file=sys.stderr)
            self.failed += 1

        self.assertEqual(expected, actual, calling_frame + name)

    def run_all(self):
        check = True

        funcs = [func for func in dir(self) if callable(getattr(self, func)) and (func.startswith("test_") or func == "setUp")]

        if 'setUp' in funcs:
            getattr(self, 'setUp')()
            if self.passed == 0 or self.failed != 0:
                check = False

        for func in funcs:
            if func != 'setUp':
                last_passed = self.passed
                getattr(self, func)()
                if self.passed == last_passed or self.failed != 0:
                    check = False

        return check and self.passed != 0
