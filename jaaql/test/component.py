import sys
import subprocess
import glob
import unittest
from jaaql.test.components.component_utils import wait_for_service


def is_test_file(file):
    return file.split(".")[-2] not in ["base_component", "__init__", "component_utils"]


def run_component_tests():
    test_files = [
        ".".join(test_file.replace("\\", ".").replace("/", ".").split(".")[:-1])
        for test_file in glob.glob("components/*.py", recursive=True)
        if is_test_file(test_file.replace("\\", ".").replace("/", "."))
    ]
    test_files.sort()

    suites = [
        unittest.defaultTestLoader.loadTestsFromName(test_file)
        for test_file in test_files
    ]
    test_suite = unittest.TestSuite(suites)
    runner = unittest.TextTestRunner(verbosity=2)  # For local debugging
    result = runner.run(test_suite)

    if len(result.errors) != 0 or len(result.failures) != 0:
        print("Component test failure!", file=sys.stderr)
    else:
        print("Component tests all passed")

    if not sys.platform.lower().startswith('win'):
        pid = open("app.pid", "r").read()
        subprocess.call("kill -HUP " + pid, shell=True)  # Kill gunicorn so coverage report is generated


if __name__ == "__main__":
    wait_for_service()

    run_component_tests()

    if not sys.platform.lower().startswith('win'):
        app_pid = open("app.pid", "r").read()
        subprocess.call("kill -HUP " + app_pid, shell=True)  # Kill gunicorn so coverage report is generated
