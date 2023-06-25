#!/bin/bash
mount | grep cyberdeck |grep dev|sed 's/.* \([^ ]\+\) [^ ]\+ [^ ]\+ [^ ]\+$/umount -R \1/g'|bash
mount | grep cyberdeck |sed 's/.* \([^ ]\+\) [^ ]\+ [^ ]\+ [^ ]\+$/umount \1/g'|bash
mount |grep cyberdeck
echo "If NO MOUNT POINT DISPLAYED press enter to rm work and deploy folder OR press ctrl+c" 
read
rm -Rf ./deploy/* ./work/*