import unittest
from unittest import TestCase, mock
from unittest.mock import MagicMock

from context_logger import setup_logging
from systemd_dbus import Systemd

from wifi_connection import ConnectionRestoreAction
from wifi_service import WifiClientService
from wifi_utility import IPlatformAccess


class ConnectionRestoreTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_reset_wireless_action(self):
        # Given
        client, systemd, platform = create_dependencies()
        action = ConnectionRestoreAction.create_actions(['reset-wireless'], client, systemd, platform)[0]

        # When
        action.run()

        # Then
        client.reset_wireless.assert_called_once()

    def test_restart_service_action(self):
        # Given
        client, systemd, platform = create_dependencies()
        systemd.list_service_names.return_value = ['test1.service', 'test2.service']
        action = ConnectionRestoreAction.create_actions(['restart-service test*.service'], client, systemd, platform)[0]

        # When
        action.run()

        # Then
        systemd.list_service_names.assert_called_once_with(patterns=['test*.service'])
        systemd.restart_service.assert_has_calls([
            mock.call('test1.service'),
            mock.call('test2.service')
        ])

    def test_execute_command_action(self):
        # Given
        client, systemd, platform = create_dependencies()
        action = ConnectionRestoreAction.create_actions(
            ['execute-command ifconfig wlan0 down && ifconfig wlan0 up'], client, systemd, platform)[0]

        # When
        action.run()

        # Then
        platform.execute_command.assert_called_once_with('ifconfig wlan0 down && ifconfig wlan0 up')


def create_dependencies():
    client = MagicMock(spec=WifiClientService)
    systemd = MagicMock(spec=Systemd)
    platform = MagicMock(spec=IPlatformAccess)
    return client, systemd, platform


if __name__ == '__main__':
    unittest.main()
