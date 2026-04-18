from pathlib import Path

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

from arguments import get_argument_parser, APPLICATION_NAME

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_REL_PATH = Path('config') / f'{APPLICATION_NAME}.conf.default'
DEFAULT_CONFIG_PATH = ROOT_DIR / DEFAULT_CONFIG_REL_PATH


def generate_default_config() -> None:
    from common_utility import ConfigLoader

    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    argument_parser = get_argument_parser()
    config_loader = ConfigLoader(DEFAULT_CONFIG_PATH)

    with open(DEFAULT_CONFIG_PATH, 'w') as file:
        config_loader.dump(argument_parser, file)


class BuildPy(build_py):
    def run(self) -> None:
        super().run()
        generate_default_config()


class Develop(develop):
    def run(self) -> None:
        super().run()
        generate_default_config()


class EggInfo(egg_info):
    def run(self) -> None:
        super().run()
        generate_default_config()


commands = {
    'build_py': BuildPy,
    'develop': Develop,
    'egg_info': EggInfo,
}

extras_require = {
    'test': [
        'pytest>=7.0',
        'pytest-console-scripts',
        'pytest-coverage'
    ],
    'lint': [
        'flake8',
        'mypy',
    ],
}
extras_require['dev'] = extras_require['test'] + extras_require['lint']

setup(
    name=APPLICATION_NAME,
    description='Wi-Fi manager application',
    long_description='Switching to AP mode if unable to connect to any configured network as a client',
    author='Ferenc Nandor Janky & Attila Gombos',
    author_email='info@effective-range.com',
    maintainer='Ferenc Nandor Janky & Attila Gombos',
    maintainer_email='info@effective-range.com',
    packages=find_packages(exclude=['tests']),
    scripts=['bin/wifi-manager.py'],
    data_files=[
        (
            'config',
            [
                str(DEFAULT_CONFIG_REL_PATH),
                'config/hostapd.conf.template',
                'config/dnsmasq.conf.template',
            ],
        ),
        ('templates', ['templates/configuration.html', 'templates/operation.html', 'templates/execution.html']),
        ('static', ['static/style.css']),
    ],
    cmdclass=commands,
    extras_require=extras_require,
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
        'python-common-utility@git+https://github.com/EffectiveRange/python-common-utility.git@latest'
    ],
    install_requires=[
        'flask',
        'waitress',
        'netifaces',
        'ping3',
        'dbus-python',
        'PyGObject==3.50.0',
        'pygobject-stubs',
        'ssdpy',
        'jinja2',
        'cysystemd',
        'parameterized',
        'gpiozero',
        'python-common-utility@git+https://github.com/EffectiveRange/python-common-utility.git@latest',
        'python-systemd-dbus@git+https://github.com/EffectiveRange/python-systemd-dbus.git@latest',
    ]
)
