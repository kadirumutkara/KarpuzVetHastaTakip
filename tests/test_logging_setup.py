import logging
import tempfile
import unittest
from pathlib import Path

from karpuzvet.logging_setup import configure_logging, get_log_paths


class LoggingSetupTests(unittest.TestCase):
    def test_get_log_paths_creates_expected_names(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_log, error_log = get_log_paths(Path(tmp_dir))
            self.assertTrue(app_log.parent.exists())
            self.assertIn("app-", app_log.name)
            self.assertIn("errors-", error_log.name)

    def test_configure_logging_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_log, error_log = configure_logging(Path(tmp_dir))
            logger = logging.getLogger("karpuzvet.tests.logging")
            logger.info("bilgi kaydi")
            logger.error("hata kaydi")
            for handler in logging.getLogger().handlers:
                handler.flush()
            self.assertTrue(app_log.exists())
            self.assertTrue(error_log.exists())
            self.assertIn("bilgi kaydi", app_log.read_text(encoding="utf-8"))
            self.assertIn("hata kaydi", error_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
