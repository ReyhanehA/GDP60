from xmlrunner.unittest import unittest

import sys
import os
from os import path
import glob
import tempfile
import shutil

try:
    import django
except ImportError:
    django = None
else:
    from django.test.utils import get_runner
    from django.conf import settings, UserSettingsHolder
    from django.apps import apps


TESTS_DIR = path.dirname(__file__)


@unittest.skipIf(django is None, 'django not found')
class DjangoTest(unittest.TestCase):

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.project_dir = path.abspath(path.join(TESTS_DIR, 'django_example'))
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.project_dir)
        sys.path.append(self.project_dir)
        # allow changing settings
        self.old_settings = settings._wrapped
        os.environ['DJANGO_SETTINGS_MODULE'] = 'example.settings'
        settings.INSTALLED_APPS  # load settings on first access
        settings.DATABASES['default']['NAME'] = path.join(
            self.tmpdir, 'db.sqlilte3')
        # this goes around the "settings already loaded" issue.
        self.override = UserSettingsHolder(settings._wrapped)
        settings._wrapped = self.override

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmpdir)
        settings._wrapped = self.old_settings

    def _override_settings(self, **kwargs):
        # see django.test.utils.override_settings
        for key, new_value in kwargs.items():
            setattr(self.override, key, new_value)

    def _check_runner(self, runner):
        suite = runner.build_suite(test_labels=['app2', 'app'])
        test_ids = [test.id() for test in suite]
        self.assertEqual(test_ids, [
            'app2.tests.DummyTestCase.test_pass',
            'app.tests.DummyTestCase.test_pass',
        ])
        suite = runner.build_suite(test_labels=[])
        test_ids = [test.id() for test in suite]
        self.assertEqual(set(test_ids), set([
            'app.tests.DummyTestCase.test_pass',
            'app2.tests.DummyTestCase.test_pass',
        ]))

    def test_django_runner(self):
        runner_class = get_runner(settings)
        runner = runner_class()
        self._check_runner(runner)

    def test_django_xmlrunner(self):
        self._override_settings(
            TEST_RUNNER='xmlrunner.extra.djangotestrunner.XMLTestRunner')
        runner_class = get_runner(settings)
        runner = runner_class()
        self._check_runner(runner)

    def test_django_verbose(self):
        self._override_settings(
            TEST_OUTPUT_VERBOSE=True,
            TEST_RUNNER='xmlrunner.extra.djangotestrunner.XMLTestRunner')
        runner_class = get_runner(settings)
        runner = runner_class()
        self._check_runner(runner)

    def test_django_single_report(self):
        self._override_settings(
            TEST_OUTPUT_DIR=self.tmpdir,
            TEST_OUTPUT_FILE_NAME='results.xml',
            TEST_OUTPUT_VERBOSE=0,
            TEST_RUNNER='xmlrunner.extra.djangotestrunner.XMLTestRunner')
        apps.populate(settings.INSTALLED_APPS)
        runner_class = get_runner(settings)
        runner = runner_class()
        suite = runner.build_suite()
        runner.run_suite(suite)
        expected_file = path.join(self.tmpdir, 'results.xml')
        self.assertTrue(path.exists(expected_file),
                        'did not generate xml report where expected.')

    def test_django_multiple_reports(self):
        self._override_settings(
            TEST_OUTPUT_DIR=self.tmpdir,
            TEST_OUTPUT_VERBOSE=0,
            TEST_RUNNER='xmlrunner.extra.djangotestrunner.XMLTestRunner')
        apps.populate(settings.INSTALLED_APPS)
        runner_class = get_runner(settings)
        runner = runner_class()
        suite = runner.build_suite(test_labels=None)
        runner.run_suite(suite)
        test_files = glob.glob(path.join(self.tmpdir, 'TEST*.xml'))
        self.assertTrue(test_files,
                        'did not generate xml reports where expected.')
        self.assertEqual(2, len(test_files))
