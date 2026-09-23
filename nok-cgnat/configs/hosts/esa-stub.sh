#!/bin/sh
# Bring up containerlab data-plane veths cabled to ESA host-ports on cgnat1/2.
for i in 1 2 3 4; do
  ip link set "eth$i" up 2>/dev/null || true
done
