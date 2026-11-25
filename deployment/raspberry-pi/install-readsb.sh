#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash $0" >&2
  exit 1
fi

cat <<'NOTICE'
This will run the upstream readsb installer from wiedehopf/adsb-scripts.
The upstream installer may remove other ADS-B decoders because a single SDR
receiver cannot be owned by multiple decoder processes. Review the installer
and your current Pi services before continuing.

RTL-SDR Blog V4 users must additionally install the V4-compatible driver
version described in docs/ADS-B_RECEIVER_BUILD.md.
NOTICE

read -r -p "Continue with upstream readsb installation? [y/N] " answer
case "${answer,,}" in
  y|yes) ;;
  *) echo "Cancelled."; exit 0 ;;
esac

apt-get update
apt-get install -y wget ca-certificates
bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
echo
echo "readsb installation command completed. Review docs/ADS-B_RECEIVER_BUILD.md for V4 driver setup, antenna location, and PFD configuration."
