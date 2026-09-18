#!/bin/sh
# DS-Lite B4 (CPE) for the CG-NAT digital twin.
# No iptables/NAT — LAN hosts keep 192.168.1.50; the AFTR does NAPT44.
# CPE_INDEX=1|2|3 selects the WAN IPv6 (static fallback if DHCPv6 is absent).
set -eu
CPE_INDEX="${CPE_INDEX:-1}"
AFTR="2001:db8:1::1"
case "$CPE_INDEX" in
  1) WAN6="2001:db8:1::11" ;;
  2) WAN6="2001:db8:1::12" ;;
  3) WAN6="2001:db8:1::13" ;;
  *) WAN6="2001:db8:1::11" ;;
esac

sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null
# Must not masquerade LAN traffic.
iptables -t nat -F 2>/dev/null || true
ip6tables -t nat -F 2>/dev/null || true

ip link set eth1 up || true
ip link set eth2 up || true
ip addr add 192.168.1.1/24 dev eth2 || true

# Production B4s learn the AFTR via DHCPv6 option 64; this lab tries dhclient then static.
if command -v dhclient >/dev/null 2>&1; then
  dhclient -6 -v eth1 >/tmp/dhclient6.log 2>&1 || true
fi
if ! ip -6 addr show dev eth1 | grep -q "inet6 2001:db8:1:"; then
  ip -6 addr add "${WAN6}/64" dev eth1 || true
fi
ip -6 route replace default via "$AFTR" dev eth1 || true

LOCAL6="$(ip -6 addr show dev eth1 | awk '/inet6 2001:db8:1:/ {print $2}' | cut -d/ -f1 | head -1)"
LOCAL6="${LOCAL6:-$WAN6}"

ip link del dslite0 2>/dev/null || true
ip link add name dslite0 type ip6tnl remote "$AFTR" local "$LOCAL6" mode ipip6 encaplimit none || \
  ip -6 tunnel add dslite0 mode ip4ip6 remote "$AFTR" local "$LOCAL6" || true
ip link set dslite0 up || true
ip addr add 192.0.0.2/29 dev dslite0 || true
ip route replace default dev dslite0 || true

echo "CPE${CPE_INDEX} B4 up local6=${LOCAL6} aftr=${AFTR} lan=192.168.1.1"
