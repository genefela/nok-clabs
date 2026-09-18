# CG-NAT telemetry XPaths (SR OS 26.7.R1)

Operator catalog for **what** this recipe streams and **how**. Paths are the
28-metric / selected-leaf set from the CG-NAT recipe analysis. Every leaf is
present in the 26.7.R1 `/state` catalogue (2,535 candidate NAT-family paths).
This recipe does **not** invent extra XPaths and does **not** subscribe
per-subscriber, per-port-block, or the full `dropped/**` tree.

Lab image remains `nokia_srsim:25.10.R1`. 26.7 leaves that 25.10 does not
implement stay empty.

Cadence: **60 s SAMPLE** unless noted. Availability and watermark booleans use
**ON_CHANGE plus a 240 s SAMPLE refresh** so Prometheus always has a recent
point.

Notation:

| Symbol | Expands to |
|--------|------------|
| `NG` | `/state/isa/nat-group[id=*]` |
| `DP` | `NG/mda[mda-id=*]` **or** `NG/esa[esa-id=*][vm=*]` (this lab uses ESA; both are subscribed) |
| `RI` | `/state/router[router-name=*]` **or** `/state/service/vprn[service-name=*]` (this lab NATs in Base; both are subscribed) |

gNMIc CRs: `nok-manifests/gnmic/subscriptions/`. Pipelines select `role: cgnat`.
Prometheus series names follow gNMIc's path-to-metric mapping (for example
`state_isa_nat_group_degraded`). Design names in the tables are the operator
aliases.

The full selected leaf list is `docs/state-nat-leaves.txt`.

## A. Availability (on-change + 4 min)

| # | Alias | Path(s) |
|---|-------|---------|
| A1 | `nat_group_oper_state` | `NG/oper-state` |
| A2 | `nat_group_degraded` | `NG/degraded` |
| A3 | `nat_member_state` | `NG/member[id=*]/state` |
| A4 | `nat_member_role` | `NG/mda[mda-id=*]/oper-state`, `NG/esa[esa-id=*][vm=*]/oper-state` |
| A5 | `nat_member_hw_oper_state` | `/state/esa[esa-id=*]/vm[vm-id=*]/oper-state`, `/state/card[slot-number=*]/mda[mda-slot=*]/hardware-data/oper-state` |

## B. Saturation (60 s; B2 and B9 watermark on-change + 4 min)

| # | Alias | Path(s) |
|---|-------|---------|
| B1 | `nat_member_session_usage_ratio` | `NG/member[id=*]/session-usage` |
| B2 | `nat_member_session_usage_high` | `NG/member[id=*]/high-session-usage` |
| B3 | `nat_member_allocated_resources_ratio` | `NG/member[id=*]/allocated-resources` |
| B4 | `nat_flows{value,max}` | `DP/resources/flows/{value,max}` |
| B5 | `nat_outside_ports{value,max}` | `NG/member[id=*]/resources/ports/{value,max}` |
| B6 | `nat_port_blocks{value,max}` | `NG/member[id=*]/resources/port-ranges/used/{value,max}` |
| B7 | `nat_lsn_hosts{value,max}` | `NG/member[id=*]/resources/large-scale-hosts/{value,max}` |
| B8 | `nat_outside_ip_addresses{value,max}` | `NG/member[id=*]/resources/ip-addresses/{value,max}` |
| B9 | `nat_pool_block_usage_ratio`, `nat_pool_high_watermark_reached` | `RI/nat/outside/pool[name=*]/large-scale/group-member[group-member=*]/block-usage`, `…/high-watermark-reached` |

Always export `max` with `value`. Prefer the node's own watermark booleans
(B2, B9) over a second collector-side threshold. This lab sets high 90 / low 80
on the NAT group and the pool.

## C. Traffic (60 s)

| # | Alias | Path |
|---|-------|------|
| C1 | `nat_flow_created_total` | `DP/statistics/nat/flow/new-flow` |
| C2 | `nat_flow_matched_total` | `DP/statistics/nat/flow/found-flow` |
| C3 | `nat_dslite_forwarded_total` | `DP/statistics/nat/dslite/forward` |

## D. Errors (60 s)

| # | Alias | Path |
|---|-------|------|
| D1 | `nat_flow_create_failed_total{reason}` | `DP/statistics/nat/dropped/flow-creation-failed/{no-resources,no-ip-or-port-resources,no-host-resources,max-flows-exceeded,flow-log-failed,port-range-log-failed,dslite-unknown-aftr,unmatched-policy,transient-no-policy}` |
| D2 | `nat_flow_closed_total` | `DP/statistics/nat/flow/tcp-closed` |
| D3 | `nat_flow_log_rate_limit_drop_total` | `DP/statistics/nat/flow-log/rate-limit-drop` |
| D4 | `nat_flow_log_records_total{action}` | `DP/statistics/nat/flow-log/{logged-flow-create,logged-flow-delete,tx-packet}` |
| D5 | `nat_receive_errors_total{reason}` | `DP/statistics/nat/dropped/receive-errors/{ip-invalid-checksum,tcp-udp-invalid-checksum,dslite-unsupported-next-header,ipv6-fragments-unsupported,ip-malformed-packet}` |

D1 is a **curated subset** of 9 reasons (not the 27-reason subtree). Capacity
reasons are the SLI numerator; `flow-log-failed` is compliance; DS-Lite AFTR /
policy misses are configuration.

## E. Softwire integrity (60 s)

| # | Alias | Path |
|---|-------|------|
| E1 | `nat_fragment_dropped_total{reason}` | `DP/statistics/nat/dropped/fragments/{reassembly-failed,too-many-fragment-buffers,fragment-list-expired,too-many-fragments-per-packet}` |
| E2 | `nat_mtu_exceeded_total` | `DP/statistics/nat/dropped/general/mtu-exceeded` |
| E3 | `nat_fragment_buffers{direction,value,max}` | `DP/resources/fragment-bufs/{upstream,downstream}/{value,max}` |

## F. Redundancy

| # | Alias | Path |
|---|-------|------|
| F1 | `nat_icr_{state,in_control,health,peer_health,state_changes_total,keepalive_timeouts_total}` | `NG/redundancy/inter-chassis/{state,in-control,health,peer-health,state-changes,statistics/keepalive-timeouts}` |
| F2 | `nat_icr_tracked_flows{state}`, `nat_icr_member_state` | `NG/member[id=*]/inter-chassis-redundancy/{tracked-flows,tracked-flows-not-synced,state}` |

`tracked-flows-not-synced / tracked-flows` is how stateful the pair is right now.

## G. Log-event counters (60 s)

| # | Alias | Path |
|---|-------|------|
| G1 | `nat_log_event_total{event}`, `nat_log_event_dropped_total{event}` | `/state/log/log-events/nat[event=*]/statistics/{count,drop}` |

Use with syslog in Loki (`docs/log-events.md`). G1 `drop` is router throttling.

## Intentionally not streamed

- Per-subscriber `/nat/inside/large-scale/dual-stack-lite/subscriber[*]`
- Per-port-block `/nat/outside/large-scale/block[*]`
- L2-aware subscriber trees
- NAT-policy MDA statistics (not in the 28)
- Whole `dropped/**` (93 counters); D1/D5/E1 are the kept reasons
- MAP-E/T, LNS, WLAN-GW NAT, PFCP

Core/agg still scrape `/state/system/cpu` and `/state/system/memory-pools`
(nok-bng/nok-dia environment metrics). Additional routing metrics are deferred.

## Enum maps (26.7 YANG)

Applied in `nok-manifests/gnmic/operators/gnmic-oper-state-to-int.yaml`.
`active` / `standby` / `disabled` are **not** globally mapped (the same token
means different integers on member vs ICR state). Unique tokens are mapped;
booleans export as 0/1.

| Leaf | Mapping |
|------|---------|
| `nat-group/oper-state` | unknown 1, up 2, down 3, transition 4 |
| `nat-group/{mda,esa}/oper-state` | unavail 0, primary 1, backup 2, busy 3 |
| `nat-group/member/state` | inactive 1, active 2, needs-reset 3, resetting 4, … active-bypass 10 |
| ICR `inter-chassis/state` | disabled 0, initial-wait-for-peer 2, wait-for-peer 3, peer-timed-out 4, active 5, standby 6, cleaning-up 7 |
| member ICR `state` | disabled 0, waiting-selection 1, cleaning-up 2, negotiating 3, active 4, standby 5 |
