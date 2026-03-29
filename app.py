from __future__ import annotations

import logging
import sys
import threading
from time import sleep

from karpuzvet.logging_setup import configure_logging
from karpuzvet.test_agent import run_startup_checks
from karpuzvet.webapp import launch_web_app


def _install_exception_hooks() -> None:
    logger = logging.getLogger("karpuzvet.app")

    def _handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.exception("Beklenmeyen uygulama hatasi.", exc_info=(exc_type, exc_value, exc_traceback))

    def _thread_exception_handler(args):
        logger.exception(
            "Thread icinde beklenmeyen hata olustu.",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _handle_exception
    threading.excepthook = _thread_exception_handler


if __name__ == "__main__":
    app_log, error_log = configure_logging()
    _install_exception_hooks()
    logger = logging.getLogger("karpuzvet.app")
    logger.info("Uygulama baslatiliyor. app_log=%s error_log=%s", app_log, error_log)
    for message in run_startup_checks():
        logger.info("startup-check: %s", message)
        print(f"[startup-check] {message}")
    server = launch_web_app()
    logger.info("Yerel uygulama basladi. address=http://127.0.0.1:%s", server.server_address[1])
    print(f"Karpuz Vet yerel uygulama basladi: http://127.0.0.1:{server.server_address[1]}")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logger.info("Uygulama kullanici tarafindan kapatildi.")
        server.shutdown()
