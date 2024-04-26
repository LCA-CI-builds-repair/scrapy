from __future__ import annotations

import os
import sys
from typing import Iterable, List, Optional, Tuple, cast

from twisted.internet.defer import Deferred
from twisted.internet.error import ProcessTerminated
from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure


class ProcessTest:
    command = None
    prefix = [sys.executable, "-m", "scrapy.cmdline"]
    cwd = os.getcwd()  # trial chdirs to temp dir

    def execute(
    def _process_finished(
        self, pp: TestProcessProtocol, cmd: List[str], check_code: bool
    ) -> Union[Tuple[int, bytes, bytes], None]:
        if pp.exitcode and check_code:
            msg = f"process {cmd} exit with code {pp.exitcode}"
            msg += f"\n>>> stdout <<<\n{pp.out.decode()}"
            msg += "\n"
            msg += f"\n>>> stderr <<<\n{pp.err.decode()}"
            raise RuntimeError(msg)
        return cast(int, pp.exitcode), pp.out, pp.err


class TestProcessProtocol(ProcessProtocol):
    def __init__(self) -> None:
        self.deferred: Deferred = Deferred()
        self.out: bytes = b""
        self.err: bytes = b""
        self.exitcode: Optional[int] = None

    def outReceived(self, data: bytes) -> None:
        self.out += data

    def errReceived(self, data: bytes) -> None:
        self.err += data

    def processEnded(self, status: Failure) -> None:
        self.exitcode = cast(ProcessTerminated, status.value).exitCode
        self.deferred.callback(self)
