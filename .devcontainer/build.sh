#!/bin/bash
set -e

WORKSPACE="/workspaces/wifi-manager"
BUILDROOT="/var/chroot/buildroot"

# Clean workspace
make clean

# Copy workspace into buildroot
rsync -av --exclude ".git" --exclude "*cache" --mkpath "$WORKSPACE/" "$BUILDROOT$WORKSPACE/"

# Build distribution packages
schroot -p -c buildroot -- make package

# Copy packages to workspace
rsync -av \
    --include "wifi-manager-*.tar.gz" \
    --include "wifi_manager-*.whl" \
    --include "wifi-manager_*.deb" \
    --exclude "*" --mkpath "$BUILDROOT$WORKSPACE/dist/" "$WORKSPACE/dist/"
