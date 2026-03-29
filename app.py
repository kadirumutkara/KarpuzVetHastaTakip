from time import sleep

from karpuzvet.test_agent import run_startup_checks
from karpuzvet.webapp import launch_web_app


if __name__ == "__main__":
    for message in run_startup_checks():
        print(f"[startup-check] {message}")
    server = launch_web_app()
    print(f"Karpuz Vet yerel uygulama basladi: http://127.0.0.1:{server.server_address[1]}")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
