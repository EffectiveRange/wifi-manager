# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from threading import Thread
from typing import Optional, Any

from context_logger import get_logger
from jinja2 import Template
from ssdpy import SSDPServer

log = get_logger('SsdpServer')


class ISsdpServer:

    def start(self, location: Optional[str]) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        raise NotImplementedError()

    def get_location(self) -> Optional[str]:
        raise NotImplementedError()


class SsdpServer(ISsdpServer):

    @staticmethod
    def create(ssdp_enabled: bool, ssdp_usn_pattern: str, ssdp_st_pattern: str, id_context: dict[str, str]) \
            -> Optional[ISsdpServer]:
        if ssdp_enabled:
            usn = Template(ssdp_usn_pattern).render(id_context)
            st = Template(ssdp_st_pattern).render(id_context)
            return SsdpServer(usn, st)
        else:
            return None

    def __init__(self, usn: str, st: str, timeout: int = 0, ) -> None:
        self._usn = usn
        self._st = st
        self._timeout = timeout
        self._server: Optional[SSDPServer] = None
        self._thread: Optional[Thread] = None
        self._location: Optional[str] = None

    def __enter__(self) -> 'SsdpServer':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()

    def start(self, location: Optional[str]) -> None:
        if location is None or location == '':
            log.warn('Invalid location, skipping server start', location=location)
            return
        else:
            self._location = location

        self.shutdown()
        self._server = SSDPServer(self._usn, location=location, device_type=self._st)
        if self._timeout > 0:
            self._server.sock.settimeout(self._timeout)
        self._thread = Thread(target=self._start_server)
        log.info('Starting SSDP server', usn=self._usn, service_type=self._st, location=location)
        self._thread.start()

    def shutdown(self) -> None:
        if self._server and self._thread:
            log.info('Shutting down')
            self._server.stopped = True
            self._server.sock.close()
            self._thread.join(1)

    def get_location(self) -> Optional[str]:
        return self._location

    def _start_server(self) -> None:
        try:
            if self._server:
                self._server.serve_forever()
        except Exception as error:
            log.info('Shutdown', reason=error)
