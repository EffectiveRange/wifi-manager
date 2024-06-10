import datetime
import logging
import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from cysystemd.reader import JournalReader, JournalEntry

from wifi_utility import ServiceJournal, ServiceEntry


class ServiceJournalTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_returns_last_journal_entries(self):
        # Given
        reader = MagicMock(spec=JournalReader)
        reader.previous.side_effect = [
            create_entry(datetime.datetime(2024, 4, 22, 12, 34, 56, 790000), 'test-service', 'service stopped', 4),
            create_entry(datetime.datetime(2024, 4, 22, 12, 34, 56, 789000), 'test-service', 'service started'),
            None
        ]
        service_journal = ServiceJournal(reader)

        # When
        result = service_journal.log_last_entries('test-service', 5)

        # Then
        reader.clear_filter.assert_called_once()
        reader.add_filter.assert_called_once()
        reader.seek_tail.assert_called_once()
        self.assertEqual(2, len(result))
        self.assert_service_entry(
            ServiceEntry('2024-04-22T12:34:56.789000', 'test-service', 'service started', logging.INFO), result[0])
        self.assert_service_entry(
            ServiceEntry('2024-04-22T12:34:56.790000', 'test-service', 'service stopped', logging.WARN), result[1])

    def assert_service_entry(self, expected: ServiceEntry, actual: ServiceEntry):
        self.assertEqual(expected.timestamp, actual.timestamp)
        self.assertEqual(expected.service, actual.service)
        self.assertEqual(expected.message, actual.message)
        self.assertEqual(expected.level, actual.level)


def create_entry(timestamp: datetime.datetime, service: str, message: str, priority: int = 6):
    entry = MagicMock(spec=JournalEntry)
    entry.date = timestamp
    entry.data = {
        '_COMM': service,
        'MESSAGE': message,
        'PRIORITY': priority,
    }
    return entry


if __name__ == '__main__':
    unittest.main()
