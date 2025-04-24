import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import IReusableTimer
from context_logger import setup_logging

from wifi_connection import ConnectionMonitor, ConnectionMonitorConfig, ConnectionRestoreAction
from wifi_utility import IPlatformAccess


class ConnectionMonitorTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_should_start_timer(self):
        # Given
        platform, timer, config = create_dependencies()
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor.start()

        # Then
        timer.start.assert_called_once_with(60, connection_monitor._check_connection)

    def test_should_cancel_timer(self):
        # Given
        platform, timer, config = create_dependencies()
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor.stop()

        # Then
        timer.cancel.assert_called_once()

    def test_should_ping_default_gateway(self):
        # Given
        platform, timer, config = create_dependencies()
        platform.ping_default_gateway.return_value = True
        platform.ping_tunnel_endpoint.return_value = True
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor._check_connection()

        # Then
        platform.ping_default_gateway.assert_called_once_with(5)
        platform.ping_tunnel_endpoint.assert_called_once_with(5)
        timer.restart.assert_called_once()

    def test_should_reset_failure_counter_when_ping_is_successful(self):
        # Given
        platform, timer, config = create_dependencies()
        platform.ping_default_gateway.side_effect = [False, False, True]
        platform.ping_tunnel_endpoint.return_value = True
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor._check_connection()
        connection_monitor._check_connection()
        connection_monitor._check_connection()

        # Then
        platform.ping_default_gateway.assert_called_with(5)
        platform.ping_tunnel_endpoint.assert_called_once_with(5)
        self.assertEqual(0, connection_monitor._failures)
        timer.restart.assert_called()

    def test_should_run_connection_restore_actions_when_failed_to_ping_default_gateway(self):
        # Given
        platform, timer, config = create_dependencies()
        platform.ping_default_gateway.side_effect = [False, False, False]
        config.restore_actions = [MagicMock(spec=ConnectionRestoreAction), MagicMock(spec=ConnectionRestoreAction)]
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor._check_connection()
        connection_monitor._check_connection()
        connection_monitor._check_connection()

        # Then
        platform.ping_default_gateway.assert_called()
        self.assertEqual(0, connection_monitor._failures)
        config.restore_actions[0].run.assert_called_once()
        config.restore_actions[1].run.assert_called_once()
        timer.restart.assert_called()

    def test_should_run_connection_restore_actions_when_failed_to_ping_tunnel_endpoint(self):
        # Given
        platform, timer, config = create_dependencies()
        platform.ping_default_gateway.return_value = True
        platform.ping_tunnel_endpoint.side_effect = [False, False, False]
        config.restore_actions = [MagicMock(spec=ConnectionRestoreAction), MagicMock(spec=ConnectionRestoreAction)]
        connection_monitor = ConnectionMonitor(platform, timer, config)

        # When
        connection_monitor._check_connection()
        connection_monitor._check_connection()
        connection_monitor._check_connection()

        # Then
        platform.ping_default_gateway.assert_called()
        self.assertEqual(0, connection_monitor._failures)
        config.restore_actions[0].run.assert_called_once()
        config.restore_actions[1].run.assert_called_once()
        timer.restart.assert_called()


def create_dependencies():
    platform = MagicMock(spec=IPlatformAccess)
    timer = MagicMock(spec=IReusableTimer)
    config = ConnectionMonitorConfig(60, 5, 3, [])
    return platform, timer, config


if __name__ == '__main__':
    unittest.main()
