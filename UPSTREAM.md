# pi-gen upstream

Source: https://github.com/RPi-Distro/pi-gen

Cyberdeck version: `v1.4`

Cyberdeck repository tags: `v1.4` and `pi-gen-2026-09-15-raspios-trixie-armhf`

Upstream tag: [`2026-09-15-raspios-trixie-armhf`](https://github.com/RPi-Distro/pi-gen/tree/2026-09-15-raspios-trixie-armhf)

Upstream commit: [`85b4d561a2708df84ae334c72c7d29be5256fea6`](https://github.com/RPi-Distro/pi-gen/commit/85b4d561a2708df84ae334c72c7d29be5256fea6)

Imported on 2026-09-16. The shared ancestor used to distinguish Cyberdeck
customizations was `01d24ef22778337ed04cf9d6444b1be57b6a1e1a`.
This pins the builder source; APT packages still come from the live Trixie mirrors.

The upstream README is kept in `pi-gen.md`; the project README remains Cyberdeck's.
The apt-cacher Docker Compose file and project automation are retained. Upstream's
GitLab CI file is not imported because this project uses GitHub Actions.

## Local differences to preserve on future updates

- Cyberdeck configuration, stage2 training tools/services, desktop skip markers,
  README, Ansible/Terraform files, and GitHub Actions.
- Bootstrap failure propagation and incomplete-rootfs recovery in `scripts/common`
  and stage prerun scripts.
- A separate Trixie work directory, Docker container name, and configurable
  `DOCKER_IMAGE`; support for hosts providing `qemu-arm-static`.
- NetworkManager Wi-Fi provisioning from `WPA_ESSID`/`WPA_PASSWORD`, a systemd
  firewall restore service, and explicit cloud-init disabling for preconfigured images.
- Explicit package providers, the configured user's SSH agent forwarding and
  groups, and passwordless sudo matching the previous image.
- Image finalization skips the systemd-timesyncd clock seed when OpenNTPD has
  replaced that package.
- Apache's `AllowOverride` remains in the directory section; it is invalid in
  a location section ([Apache directive documentation](https://httpd.apache.org/docs/2.4/mod/core.html#allowoverride)).

The obsolete upstream QCOW2 implementation (`imagetool.sh`, `scripts/qcow2_handling`,
and `USE_QCOW2`) was removed. Images now use the upstream raw-image export path;
`USE_QEMU` is a different upstream option. Removed tracked files remain recoverable
from Git history. Existing `work/` and `deploy/` artifacts have not been removed.

## Validation on 2026-09-16

Passed: 12 unprivileged bootstrap and offline NetworkManager regression tests,
Bash syntax checks for build/stage/export scripts, systemd unit verification,
and `git diff --check`. Imported archive keyrings and upstream documentation
were compared byte-for-byte with the pinned release.

Full build validation is pending. Docker failed while fetching
`i386/debian:trixie`: the host resolves `registry-1.docker.io` to `192.168.1.1`,
which refuses port 443. The Raspbian mirror was also unreachable. No Trixie image
was built or boot-tested. At validation time, Docker's filesystem had only
2.1 GB free (the project filesystem had 26 GB); check capacity before retrying.

Package-provider changes use Trixie's explicit
[netcat-openbsd](https://packages.debian.org/trixie/netcat-openbsd),
[fortune-mod](https://packages.debian.org/trixie/fortune-mod), and
[inetutils-telnetd](https://packages.debian.org/trixie/inetutils-telnetd).
Availability in the actual Raspbian mirror and complete dependency resolution
still require the image build.
