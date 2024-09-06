import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import copy_file
from context_logger import setup_logging
from systemd_dbus import Systemd
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_service import AvahiService, ServiceDependencies, ServiceError
from wifi_utility import IPlatform, IJournal


class AvahiServiceTest(TestCase):
    HOSTS_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/hosts'
    HOSTNAME_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/hostname'
    EXPECTED_HOSTS_FILE = f'{TEST_RESOURCE_ROOT}/expected/hosts'
    EXPECTED_HOSTNAME_FILE = f'{TEST_RESOURCE_ROOT}/expected/hostname'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        copy_file(f'{TEST_RESOURCE_ROOT}/config/hosts', self.HOSTS_FILE)
        copy_file(f'{TEST_RESOURCE_ROOT}/config/hostname', self.HOSTNAME_FILE)

    def test_setup_updates_hosts_and_hostname_file_and_restarts_avahi_daemon(self):
        # Given
        dependencies = create_dependencies()
        dependencies.platform.get_hostname.side_effect = ['test-hostname', 'test-hostname', 'new-hostname']
        avahi_service = AvahiService(dependencies, 'new-hostname', self.HOSTS_FILE, self.HOSTNAME_FILE)

        # When
        avahi_service._config_reloaded.set()
        avahi_service.setup()

        # Then
        self.assertTrue(compare_files(self.EXPECTED_HOSTS_FILE, self.HOSTS_FILE))
        self.assertTrue(compare_files(self.EXPECTED_HOSTNAME_FILE, self.HOSTNAME_FILE))
        dependencies.systemd.restart_service.assert_called_once_with('avahi-daemon')

    def test_setup_raises_service_error_when_fails_to_update_hostname(self):
        # Given
        dependencies = create_dependencies()
        dependencies.platform.get_hostname.return_value = 'test-hostname'
        avahi_service = AvahiService(dependencies, 'new-hostname', self.HOSTS_FILE, self.HOSTNAME_FILE)

        # When
        self.assertRaises(ServiceError, avahi_service.setup)

        # Then
        dependencies.systemd.restart_service.assert_not_called()

    def test_setup_raises_service_error_when_fails_to_update_hosts_and_hostname_file(self):
        # Given
        dependencies = create_dependencies()
        dependencies.platform.get_hostname.side_effect = Exception('Failed to get hostname')
        avahi_service = AvahiService(dependencies, 'new-hostname', self.HOSTS_FILE, self.HOSTNAME_FILE)

        # When
        self.assertRaises(ServiceError, avahi_service.setup)

        # Then
        dependencies.systemd.restart_service.assert_not_called()


def create_dependencies():
    platform = MagicMock(spec=IPlatform)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    return ServiceDependencies(platform, systemd, journal)


if __name__ == '__main__':
    unittest.main()
