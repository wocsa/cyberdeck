#!/bin/bash -e

if [ "$RELEASE" != "bullseye" ]; then
	echo "WARNING: RELEASE does not match the intended option for this branch."
	echo "         Please check the relevant README.md section."
fi

if [ "${USE_QCOW2}" != "1" ] && { [ ! -x "${ROOTFS_DIR}/bin/sh" ] || [ ! -d "${ROOTFS_DIR}/etc/apt" ]; }; then
	# A failed debootstrap leaves a partial directory behind.  Remove only that
	# generated stage output so the next build starts from a clean bootstrap.
	rm -rf "${ROOTFS_DIR}"
	bootstrap ${RELEASE} "${ROOTFS_DIR}" http://raspbian.raspberrypi.org/raspbian/
elif [ "${USE_QCOW2}" = "1" ]; then
	bootstrap ${RELEASE} "${ROOTFS_DIR}" http://raspbian.raspberrypi.org/raspbian/
fi
