import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from systemd_dbus import Systemd

from wifi_service import ServiceDependencies, SystemdResolvedService
from wifi_utility import IPlatform, IJournal


class SystemdResolvedServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_returns_true_when_systemd_resolved_is_installed(self):
        # Given
        dependencies = create_dependencies()
        dependencies.systemd.is_installed.return_value = True
        systemd_resolved_service = SystemdResolvedService(dependencies)

        # When
        result = systemd_resolved_service.is_installed()

        # Then
        self.assertTrue(result)

    def test_setup_disables_and_stops_systemd_resolved(self):
        # Given
        dependencies = create_dependencies()
        dependencies.systemd.is_enabled.return_value = True
        systemd_resolved_service = SystemdResolvedService(dependencies)

        # When
        systemd_resolved_service.setup()

        # Then
        dependencies.systemd.disable_service.assert_called_once_with('systemd-resolved')
        dependencies.systemd.stop_service.assert_called_once_with('systemd-resolved')


def create_dependencies():
    platform = MagicMock(spec=IPlatform)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    return dependencies


if __name__ == '__main__':
    unittest.main()
