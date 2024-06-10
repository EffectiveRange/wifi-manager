
.PHONY: clean package

clean:
	rm -rf build dist wifi_manager.egg-info

package:
	apt-get update
	apt-get install -y --no-install-recommends cmake git build-essential debhelper devscripts equivs dbus dh-virtualenv
	apt-get install -y --no-install-recommends python3-pip python3-virtualenv libdbus-glib-1-dev libgirepository1.0-dev libcairo2-dev libsystemd-dev
	pip3 install wheel ninja patchelf meson
	python3 setup.py sdist
	python3 setup.py bdist_wheel
	dpkg-buildpackage -us -ui -uc -tc --buildinfo-option=-udist --buildinfo-option=-Odist/wifi-manager.buildinfo --changes-option=-udist --changes-option=-Odist/wifi-manager.changes
