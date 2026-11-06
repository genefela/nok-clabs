# SR-SIM 26.7 ESA VM Capability Probe

This isolated topology records the ESA VM attempt. It is **diagnostic only**;
its presence does not mean SR-SIM supplied ESA resources or measurements.
It is not the NAT444 lab and is not included in the default DS-Lite topology.

## Prerequisites

- Authorized Nokia SR-SIM 26.7 image:
  `registry.srlinux.dev/pub/nokia_srsim:26.7.R1`.
- Authorized SR-SIM 26.7 license copied locally as `srsim-lic-26.7.txt`.
  The repository ignore rule excludes license files. Never commit or print it.
- Docker and Containerlab.

## Run

From this directory, after confirming the image and local license are present:

```bash
clab deploy -t topo.yaml
```

Connect to SR OS at management IP `172.21.50.11` and inspect:

```text
show esa 1
show isa nat-group 2
show card state
```

Stop and remove only this probe with:

```bash
clab destroy --cleanup -t topo.yaml
```

## Observed Result (2026-11-04)

SR OS 26.7 loaded and committed the config after the SR-1s connector breakouts
were specified. Both ESA host-port links were up. Nevertheless:

- ESA 1 VM 1 remained `provisioned`.
- ESA hardware health was `Unknown`.
- ESA available/allocated core counts were zero.
- ESA available/allocated memory was zero.
- NAT group 2 remained `transition`, degraded, with its member inactive.

This means the SR-SIM image/configuration plus Linux host-port peers did not
provide usable ESA compute in this environment. A Linux peer supplies link
connectivity only; it is not an ESA VM runtime. This probe cannot satisfy ESA
NAT forwarding or ESA-based telemetry acceptance.

To proceed, obtain confirmation from the Nokia platform owner of the supported
SR OS 26.7 ESA runtime/appliance or an ESA-equipped device and authorized image
entitlement. Do not substitute VSR or label ISA/MDA counters as ESA measurements.
