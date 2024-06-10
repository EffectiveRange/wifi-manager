# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import logging

from context_logger import get_logger
from cysystemd.journal import Priority
from cysystemd.reader import JournalOpenMode, Rule, JournalReader, JournalEntry  # type: ignore

log = get_logger('ServiceJournal')


class ServiceEntry(object):
    LEVELS = {
        Priority.PANIC.value: logging.CRITICAL,
        Priority.ALERT.value: logging.CRITICAL,
        Priority.CRITICAL.value: logging.CRITICAL,
        Priority.ERROR.value: logging.ERROR,
        Priority.WARNING.value: logging.WARN,
        Priority.NOTICE.value: logging.INFO,
        Priority.INFO.value: logging.INFO,
        Priority.DEBUG.value: logging.DEBUG,
        Priority.NONE.value: logging.DEBUG
    }

    @classmethod
    def convert_from(cls, journal_entry: JournalEntry) -> 'ServiceEntry':
        timestamp = journal_entry.date.isoformat().replace('+00:00', 'Z')
        service = journal_entry.data['_COMM']
        message = journal_entry.data['MESSAGE']
        priority = int(journal_entry.data.get('PRIORITY', Priority.NONE.value))
        level = cls.LEVELS.get(priority, logging.DEBUG)
        return ServiceEntry(timestamp, service, message, level)

    def __init__(self, timestamp: str, service: str, message: str, level: int) -> None:
        self.timestamp = timestamp
        self.service = service
        self.message = message
        self.level = level


class IJournal(object):

    def get_last_entries(self, service: str, count: int) -> list[ServiceEntry]:
        raise NotImplementedError()

    def log_last_entries(self, service: str, count: int) -> list[ServiceEntry]:
        raise NotImplementedError()


class ServiceJournal(IJournal):

    def __init__(self, reader: JournalReader) -> None:
        self._reader = reader
        self._reader.open(JournalOpenMode.SYSTEM)

    def get_last_entries(self, service: str, count: int) -> list[ServiceEntry]:
        self._init_reader(service)
        self._reader.seek_tail()
        entries = []
        for i in range(count):
            entry = self._reader.previous()
            if entry is None:
                break
            entries.append(ServiceEntry.convert_from(entry))
        entries.reverse()
        return entries

    def log_last_entries(self, service: str, count: int) -> list[ServiceEntry]:
        entries = self.get_last_entries(service, count)
        for entry in entries:
            log.log(entry.level, entry.message, service=entry.service, original_timestamp=str(entry.timestamp))
        return entries

    def _init_reader(self, service: str) -> None:
        self._reader.clear_filter()
        self._reader.add_filter(Rule('_COMM', f'{service}'))
