#!/bin/bash -e

install -m 0644 files/cyberdeck-firewall.service "${ROOTFS_DIR}/etc/systemd/system/"

# Cloud-init is installed by upstream even when its seed generation is disabled.
if [ "${ENABLE_CLOUD_INIT}" != "1" ]; then
	install -m 0644 /dev/null "${ROOTFS_DIR}/etc/cloud/cloud-init.disabled"
fi

if [ -n "${WPA_ESSID:-}" ]; then
	# nmcli's offline mode safely serializes SSIDs and passwords without a daemon.
	on_chroot <<'EOF'
install -d -m 0700 /etc/NetworkManager/system-connections
umask 077
wifi_args=(type wifi con-name cyberdeck-wifi ssid "$WPA_ESSID"
    connection.autoconnect yes ipv4.method auto ipv6.method auto)
if [ -n "${WPA_PASSWORD:-}" ]; then
    wifi_args+=(wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WPA_PASSWORD")
fi
nmcli --offline connection add "${wifi_args[@]}" > /etc/NetworkManager/system-connections/cyberdeck-wifi.nmconnection
EOF
fi
