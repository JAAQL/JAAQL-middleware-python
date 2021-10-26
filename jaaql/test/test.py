import glob
import sys
import unittest
import importlib as imp
import coverage

if __name__ == "TODO":
    test_files = glob.glob('**/test_*.py', recursive=True)
    module_strings = [test_file[0:len(test_file) - 3].replace("\\", ".") for test_file in test_files]
    modules_to_test = [x.replace('\\', '/')[0:len(x.replace('\\', '/'))-1] for x in glob.glob('units/*/') if '__' not in x]

    running_coverage = False
    if sys.gettrace() is None:
        running_coverage = True
        cov = coverage.Coverage(branch=True, source=modules_to_test, omit=["*__init__*", "*test\*"])
        cov.exclude("^from *")
        cov.exclude("^import *")
        cov.start()

        for module in sys.modules.values():  # Reloads all modules that are not tests. Helps with coverage reports
            try:
                test = module.BaseUnit
                try:
                    test = module.BaseTest
                except:
                    found = False
                    name = "test_" + module.__file__.split("\\")[-1:][0].split(".")[0]
                    for test_file in module_strings:
                        if name == test_file.split(".")[-1:][0]:
                            found = True
                    if found:
                        imp.reload(module)
            except Exception:
                pass

    suites = [unittest.defaultTestLoader.loadTestsFromName(test_file) for test_file in module_strings]
    test_suite = unittest.TestSuite(suites)

    runner = unittest.TextTestRunner()

    result = runner.run(test_suite)

    if running_coverage:
        cov.stop()
        cov.save()
        cov.html_report()

    if len(result.errors) != 0 or len(result.failures) != 0:
        print("Unit test failure. Exiting app", file=sys.stderr)
        sys.exit(1)