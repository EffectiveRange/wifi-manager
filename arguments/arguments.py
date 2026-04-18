from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, BooleanOptionalAction

APPLICATION_NAME = 'wifi-manager'
DEFAULT_CONFIG_FILE = f'/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf'
DEFAULT_LOG_FILE = f'/var/log/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.log'


def get_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description='Effective Range Wi-Fi Manager',
        formatter_class=ArgumentDefaultsHelpFormatter
    )

    app_group = parser.add_argument_group(APPLICATION_NAME)
    app_group.add_argument(
        '-c',
        '--config',
        help='configuration file path',
        default=DEFAULT_CONFIG_FILE
    )
    app_group.add_argument(
        '-f',
        '--log-file',
        help='log file path',
        default=DEFAULT_LOG_FILE
    )
    app_group.add_argument(
        '-l',
        '--log-level',
        help='logging level',
        default='info'
    )
    app_group.add_argument(
        '--server-port',
        dest='server_port',
        help='web server port to listen on',
        type=int,
        default=8080
    )

    device_group = parser.add_argument_group('device')
    device_group.add_argument('--device-role', help='device role', default='edge')
    device_group.add_argument(
        '--device-hostname',
        help='hostname pattern',
        default='er-{{device_role}}-{{cpu_serial}}'
    )

    wlan_group = parser.add_argument_group('wlan')
    wlan_group.add_argument(
        '--wlan-interface',
        help='preferred wlan interface',
        default='wlan0'
    )
    wlan_group.add_argument('--wlan-country', help='country code', default='HU')
    wlan_group.add_argument(
        '--wlan-disable-power-save',
        help='disable wlan power save mode',
        action='store_true',
        default=False
    )
    wlan_group.add_argument(
        '--wlan-disable-roaming',
        help='disable wifi roaming',
        action='store_true',
        default=False
    )

    control_group = parser.add_argument_group('control')
    control_group.add_argument(
        '--control-switch-fail-limit',
        help='mode switching failure limit',
        type=int,
        default=5
    )
    control_group.add_argument(
        '--control-switch-fail-command',
        help='command to execute when reaching failure limit',
        default='reboot'
    )

    client_group = parser.add_argument_group('client')
    client_group.add_argument(
        '--client-timeout',
        help='client timeout in seconds',
        type=int,
        default=30
    )
    client_group.add_argument(
        '--client-restart-delay',
        help='client restart delay in seconds',
        type=int,
        default=5
    )

    hotspot_group = parser.add_argument_group('hotspot')
    hotspot_group.add_argument(
        '--hotspot-password',
        help='hotspot Wi-Fi password',
        default='p4ssw0rd'
    )
    hotspot_group.add_argument(
        '--hotspot-peer-timeout',
        help='peer timeout in seconds',
        type=int,
        default=120
    )
    hotspot_group.add_argument(
        '--hotspot-static-ip',
        help='hotspot static IP address',
        default='192.168.100.1'
    )
    hotspot_group.add_argument(
        '--hotspot-dhcp-range',
        help='hotspot DHCP range',
        default='192.168.100.2,192.168.100.254,255.255.255.0,2m'
    )
    hotspot_group.add_argument(
        '--hotspot-startup-delay',
        help='hotspot startup delay in seconds',
        type=int,
        default=5
    )

    connection_group = parser.add_argument_group('connection')
    connection_group.add_argument(
        '--connection-ping-interval',
        help='connection ping interval in seconds',
        type=int,
        default=60
    )
    connection_group.add_argument(
        '--connection-ping-timeout',
        help='connection ping timeout in seconds',
        type=int,
        default=5
    )
    connection_group.add_argument(
        '--connection-ping-fail-limit',
        help='consecutive ping failures before fallback',
        type=int,
        default=5
    )
    connection_group.add_argument(
        '--connection-connect-actions',
        help='connection established actions, separated by newlines',
        default=''
    )
    connection_group.add_argument(
        '--connection-restore-actions',
        help='connection restore actions, separated by newlines',
        default='reset-wireless\nrestart-service openvpn@*.service'
    )

    identify_group = parser.add_argument_group('identify')
    identify_group.add_argument(
        '--identify-pin-gpio-number',
        help='GPIO pin number for identify signal',
        type=int,
        default=12
    )
    identify_group.add_argument(
        '--identify-pin-active-high',
        help='use active-high identify pin logic',
        action=BooleanOptionalAction,
        default=True
    )
    identify_group.add_argument(
        '--identify-pin-initial-value',
        help='initial identify pin state',
        action='store_true',
        default=False
    )
    identify_group.add_argument(
        '--identify-blink-frequency',
        help='identify tone frequency in Hz',
        type=float,
        default=440
    )
    identify_group.add_argument(
        '--identify-blink-interval',
        help='blink interval in seconds',
        type=float,
        default=0.5
    )
    identify_group.add_argument(
        '--identify-blink-pause',
        help='pause between blink groups in seconds',
        type=float,
        default=0.5
    )
    identify_group.add_argument(
        '--identify-blink-count',
        help='blink count per identify cycle',
        type=int,
        default=3
    )

    command_group = parser.add_argument_group('command')
    command_group.add_argument(
        '--command-definitions',
        help='command definitions, separated by newlines',
        default="Get current IP: ip addr show wlan0 | grep 'inet ' | awk '{print $2}'"
    )

    return parser
