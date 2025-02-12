import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from systemd_dbus import Systemd

from wifi_event import WifiEventType
from wifi_service import ServiceDependencies, ServiceError, Service
from wifi_utility import IPlatformAccess, IJournal


class HostapdServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_logged_journal_and_restarted_service_on_service_failed_event(self):
        # Given
        dependencies = create_dependencies()
        service = Service('test-service', '/test/service/path', dependencies)

        # When
        service._on_service_state_changed('failed')

        # Then
        dependencies.journal.log_last_entries('test-service', 5)
        dependencies.systemd.restart_service.assert_called_once_with('test-service')

    def test_service_restored_when_failed_and_state_changed_to_active(self):
        # Given
        dependencies = create_dependencies()
        service = Service('test-service', '/test/service/path', dependencies)

        # When
        service._on_service_state_changed('failed')
        service._on_service_state_changed('active')

        # Then
        self.assertFalse(service._failed)

    def test_raises_service_error_when_registering_callback_for_not_supported_event(self):
        # Given
        dependencies = create_dependencies()
        service = Service('test-service', '/test/service/path', dependencies)

        # When, Then
        self.assertRaises(ServiceError, service.register_callback, WifiEventType.HOTSPOT_STARTED, None)


def create_dependencies():
    platform = MagicMock(spec=IPlatformAccess)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    return dependencies


if __name__ == '__main__':
    unittest.main()
