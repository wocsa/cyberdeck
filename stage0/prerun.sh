#!/bin/bash -e

if [ "$RELEASE" != "trixie" ]; then
	echo "WARNING: RELEASE does not match the intended option for this branch."
	echo "         Please check the relevant README.md section."
fi

if [ ! -x "${ROOTFS_DIR}/bin/sh" ] || [ ! -d "${ROOTFS_DIR}/etc/apt" ] || [ -d "${ROOTFS_DIR}/debootstrap" ]; then
	# Only discard this stage's generated rootfs, after run_stage has unmounted it.
	if [ "${ROOTFS_DIR}" != "${STAGE_WORK_DIR}/rootfs" ] || [ -z "${STAGE_WORK_DIR}" ]; then
		echo "Refusing to remove an unexpected rootfs path: ${ROOTFS_DIR}" >&2
		exit 1
	fi
	rm -rf -- "${ROOTFS_DIR}"
	bootstrap ${RELEASE} "${ROOTFS_DIR}" http://raspbian.raspberrypi.com/raspbian/
fi
