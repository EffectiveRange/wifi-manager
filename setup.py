from setuptools import setup

setup(
    name='wifi-manager',
    version='1.4.0',
    description='Wi-Fi manager application',
    long_description='Switching to AP mode if unable to connect to any configured network as a client',
    author='Ferenc Nandor Janky & Attila Gombos',
    author_email='info@effective-range.com',
    maintainer='Ferenc Nandor Janky & Attila Gombos',
    maintainer_email='info@effective-range.com',
    packages=['wifi_utility', 'wifi_event', 'wifi_dbus', 'wifi_config', 'wifi_service', 'wifi_manager'],
    scripts=['bin/wifi-manager.py'],
    data_files=[
        ('config', ['config/wifi-manager.conf', 'config/hostapd.conf.template', 'config/dnsmasq.conf.template']),
        ('templates', ['templates/configure.html', 'templates/identify.html']),
        ('static', ['static/style.css']),
    ],
    install_requires=[
        'flask',
        'waitress',
        'netifaces',
        'dbus-python',
        'PyGObject==3.50.0',
        'pygobject-stubs',
        'ssdpy',
        'jinja2',
        'cysystemd',
        'parameterized',
        'python-context-logger@git+https://github.com/EffectiveRange/python-context-logger.git@latest',
        'python-common-utility@git+https://github.com/EffectiveRange/python-common-utility.git@latest',
        'python-systemd-dbus@git+https://github.com/EffectiveRange/python-systemd-dbus.git@latest',
    ],
)
