# CG-NAT log events and XPath correlation

Application **NAT** on the `main` stream. Event IDs are from SR OS 26.7.R1
Log Events Guide chapter **48 NAT** (41 events, IDs 2001–2048 with gaps).
Key the parser on the **event number**, not the name.

This lab splits syslog by facility (same collector `172.18.0.104:1514`):

| Facility | Content | Loki |
|----------|---------|------|
| **local5** | CPM NAT events (`log-id 50`, filter `application eq nat`) | `{job="syslog", facility=~"local5\|21"}` |
| **local6** | ISA/ESA per-flow records (`service nat syslog export-policy`) | `{job="syslog", facility=~"local6\|22"}` |
| local7 | core/agg device logs only | `{facility=~"local7\|23"}` |

Promtail already labels `application`, `event_id`, `facility`, `severity`,
`source`. Grafana **CG-NAT logs and XPath correlation** joins those with gNMI.

Severity is a poor default filter: all 41 events are minor or warning until
this lab raises **2025** to critical and **2037** / **2003** to major.

Do **not** alert on events that duplicate a metric. Alert on the metric.
Log-only events are the exception (no metric covers them).

## Loki examples

```logql
{job="syslog", application="NAT"}
{job="syslog", facility=~"local5|21"}
{job="syslog", facility=~"local6|22"}
{job="syslog", application="NAT", event_id="2015"}
{job="syslog", application="NAT", event_id=~"2023|2040|2043"}
```

## Event classes (41)

**Skip on this DS-Lite AFTR (L2-aware, cannot occur):** 2001, 2007, 2008, 2009,
2010, 2013, 2044.

**Duplicate a metric (keep in Loki for the pool/member name; do not page):**

| Event ID | Name | Metric |
|----------|------|--------|
| 2024 | `tmnxNatIsaGrpOperStateChanged` | A1 `NG/oper-state` |
| 2025 | `tmnxNatIsaGrpIsDegraded` | A2 `NG/degraded` |
| 2020 | `tmnxNatMdaActive` | A4 MDA `oper-state` |
| 2039 | `tmnxNatVappActive` | A4 ESA-VM `oper-state` |
| 2002 | `tmnxNatIsaMemberSessionUsageHigh` | B1/B2 `session-usage` / `high-session-usage` |
| 2003 | `tmnxNatPlLsnMemberBlockUsageHigh` | B9 pool `block-usage` / `high-watermark-reached` |
| 2046 | `tmnxNatPlLsnMemberPortUsageHigh` | B5–B7 (flexible-port; not this lab's port-block pool) |
| 2045 | `tmnxNatPlMemberExtBlockUsageHigh` | extended blocks |
| 2014 | `tmnxNatResourceProblemDetected` | A2 / B3 |
| 2017 | `tmnxNatPlLsnRedActiveChanged` | F1 (stateless pool redundancy; disabled under SICR) |
| 2037 | `tmnxNatMaxNbrSubsOrHostsExceeded` | B7/B8 host/IP scale |
| 2038 | `tmnxNatNbrSubsOrHostsBelowThrsh` | B7/B8 clear |

**Log-only (alert from Loki or G1; no metric in the 28):** 2015 (resource cause),
2022 / 2041 / 2042 / 2047 (deterministic map), 2036 (MAP rule), 2023 / 2040
(ingress load-sharing — 2023 is the clearest: ingress card cannot hash NAT,
traffic dropped), 2043 (SICR config mismatch), 2031 / 2034 (port forwarding),
2018 (PCP), 2035 / 2048 (outside route limits).

**Once per subscriber (throttle in `log-events`; do not use as a Loki label):**
2026–2029 (LSN ICMP/UDP/TCP/session). This lab sets `throttle true` on those four.

**Binding records (leave suppressed; flow-log on local6 already records them):**
2012, 2013, 2016, 2021, 2030.

ICR activity is telemetry-first (F1/F2). 2024/2025 fire when the group itself
changes.

## Completeness

- G1 `…/log-events/nat[event=*]/statistics/drop` — router throttle discards.
- Sequence numbers on local6 flow records — a gap means a syslog UDP packet was lost.

## Complete NAT event ID list (26.7 ch. 48)

| Event ID | Event name |
|----------|------------|
| 2001 | `tmnxNatPlL2AwBlockUsageHigh` |
| 2002 | `tmnxNatIsaMemberSessionUsageHigh` |
| 2003 | `tmnxNatPlLsnMemberBlockUsageHigh` |
| 2007 | `tmnxNatL2AwSubIcmpPortUsageHigh` |
| 2008 | `tmnxNatL2AwSubUdpPortUsageHigh` |
| 2009 | `tmnxNatL2AwSubTcpPortUsageHigh` |
| 2010 | `tmnxNatL2AwSubSessionUsageHigh` |
| 2012 | `tmnxNatPlBlockAllocationLsn` |
| 2013 | `tmnxNatPlBlockAllocationL2Aw` |
| 2014 | `tmnxNatResourceProblemDetected` |
| 2015 | `tmnxNatResourceProblemCause` |
| 2016 | `tmnxNatPlAddrFree` |
| 2017 | `tmnxNatPlLsnRedActiveChanged` |
| 2018 | `tmnxNatPcpSrvStateChanged` |
| 2020 | `tmnxNatMdaActive` |
| 2021 | `tmnxNatLsnSubBlksFree` |
| 2022 | `tmnxNatDetPlcyChanged` |
| 2023 | `tmnxNatMdaDetectsLoadSharingErr` |
| 2024 | `tmnxNatIsaGrpOperStateChanged` |
| 2025 | `tmnxNatIsaGrpIsDegraded` |
| 2026 | `tmnxNatLsnSubIcmpPortUsgHigh` |
| 2027 | `tmnxNatLsnSubUdpPortUsgHigh` |
| 2028 | `tmnxNatLsnSubTcpPortUsgHigh` |
| 2029 | `tmnxNatLsnSubSessionUsgHigh` |
| 2030 | `tmnxNatInAddrPrefixBlksFree` |
| 2031 | `tmnxNatFwd2EntryAdded` |
| 2034 | `tmnxNatFwd2OperStateChanged` |
| 2035 | `tmnxNatVrtrOutDnatOnlyRoutesHigh` |
| 2036 | `tmnxNatMapRuleChange` |
| 2037 | `tmnxNatMaxNbrSubsOrHostsExceeded` |
| 2038 | `tmnxNatNbrSubsOrHostsBelowThrsh` |
| 2039 | `tmnxNatVappActive` |
| 2040 | `tmnxNatVappDetectsLoadSharingErr` |
| 2041 | `tmnxNatDetPfxMapOperStateChanged` |
| 2042 | `tmnxNatDetMap2OperStateChanged` |
| 2043 | `tmnxNatDynamicConfigMismatch` |
| 2044 | `tmnxNatPlL2AwMembrBlockUsageHigh` |
| 2045 | `tmnxNatPlMemberExtBlockUsageHigh` |
| 2046 | `tmnxNatPlLsnMemberPortUsageHigh` |
| 2047 | `tmnxNatDetAddrMapOperStateChngd` |
| 2048 | `tmnxNatVrtrOutRoutesHigh` |
