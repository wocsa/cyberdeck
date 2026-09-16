#!/bin/bash -e

if [ ! -x "${ROOTFS_DIR}/bin/sh" ]; then
	copy_previous
fi
