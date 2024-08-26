
[![Test and Release](https://github.com/EffectiveRange/wifi-manager/actions/workflows/test_and_release.yml/badge.svg)](https://github.com/EffectiveRange/wifi-manager/actions/workflows/test_and_release.yml)
[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/EffectiveRange/wifi-manager/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

# Wi-Fi Manager

Wi-Fi management: switching to AP mode if unable to connect to any configured network as a client

## Wi-Fi provisioning

In order to scale Wi-Fi provisioning for mass deployment of edge devices, a two-stage method is used:

1. Initial generic Wi-Fi network setup
2. Client specific Wi-Fi network setup

If the client specific Wi-Fi network needs to be changed, transitioning is to the new network is done similarly as it
was done from the initial network.

### 1. Initial generic Wi-Fi network setup

Edge devices has a default secured Wi-Fi connection configured with SSID and password. After physical deployment of the
edge devices, the Wi-Fi access point is providing an initial network with the same configuration. Once all edge devices
has successfully connected, the configuration for the client specific network is broadcast to them. Edge devices should
handle the new Wi-Fi network configuration with higher priority, than the initial one.

### 2. Client specific Wi-Fi network setup

After all edge devices acknowledge the new network configuration, the initial generic Wi-Fi network is brought down.
Edge devices at this point are configured to connect to the client specific Wi-Fi network with priority. The Wi-Fi
access point is started up with the same configuration and edge devices are connecting to the new Wi-Fi network. After
all edge devices have successfully connected, the Wi-Fi provisioning is completed.

## Fallback Wi-Fi setup

If for some reason any edge device lost the network connection for a configured amount of time, it will switch to Wi-Fi
hotspot mode. In this mode the edge device will host a web server providing a web interface to refresh the Wi-Fi
configuration and switch back to client mode. Optionally it can be switched back to client mode without changing the
Wi-Fi configuration.

## Building the application

### Prerequisites

The application is written in Python 3 and uses D-Bus (for inter-process communication) and GLib (for mainloop). To have
the necessary dependencies available the following Debian packages and Python packages needs to be installed:

#### Required Debian packages

* debhelper
* python3
* python3-pip
* python3-distutils
* dbus
* libdbus-1-dev
* libdbus-glib-1-dev
* libgirepository1.0-dev
* libcairo2-dev
* python3-gi

`sudo apt install debhelper python3 python3-pip python3-distutils dbus libdbus-1-dev libdbus-glib-1-dev libgirepository1.0-dev libcairo2-dev python3-gi`

#### Required Python packages

These packages are listed in `setup.py`:

* flask
* waitress
* netifaces
* dbus-python
* PyGObject
* gpiozero
* structlog

`sudo pip install flask waitress netifaces dbus-python PyGObject gpiozero structlog`

### Building as a Python package

Using PIP from the project root:

`sudo pip install .`

To use a Python virtual environment, first install `python3-venv` Debian package. Then create a virtual environment for
the project:

`sudo python -m venv /path/to/new/virtual/environment`

Use the virtual environment's `pip` (/path/to/new/virtual/environment/`bin/pip`) to install the application.

### Building as a Debian package

To build an installable Debian package first install the packages:

* dh-virtualenv
* devscripts

`sudo apt install dh-virtualenv devscripts`

Then run from the project root:

`sudo dpkg-buildpackage -us -uc -b`

It will output a similar file as `wifi-manager_0.0.1_all.deb` into the project root's parent directory. This Debian
package can be copied to the device and installed:

`sudo apt install ./wifi-manager_0.0.1_all.deb`

Then it can be run:

`sudo /opt/venvs/wifi-manager/bin/python3 /opt/venvs/wifi-manager/bin/wifi-manager.py`

It is also installed as a `systemd` service and is automatically started up

## Installation on the edge device

### Client mode

#### WPA supplicant

This is the default application for managing Wi-Fi networks as a client. Out of the box it will be available as a
binary and also as a systemd service.

`/sbin/wpa_supplicant`

`/lib/systemd/system/wpa_supplicant.service`

(It is also started separately by DHCP client daemon, so we will need to prevent that. See about it later.)

The service descriptor file's `ExecStart` should be appended by the interface `wlan0` and the configuration file path.

```bash
$ cat /lib/systemd/system/wpa_supplicant.service
[Unit]
Description=WPA supplicant
Before=network.target
After=dbus.service
Wants=network.target
IgnoreOnIsolate=true

[Service]
Type=dbus
BusName=fi.w1.wpa_supplicant1
ExecStart=/sbin/wpa_supplicant -u -s -O /run/wpa_supplicant -iwlan0 -c/etc/wpa_supplicant/wpa_supplicant.conf

[Install]
WantedBy=multi-user.target
Alias=dbus-fi.w1.wpa_supplicant1.service
```

Its configuration file stores the added networks as a persistent database.

`/etc/wpa_supplicant/wpa_supplicant.conf`

We can add our default network configuration here:

```bash
$ cat /etc/wpa_supplicant/wpa_supplicant.conf
ctrl_interface=/run/wpa_supplicant
update_config=1

network={
        ssid="EffectiveRange"
        psk="p4ssw0rd"
        disabled=0
}
```

#### DHCP client daemon

This daemon is provided by default and started up automatically.

`/lib/systemd/system/dhcpcd.service`

This also starts up a WPA supplicant instance that holds the control interface `/run/wpa_supplicant/wlan0` and prevents
`wpa_supplicant.service` to manage it.

```bash
$ sudo systemctl status dhcpcd.service | grep wlan0
             ├─564 wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iwlan0
```

To prevent this, the configuration file should be appended:

`/etc/dhcpcd.conf`

To remove the hook from `wpa_supplicant`

```bash
$ tail -2 /etc/dhcpcd.conf
interface wlan0
nohook wpa_supplicant
```

For the access point to be able to assign the device an IP address, any static IP configuration needs to be deleted:

```bash
sudo ifconfig wlan0 0.0.0.0
```

### Hotspot mode

#### HostAP daemon

This is the application we need to manage hotspot (access point) mode on our edge device. It is not available by
default, so we need to install it. It will be available as a systemd service.

```bash
$ sudo apt install hostapd
$ sudo systemctl unmask hostapd
$ sudo systemctl enable hostapd
```

`/lib/systemd/system/hostapd.service`

To configure the hotspot settings the configuration file should be edited:

`/etc/hostapd/hostapd.conf`

```bash
$ cat /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=edge-device-ap-1
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=p4ssw0rd
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

#### DNS masquerading daemon

This daemon can control the IP range and lease time for the connected peers. It is not available by defult, so
we will need to install it. It will be available as a systemd service.

```bash
$ sudo apt install dnsmasq
$ sudo systemctl unmask dnsmasq
$ sudo systemctl enable dnsmasq
```

Its configuration file can be edited to set up the IP range and the lease time (min 2 minutes).

`/etc/dnsmasq.conf`

```bash
$ cat /etc/dnsmasq.conf
interface=wlan0
dhcp-range=192.168.100.2,192.168.100.254,255.255.255.0,2m
enable-dbus
```

By adding `enable-dbus` dnsmasq will send events on adding/updating/deleting IP leases. These events can be used to
take into account the connected peers.

In order to act as a gateway for the connected peers, a static IP should be set for the device which is in the same
subnet. This can be done via the DHCP client daemon configuration or dynamically with `ifconfig`:

```bash
sudo ifconfig wlan0 192.168.100.1 netmask 255.255.255.0 broadcast 192.168.100.255
```

Also, there is a persisted list of leases:

`/var/lib/misc/dnsmasq.leases`

Containing the Epoch time of lease expiry, MAC, IP and device name

```bash
$ cat /var/lib/misc/dnsmasq.leases
1693133322 02:c0:e1:7c:35:34 192.168.100.118 Samsung-S20_1234 01:02:c0:e1:7c:35:34
```

DNS masquerading can also help in sharing the device's other connections with the connected peers. Providing
internet access for example. This is not a relevant use case currently for our application.
