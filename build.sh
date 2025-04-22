WORKSPACE="/workspaces/wifi-manager"
BUILDROOT="/var/chroot/buildroot"

sudo rsync -av --exclude ".git" --exclude ".*cache" --mkpath "${WORKSPACE}/" "${BUILDROOT}${WORKSPACE}/"

sudo schroot -p -c buildroot -- apt update
sudo schroot -p -c buildroot -- apt install -y python3-stdeb packaging-tools
sudo schroot -p -c buildroot -- pack_python . -s dh-virtualenv

sudo rsync -av --include "*" --mkpath "${BUILDROOT}${WORKSPACE}/dist/" "${WORKSPACE}/dist/"
