import platform

from setuptools import setup


def get_platform_name() -> str:
    return platform.system().lower() + '-' + platform.machine().lower()


setup(
    name='wifi-manager',
    version='1.0.4',
    options={
        'bdist_wheel': {
            'plat_name': get_platform_name(),
        },
    },
    description='Wi-Fi management: switching to AP mode if unable to connect to any configured network as a client',
    author='Ferenc Nandor Janky & Attila Gombos',
    author_email='info@effective-range.com',
    packages=['wifi_utility', 'wifi_event', 'wifi_wpa', 'wifi_service', 'wifi_manager'],
    scripts=['bin/wifi-manager.py'],
    data_files=[
        ('config', ['config/wifi-manager.conf', 'config/hostapd.conf.template', 'config/dnsmasq.conf.template']),
        ('templates', ['templates/configure.html', 'templates/identify.html']),
        ('static', ['static/style.css'])],
    install_requires=['flask', 'waitress', 'netifaces', 'dbus-python', 'PyGObject', 'ssdpy', 'jinja2', 'cysystemd',
                      'parameterized',
                      'python-context-logger@git+https://github.com/EffectiveRange/python-context-logger.git@latest',
                      'python-systemd-dbus@git+https://github.com/EffectiveRange/python-systemd-dbus.git@latest']
)
