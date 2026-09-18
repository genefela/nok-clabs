#!/bin/sh
# Public IPv4 target: 198.51.100.10/24 with three iperf3 servers (one per LAN stream).
set -eu
ip link set eth1 up || true
ip addr add 198.51.100.10/24 dev eth1 || true
ip route replace default via 198.51.100.1 || true
ip route replace 203.0.113.0/24 via 198.51.100.1 || true

if command -v iperf3 >/dev/null 2>&1; then
  iperf3 -s -p 5201 >/tmp/iperf-5201.log 2>&1 &
  iperf3 -s -p 5202 >/tmp/iperf-5202.log 2>&1 &
  iperf3 -s -p 5203 >/tmp/iperf-5203.log 2>&1 &
  echo "inet ready at 198.51.100.10 (iperf3 5201/5202/5203)"
else
  echo "inet ready at 198.51.100.10 (iperf3 missing)"
fi
