#!/bin/sh
# Identical customer LAN on every home: 192.168.1.50/24 via B4 192.168.1.1.
# Bidirectional UDP iperf3 at 4 kbps / 100-byte payload = 5 pps.
set -eu
IPERF_PORT="${IPERF_PORT:-5201}"
INET="198.51.100.10"

ip link set eth1 up || true
ip addr add 192.168.1.50/24 dev eth1 || true
ip route replace default via 192.168.1.1 || true

if command -v iperf3 >/dev/null 2>&1; then
  i=0
  while [ "$i" -lt 30 ]; do
    if ping -c 1 -W 1 "$INET" >/dev/null 2>&1; then
      break
    fi
    i=$((i + 1))
    sleep 2
  done
  iperf3 -c "$INET" -u -p "$IPERF_PORT" -b 4k -l 100 -t 86400 --bidir \
    >/tmp/iperf-lan.log 2>&1 &
  echo "LAN host 192.168.1.50 iperf3 UDP 5pps to ${INET}:${IPERF_PORT}"
else
  echo "iperf3 not found; LAN host addressed at 192.168.1.50"
fi
