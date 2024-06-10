import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from systemd_dbus import Systemd

from wifi_service import ServiceDependencies, NetworkManagerService
from wifi_utility import IPlatform, IJournal


class NetworkManagerServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_returns_true_when_network_manager_is_installed(self):
        # Given
        dependencies = create_dependencies()
        dependencies.systemd.is_installed.return_value = True
        network_manager_service = NetworkManagerService(dependencies)

        # When
        result = network_manager_service.is_installed()

        # Then
        self.assertTrue(result)

    def test_setup_disables_and_stops_network_manager(self):
        # Given
        dependencies = create_dependencies()
        dependencies.systemd.is_enabled.return_value = True
        network_manager_service = NetworkManagerService(dependencies)

        # When
        network_manager_service.setup()

        # Then
        dependencies.systemd.disable_service.assert_called_once_with('NetworkManager')
        dependencies.systemd.stop_service.assert_called_once_with('NetworkManager')

    def test_setup_masks_network_manager(self):
        # Given
        dependencies = create_dependencies()
        dependencies.systemd.is_masked.return_value = False
        network_manager_service = NetworkManagerService(dependencies)

        # When
        network_manager_service.setup()

        # Then
        dependencies.systemd.mask_service.assert_called_once_with('NetworkManager')
        dependencies.systemd.reload_daemon.assert_called_once()

    def test_logged_journal_on_service_failed_event(self):
        # Given
        dependencies = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies)

        # When
        network_manager_service._on_service_state_changed('failed')

        # Then
        dependencies.journal.log_last_entries('NetworkManager', 5)
        dependencies.systemd.restart_service.assert_not_called()

    def test_force_stopped_on_service_active_event(self):
        # Given
        dependencies = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies)

        # When
        network_manager_service._on_service_state_changed('active')

        # Then
        dependencies.systemd.stop_service.assert_called_once_with('NetworkManager')


def create_dependencies():
    platform = MagicMock(spec=IPlatform)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    return dependencies


if __name__ == '__main__':
    unittest.main()
