# CG-NAT recipe (NAT444 and DS-Lite)

Containerlab + GitOps recipe for Nokia SR OS **carrier-grade NAT**, using **nok-bng as the template**.

The SR7 + ISA NAT444 lab is available in `topo-nat444-sr7.yaml`: two
overlapping customer LANs, CPE-side NAT44, provider NAT group 2, inside VPRN
700, and outside VPRN 500. The earlier SR-1e proof remains in
`topo-nat444.yaml`. See [NAT444 deployment and tests](docs/nat444.md).
Native IPv6, the redundant pair, and the complete multi-use-case design remain open.

Coverage:

| Area | Where |
|------|--------|
| Containerlab | `topo.yaml` — 11 logical nodes / 13 containers, including two IOM components |
| Telemetry XPaths (what / how) | `docs/telemetry-xpaths.md` and `nok-manifests/gnmic/subscriptions/` |
| Logs + XPath correlation | `docs/log-events.md` and Grafana **CG-NAT logs and XPath correlation** |
| SROS configuration | `configs/ne/` (MD-CLI: DS-Lite AFTR + SICR) |
| Selected NAT leaves | `docs/state-nat-leaves.txt` (recipe 28 metrics; MDA and ESA twins) |

gNMIc subscriptions are the 28-metric set (availability, saturation, traffic,
errors, DS-Lite softwire, ICR, log-event counters). Do not add per-subscriber
or extra `dropped/**` paths.

## Deploy

```bash
# Place your authorized SR-SIM 26.7 license at this ignored path (not committed):
# nok-clabs/nok-cgnat/srsim-lic-26.7.txt

make try-nok
make try-nok-cgnat
sudo make SRLINUX_IMAGE=registry.srlinux.dev/pub/nokia_srsim:26.7.R1 \
  SRSIM_LICENSE_FILE=nok-clabs/nok-cgnat/srsim-lic-26.7.txt deploy-clab-cgnat
```

Portal: `http://bng.nok.local:8080` → **NOK CG-NAT**.

After Containerlab deploy, run `make cgnat-post-deploy` (from `netopskube/`). That
script scales gNMIc down so zombie TCP sessions clear, waits for gRPC `:57400` on
the four SR-SIM NEs, scales gNMIc back up, and re-runs CPE/LAN startup scripts.
Grafana **CG-NAT ISA and ICR** should then show A1/A2/F1/E1 without manual
`show` commands on the routers.

### SR OS CLI (not `docker exec sr_cli`)

Nokia SR-SIM has no `sr_cli` in the container shell. SSH to the management IP
(password in `nok-manifests/secrets/device-credentials.yaml`, default `NokiaSros1!`):

```bash
ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o PubkeyAuthentication=no -o PreferredAuthentications=password \
  -o NumberOfPasswordPrompts=1 -o IdentitiesOnly=yes \
  admin@172.21.30.11   # CGNAT1; cgnat2 is .12
```

Prompt: `A:admin@CGNAT1#`. Same pattern as BNG (`admin@172.21.20.11`).

### NAT hardware profile

The NAT routers use SR-SIM 26.7 SR-1e CPM/IOM pairs with ISA2-BB in MDA `1/2`.
Each `cgnat*-iom` container shares its CPM's network namespace and owns the
access, outside, and ICL ports. No ESA stub is required: a Linux peer only brings
links up and does not supply ESA compute resources or a NAT datapath.

Syslog LB: KinD `.104` (`KIND_LB_CGNAT_SYSLOG_HOST`). SROS uses `172.18.0.104` —
`make update-kpt-lb-setters` patches the kpt setter if the Kind prefix is not `172.18.0`.

NAT events are **local5**; ISA flow records are **local6**.

## Topology (11 logical nodes / 13 containers)

- **cgnat1 / cgnat2** — SR-1e CPMs with slot-1 IOM components, ISA2-BB `nat-group 1`, **SICR**, and MCS `sync nat`
- **agg** — L2 VPLS bridging three B4s to both CG-NAT access ports
- **core** — IPv4 toward the internet host and the NAT pool
- **cpe1–3** — DS-Lite B4 (`configs/hosts/cpe.sh`), no masquerade, `ip4ip6` to `2001:db8:1::1`
- **lan1–3** — identical `192.168.1.50/24`, separate forward/reverse 5 pps UDP iperf3 streams to `198.51.100.10` ports 5201–5206
- **inet** — `198.51.100.10` with iperf3 servers on 5201–5206
- Mgmt: `172.21.30.0/24` (does not overlap BNG `172.21.20.0/24`)

Host scripts run as the linux node command. Re-run manually if needed:

```bash
docker exec -it clab-sros-cgnat-inet sh /startup.sh
docker exec -it clab-sros-cgnat-cpe1 sh /startup.sh
```

After Containerlab is up, `make deploy-clab-cgnat` (and `make try-nok-cgnat`) run
`scripts/cgnat-post-deploy.sh`: scale gNMIc to 0, wait for gRPC on all four NEs,
scale gNMIc back up, re-run CPE/LAN scripts. KinD must **not** get a direct
`172.21.30.0/24` interface (SR-SIM ignores mgmt SYNs from `172.21.30.2`); pods
reach the lab via host forwarding like BNG. Open Grafana — **CG-NAT ISA and ICR**
should show A1/A2/F1/E1 without router CLI.

## Versions

| Piece | Version |
|-------|---------|
| Lab image | `registry.srlinux.dev/pub/nokia_srsim:26.7.R1` |
| NAT YANG / XPaths / log IDs | SR OS **26.7.R1** (recipe analysis + Log Events Guide ch. 48) |

## Operator docs

- [Telemetry XPaths](docs/telemetry-xpaths.md)
- [Log events and XPath correlation](docs/log-events.md)
- [SROS configuration](docs/sros-configuration.md)
- [NAT444 IPv4 lab, tests, and dashboard](docs/nat444.md)

## Multi-use-case design groundwork

`configs/hosts/nat44-cpe.sh` is the first UC2/UC3 client component: it models a
dual-stack CPE with a private customer namespace, CPE-side NAT44, and optional
traffic generation. `eth1` is its WAN; the script creates an isolated customer
network namespace, so repeated `192.168.1.50/24` home addresses do not collide
between separate CPE containers.

| Setting | UC2 NAT444 example | UC3 deterministic example |
|---------|--------------------|---------------------------|
| `WAN4` | `100.64.1.10/24` | `100.65.0.10/22` |
| `WAN_GW4` | `100.64.1.1` | `100.65.0.1` |
| `WAN6` | `2001:db8:700:1::10/64` | `2001:db8:800:1::10/64` |
| `WAN_GW6` | `2001:db8:700:1::1` | `2001:db8:800:1::1` |
| `LAN6_CPE` / `LAN6_CLIENT` | Unique delegated `/64` per CPE in `2001:db8:700::/48` | Unique delegated `/64` per CPE in `2001:db8:800::/48` |
| `TCP_PORT` / `UDP_PORT` | `5203` / `5303` | `5205` / `5305` |

Set per-client values through Containerlab node `env`; for example, the second
NAT444 client uses WAN addresses `.11`, TCP port `5204`, and UDP port `5304`.
Set distinct `LAN6_CPE` and `LAN6_CLIENT` addresses for every client; the two
NAT444 clients must not share a delegated IPv6 `/64`. Use UC3 prefixes from
`2001:db8:800::/48`.
`START_TRAFFIC=no` configures the CPE without starting the traffic processes.
The client targets 2 ICMP requests/s and 9 UDP datagrams/s with 100-byte
payloads. TCP uses 100-byte writes, `TCP_NODELAY`, and a 7.2 kbps iperf3 target;
TCP segmentation and ACK behavior mean this is not an exact 9-wire-packets/s
guarantee.
For the design's Internet server, set `INET_IPV4=192.0.2.2/30`,
`INET_GW4=192.0.2.1`, and `NAT_RETURN_PREFIX=""`; the core routes return traffic
for the NAT pools. The default values in `inet.sh` continue to serve the current
DS-Lite lab.

The script is wired into the separate SR-SIM 26.7 NAT444 IPv4 topology;
the default `topo.yaml` remains DS-Lite. Forward and reverse traffic use
separate sessions; reverse TCP/UDP ports default to the forward port plus 1000.
The full redundant three-NAT-group topology and native IPv6 routing are not
yet implemented by this isolated NAT444 variant.
