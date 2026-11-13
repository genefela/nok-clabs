#!/bin/sh
# Public IPv4 target; INET_IPV4/INET_GW4 override the default DS-Lite lab addressing.
set -eu
INET_IPV4="${INET_IPV4:-198.51.100.10/24}"
INET_GW4="${INET_GW4:-198.51.100.1}"
NAT_RETURN_PREFIX="${NAT_RETURN_PREFIX-203.0.113.0/24}"

ip link set eth1 up || true
ip addr add "$INET_IPV4" dev eth1 || true
ip route replace default via "$INET_GW4" || true
if [ -n "$NAT_RETURN_PREFIX" ]; then
  ip route replace "$NAT_RETURN_PREFIX" via "$INET_GW4" || true
fi

if command -v iperf3 >/dev/null 2>&1; then
  iperf3 -s -p 5201 >/tmp/iperf-5201.log 2>&1 &
  iperf3 -s -p 5202 >/tmp/iperf-5202.log 2>&1 &
  iperf3 -s -p 5203 >/tmp/iperf-5203.log 2>&1 &
  for port in 5204 5205 5206; do
    iperf3 -s -p "$port" >"/tmp/iperf-${port}.log" 2>&1 &
  done
  for port in 5301 5302 5303 5304 5305 5306; do
    iperf3 -s -p "$port" >"/tmp/iperf-${port}.log" 2>&1 &
  done
  for port in 6201 6202 6203 6204 6205 6206 6301 6302 6303 6304 6305 6306; do
    iperf3 -s -p "$port" >"/tmp/iperf-${port}.log" 2>&1 &
  done
  echo "inet ready at ${INET_IPV4%/*} (iperf3 5201-5206/5301-5306, reverse 6201-6206/6301-6306)"
else
  echo "inet ready at ${INET_IPV4%/*} (iperf3 missing)"
fi
