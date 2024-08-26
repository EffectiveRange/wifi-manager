
.PHONY: clean package

clean:
	rm -rf build dist *.egg-info

package:
	apt-get update
	apt-get install -y --no-install-recommends cmake git build-essential debhelper devscripts equivs dbus dh-python dh-virtualenv
	apt-get install -y --no-install-recommends python3-all libdbus-glib-1-dev libgirepository1.0-dev libcairo2-dev libsystemd-dev
	pip3 install stdeb wheel ninja patchelf meson
	python3 setup.py sdist
	python3 setup.py bdist_wheel
	python3 setup.py --command-packages=stdeb.command sdist_dsc -d dist --with-dh-virtualenv --with-dh-systemd --compat 10
	cp service/*.service dist/wifi-manager*/debian/
	cd dist/wifi-manager*/ && dpkg-buildpackage -us -ui -uc -tc -b
