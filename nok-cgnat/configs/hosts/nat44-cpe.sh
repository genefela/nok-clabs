#!/bin/sh
# Dual-stack NAT44 CPE for the multi-use-case CG-NAT recipe.
# eth1 is the RFC6598/native-IPv6 WAN; an isolated namespace models the home LAN.
set -eu

: "${WAN4:?set WAN4 with prefix length}"
: "${WAN_GW4:?set WAN_GW4}"
: "${WAN6:?set WAN6 with prefix length}"
: "${WAN_GW6:?set WAN_GW6}"
: "${LAN6_CPE:?set LAN6_CPE from this CPE's unique delegated prefix}"
: "${LAN6_CLIENT:?set LAN6_CLIENT from this CPE's unique delegated prefix}"
: "${TCP_PORT:?set TCP_PORT}"
: "${UDP_PORT:?set UDP_PORT}"

LAN_NS="${LAN_NS:-customer}"
LAN4_CPE="${LAN4_CPE:-192.168.1.1/24}"
LAN4_CLIENT="${LAN4_CLIENT:-192.168.1.50/24}"
LAN4_PREFIX="${LAN4_PREFIX:-192.168.1.0/24}"
SERVER4="${SERVER4:-192.0.2.2}"
START_TRAFFIC="${START_TRAFFIC:-yes}"
REVERSE_TCP_PORT="${REVERSE_TCP_PORT:-$((TCP_PORT + 1000))}"
REVERSE_UDP_PORT="${REVERSE_UDP_PORT:-$((UDP_PORT + 1000))}"

ip link set eth1 up
ip addr flush dev eth1
ip -6 addr flush dev eth1 scope global
ip addr add "$WAN4" dev eth1
ip -6 addr add "$WAN6" dev eth1
ip route replace default via "$WAN_GW4" dev eth1
ip -6 route replace default via "$WAN_GW6" dev eth1

sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null

ip netns del "$LAN_NS" 2>/dev/null || true
ip netns add "$LAN_NS"
ip link del cpe-lan 2>/dev/null || true
ip link add cpe-lan type veth peer name lan0
ip link set lan0 netns "$LAN_NS"
ip addr add "$LAN4_CPE" dev cpe-lan
ip -6 addr add "$LAN6_CPE" dev cpe-lan
ip -6 addr add fe80::1/64 dev cpe-lan
ip link set cpe-lan up

ip netns exec "$LAN_NS" ip link set lo up
ip netns exec "$LAN_NS" ip link set lan0 up
ip netns exec "$LAN_NS" ip addr add "$LAN4_CLIENT" dev lan0
ip netns exec "$LAN_NS" ip -6 addr add "$LAN6_CLIENT" dev lan0
ip netns exec "$LAN_NS" ip -6 addr add fe80::2/64 dev lan0
ip netns exec "$LAN_NS" ip route replace default via "${LAN4_CPE%/*}" dev lan0
ip netns exec "$LAN_NS" ip -6 route replace default via fe80::1 dev lan0

iptables -t nat -N CGNAT_CPE 2>/dev/null || true
iptables -t nat -F CGNAT_CPE
iptables -t nat -C POSTROUTING -j CGNAT_CPE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -j CGNAT_CPE
iptables -t nat -A CGNAT_CPE -s "$LAN4_PREFIX" -o eth1 -j MASQUERADE
iptables -C FORWARD -i cpe-lan -o eth1 -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i cpe-lan -o eth1 -j ACCEPT
iptables -C FORWARD -i eth1 -o cpe-lan -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i eth1 -o cpe-lan -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
ip6tables -C FORWARD -i cpe-lan -o eth1 -j ACCEPT 2>/dev/null || \
  ip6tables -A FORWARD -i cpe-lan -o eth1 -j ACCEPT
ip6tables -C FORWARD -i eth1 -o cpe-lan -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
  ip6tables -A FORWARD -i eth1 -o cpe-lan -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

echo "NAT44 CPE up: WAN=${WAN4} LAN=${LAN4_CLIENT} IPv6=${LAN6_CLIENT} namespace=${LAN_NS}"

if [ "$START_TRAFFIC" = yes ]; then
  ip netns exec "$LAN_NS" ping -4 -i 0.5 -s 100 "$SERVER4" >/tmp/nat44-ping.log 2>&1 &
  ip netns exec "$LAN_NS" iperf3 -c "$SERVER4" -p "$UDP_PORT" -u -b 7.2k -l 100 \
    -t 86400 --forceflush >/tmp/nat44-udp.log 2>&1 &
  ip netns exec "$LAN_NS" iperf3 -c "$SERVER4" -p "$REVERSE_UDP_PORT" -u -b 7.2k -l 100 \
    -R -t 86400 --forceflush >/tmp/nat44-udp-reverse.log 2>&1 &
  ip netns exec "$LAN_NS" iperf3 -c "$SERVER4" -p "$TCP_PORT" -b 7.2k -l 100 -N \
    -t 86400 --forceflush >/tmp/nat44-tcp.log 2>&1 &
  ip netns exec "$LAN_NS" iperf3 -c "$SERVER4" -p "$REVERSE_TCP_PORT" -b 7.2k -l 100 -N \
    -R -t 86400 --forceflush >/tmp/nat44-tcp-reverse.log 2>&1 &
fi
