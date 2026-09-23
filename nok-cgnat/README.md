# CG-NAT recipe (DS-Lite + SICR)

Containerlab + GitOps recipe for Nokia SR OS **carrier-grade NAT**, using **nok-bng as the template**.

Coverage:

| Area | Where |
|------|--------|
| Containerlab | `topo.yaml` — 11-node DS-Lite digital twin |
| Telemetry XPaths (what / how) | `docs/telemetry-xpaths.md` and `nok-manifests/gnmic/subscriptions/` |
| Logs + XPath correlation | `docs/log-events.md` and Grafana **CG-NAT logs and XPath correlation** |
| SROS configuration | `configs/ne/` (MD-CLI: DS-Lite AFTR + SICR) |
| Selected NAT leaves | `docs/state-nat-leaves.txt` (recipe 28 metrics; MDA and ESA twins) |

gNMIc subscriptions are the 28-metric set (availability, saturation, traffic,
errors, DS-Lite softwire, ICR, log-event counters). Do not add per-subscriber
or extra `dropped/**` paths.

## Deploy

```bash
# License (same file as BNG; not committed)
cp nok-clabs/nok-bng/srsim-lic-25.txt nok-clabs/nok-cgnat/srsim-lic-25.txt

make try-nok
make try-nok-cgnat
sudo make deploy-clab-cgnat
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

### ESA host-ports

The topology includes an `esa-stub` linux node cabled to ESA host-ports on both
NAT routers. Without it, ESA stays `provisioned / health Unknown` and the NAT
group stays `transition`. If the lab was deployed before `esa-stub` was added,
re-run `sudo make deploy-clab-cgnat` (additive; does not touch BNG).

Syslog LB: KinD `.104` (`KIND_LB_CGNAT_SYSLOG_HOST`). SROS uses `172.18.0.104` —
`make update-kpt-lb-setters` patches the kpt setter if the Kind prefix is not `172.18.0`.

NAT events are **local5**; ISA flow records are **local6**.

## Topology (11 nodes)

- **cgnat1 / cgnat2** — SR-1s, ESA-VM BB, ISA `nat-group 1` with **SICR** and MCS `sync nat`
- **agg** — L2 VPLS bridging three B4s to both CG-NAT access ports
- **core** — IPv4 toward the internet host and the NAT pool
- **cpe1–3** — DS-Lite B4 (`configs/hosts/cpe.sh`), no masquerade, `ip4ip6` to `2001:db8:1::1`
- **lan1–3** — identical `192.168.1.50/24`, 5 pps UDP iperf3 to `198.51.100.10` ports 5201–5203
- **inet** — `198.51.100.10` with iperf3 servers on 5201–5203
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
| Lab image | `nokia_srsim:25.10.R1` (same license as nok-bng) |
| NAT YANG / XPaths / log IDs | SR OS **26.7.R1** (recipe analysis + Log Events Guide ch. 48) |

## Operator docs

- [Telemetry XPaths](docs/telemetry-xpaths.md)
- [Log events and XPath correlation](docs/log-events.md)
- [SROS configuration](docs/sros-configuration.md)
