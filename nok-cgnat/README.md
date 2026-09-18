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

## Versions

| Piece | Version |
|-------|---------|
| Lab image | `nokia_srsim:25.10.R1` (same license as nok-bng) |
| NAT YANG / XPaths / log IDs | SR OS **26.7.R1** (recipe analysis + Log Events Guide ch. 48) |

## Operator docs

- [Telemetry XPaths](docs/telemetry-xpaths.md)
- [Log events and XPath correlation](docs/log-events.md)
- [SROS configuration](docs/sros-configuration.md)
