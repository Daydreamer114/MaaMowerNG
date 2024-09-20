from __future__ import annotations

import subprocess

from arknights_mower import __system__
from arknights_mower.utils.device.adb_client.core import Client as ADBClient
from arknights_mower.utils.log import logger


class Session:
    def __init__(self, client: ADBClient) -> None:
        self.process = subprocess.Popen(
            [
                client.adb_bin,
                "-s",
                client.device_id,
                "shell",
                "CLASSPATH=/data/local/tmp/maatouch",
                "app_process",
                "/",
                "com.shxyke.MaaTouch.App",
            ],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if __system__ == "windows" else 0,
        )

        # ^ <max-contacts> <max-x> <max-y> <max-pressure>
        _, max_contacts, max_x, max_y, max_pressure, *_ = (
            self.process.stdout.readline().strip().split(" ")
        )
        self.max_contacts = max_contacts
        self.max_x = max_x
        self.max_y = max_y
        self.max_pressure = max_pressure

        # $ <pid>
        _, pid = self.process.stdout.readline().strip().split(" ")
        self.pid = pid

        logger.debug(f"{self.pid=}")
        logger.debug(f"{max_contacts=} {max_x=} {max_y=} {max_pressure=}")

    def __enter__(self) -> Session:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        self.process.terminate()

    def send(self, content: str):
        self.process.stdin.write(content)
        self.process.stdin.flush()
