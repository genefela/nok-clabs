import json
import os
import re
import subprocess
import unittest
from pathlib import Path

import yaml


RECIPE = Path(__file__).resolve().parents[1]


class CgnatRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.topology = yaml.safe_load((RECIPE / "topo.yaml").read_text())
        cls.nodes = cls.topology["topology"]["nodes"]
        cls.links = cls.topology["topology"]["links"]

    def test_srsim_version_and_isa_iom_profile(self):
        srsim_nodes = [node for node in self.nodes.values() if node.get("kind") == "nokia_srsim"]
        self.assertTrue(srsim_nodes)
        self.assertTrue(all(node["image"].endswith(":26.7.R1") for node in srsim_nodes))
        self.assertNotIn("esa-stub", self.nodes)

        for router in ("cgnat1", "cgnat2"):
            cpm = self.nodes[router]
            iom = self.nodes[f"{router}-iom"]
            self.assertEqual(cpm["env"]["NOKIA_SROS_CHASSIS"], "sr-1e")
            self.assertEqual(iom["network-mode"], f"container:{router}")
            self.assertEqual(iom["env"]["NOKIA_SROS_CARD"], "iom-e")
            self.assertEqual(iom["env"]["NOKIA_SROS_MDA_2"], "isa2-bb")
            self.assertEqual(iom["license"], "srsim-lic-26.7.txt")
            endpoints = [endpoint for link in self.links for endpoint in link["endpoints"]]
            for port in ("1/1/1", "1/1/2", "1/1/3"):
                self.assertIn(f"{router}-iom:{port}", endpoints)

    def test_nat_routers_have_operational_vrrp_and_sync_config(self):
        for router, link_local, peer in (
            ("cgnat1", "fe80::2", "10.255.255.2"),
            ("cgnat2", "fe80::3", "10.255.255.1"),
        ):
            config = (RECIPE / self.nodes[router]["startup-config"]).read_text()
            self.assertEqual(config.count("{"), config.count("}"))
            self.assertIn("card-type iom-e", config)
            self.assertIn("mda-type isa2-bb", config)
            self.assertIn("mda 1/2 { }", config)
            self.assertNotIn("esa 1", config)
            self.assertIn(f"address {link_local}", config)
            self.assertIn("backup [fe80::1 2001:db8:1::1]", config)
            self.assertIn("use-virtual-mac true", config)
            self.assertIn(f"next-hop {peer} {{ admin-state enable }}", config)

    def test_core_advertises_inet_and_enables_nat_return_routes(self):
        config = (RECIPE / "configs/ne/core.txt").read_text()
        self.assertIn('interface "INET" { passive true }', config)
        self.assertIn("next-hop 192.0.2.1 { admin-state enable preference 10 }", config)
        self.assertIn("next-hop 192.0.2.5 { admin-state enable preference 20 }", config)

    def test_dashboards_query_the_mda_metrics(self):
        dashboards = RECIPE / "grafana-dashboards"
        for name in ("cgnat-isa-and-icr.json", "cgnat-pools-and-dslite.json"):
            dashboard = json.loads((dashboards / name).read_text())
            expressions = [
                target["expr"]
                for panel in dashboard["panels"]
                for target in panel.get("targets", [])
                if "expr" in target
            ]
            hardware_queries = [
                expr for expr in expressions
                if "state_isa_nat_group_mda_" in expr or "state_isa_nat_group_esa_" in expr
            ]
            self.assertTrue(any("state_isa_nat_group_mda_" in expr for expr in hardware_queries), name)
            self.assertFalse(any("state_isa_nat_group_esa_" in expr for expr in expressions), name)

    def test_dashboard_resources_refresh_cached_content(self):
        resources = RECIPE / "nok-manifests/grafana/dashboards"
        for name in ("cgnat-isa-and-icr.yaml", "cgnat-pools-and-dslite.yaml"):
            resource = yaml.safe_load((resources / name).read_text())
            self.assertEqual(resource["spec"]["contentCacheDuration"], "1m", name)
            self.assertEqual(resource["spec"]["resyncPeriod"], "1m", name)

    def test_subscriber_traffic_uses_separate_forward_and_reverse_udp(self):
        lan = (RECIPE / "configs/hosts/lan.sh").read_text()
        internet = (RECIPE / "configs/hosts/inet.sh").read_text()
        self.assertIn("REVERSE_PORT=$((IPERF_PORT + 3))", lan)
        self.assertIn('"$REVERSE_PORT" -b 4k -l 100 -t 86400 -R', lan)
        self.assertNotIn("--bidir", lan)
        self.assertIn("for port in 5204 5205 5206", internet)

    def test_nat444_topology_is_isolated_and_has_two_customer_translations(self):
        topology = yaml.safe_load((RECIPE / "topo-nat444.yaml").read_text())
        nodes = topology["topology"]["nodes"]
        self.assertEqual(topology["name"], "sros-nat444")
        self.assertEqual(topology["mgmt"]["ipv4-subnet"], "172.21.40.0/24")
        self.assertEqual(nodes["nat-iom"]["network-mode"], "container:nat")
        self.assertEqual(nodes["nat-iom"]["env"]["NOKIA_SROS_MDA_2"], "isa2-bb")
        for customer in ("cpe1", "cpe2"):
            self.assertEqual(nodes[customer]["image"], "nok-nat44-cpe:local")
            self.assertEqual(nodes[customer]["env"]["START_TRAFFIC"], "no")
            self.assertIn("sh /startup.sh", nodes[customer]["cmd"])
        self.assertNotEqual(nodes["cpe1"]["env"]["WAN4"], nodes["cpe2"]["env"]["WAN4"])
        cpe = (RECIPE / "configs/hosts/nat44-cpe.sh").read_text()
        self.assertIn("192.168.1.50/24", cpe)
        self.assertIn("-j MASQUERADE", cpe)
        self.assertNotIn("--bidir", cpe)
        self.assertIn("REVERSE_TCP_PORT", cpe)
        self.assertIn("REVERSE_UDP_PORT", cpe)
        image = (RECIPE / "configs/hosts/Dockerfile.nat44").read_text()
        self.assertIn("apk add --no-cache iptables ip6tables", image)

    def test_nat444_sr7_topology_uses_iom4e_and_isa_mda(self):
        topology = yaml.safe_load((RECIPE / "topo-nat444-sr7.yaml").read_text())
        nodes = topology["topology"]["nodes"]
        self.assertEqual(topology["name"], "sros-nat444-sr7")
        self.assertEqual(topology["mgmt"]["ipv4-subnet"], "172.21.41.0/24")
        self.assertEqual(nodes["nat-a"]["type"], "SR-7")
        self.assertEqual(nodes["nat-a"]["env"]["NOKIA_SROS_SLOT"], "A")
        self.assertEqual(nodes["nat-a"]["env"]["NOKIA_SROS_CARD"], "cpm5")
        self.assertEqual(nodes["nat-a"]["env"]["NOKIA_SROS_SFM"], "m-sfm6-7/12")
        self.assertEqual(nodes["nat-a"]["startup-config"], "configs/ne/nat444-sr7.txt")
        self.assertEqual(nodes["nat-a"]["mgmt-ipv4"], "172.21.41.11")
        self.assertEqual(nodes["nat-b"]["network-mode"], "container:nat-a")
        self.assertEqual(nodes["nat-b"]["env"]["NOKIA_SROS_SLOT"], "B")
        self.assertEqual(nodes["nat-1"]["network-mode"], "container:nat-a")
        self.assertEqual(nodes["nat-1"]["env"]["NOKIA_SROS_SLOT"], "1")
        self.assertEqual(nodes["nat-1"]["env"]["NOKIA_SROS_CARD"], "iom4-e")
        self.assertEqual(nodes["nat-1"]["env"]["NOKIA_SROS_MDA_1"], "me6-10gb-sfp+")
        self.assertEqual(nodes["nat-1"]["env"]["NOKIA_SROS_MDA_2"], "isa2-bb")
        self.assertEqual(nodes["cpe1"]["env"]["WAN4"], "100.64.1.10/24")
        self.assertEqual(nodes["cpe2"]["env"]["WAN4"], "100.64.1.11/24")
        config = (RECIPE / nodes["nat-a"]["startup-config"]).read_text()
        self.assertEqual(config.count("{"), config.count("}"))
        for required in (
            "card-type iom4-e", "sfm-type m-sfm6-7/12", "mda-type isa2-bb",
            "mda 1/2 { }", "port 1/1/1", "sap 1/1/2",
        ):
            self.assertIn(required, config)

    def test_nat444_provider_uses_dedicated_vprns_and_blocks_shared_address_leaks(self):
        config = (RECIPE / "configs/ne/nat444.txt").read_text()
        self.assertEqual(config.count("{"), config.count("}"))
        for required in (
            "nat-group 2", 'vprn "700"', 'vprn "500"',
            'pool { router-instance "500" name "nat444-pool" }',
            "destination-prefix 0.0.0.0/0", "ports 512", "subscriber-limit 64",
            "198.51.100.128 end 198.51.100.254", "filter-id 700",
            "src-ip { address 100.64.0.0/10 }", 'filter { ip "no-rfc6598-leak" }',
            "udp { inbound-refresh true }",
        ):
            self.assertIn(required, config)
        self.assertNotIn("route 0.0.0.0/0", config)

    def test_nat444_metrics_target_and_pipeline_collect_datapath(self):
        target = yaml.safe_load((RECIPE / "nat444/network-device-target.yaml").read_text())
        self.assertEqual(target["spec"]["address"], "172.21.40.11")
        self.assertFalse(target["spec"]["sdcio"]["enabled"])
        self.assertTrue(target["spec"]["gnmic"]["enabled"])
        pipeline = yaml.safe_load((RECIPE / "nok-manifests/gnmic/pipelines/gnmic-pipe-cgnat-tel.yaml").read_text())
        self.assertEqual(set(pipeline["spec"]["subscriptionRefs"]), {
            "sros-nat-availability-refresh", "sros-nat-saturation-sample", "sros-nat-datapath-sample",
        })

    def test_nat444_dashboard_queries_only_the_nat444_source_and_group(self):
        dashboard = json.loads((RECIPE / "grafana-dashboards/cgnat-nat444.json").read_text())
        self.assertEqual(dashboard["uid"], "cgnat-nat444")
        self.assertEqual(len(dashboard["panels"]), 7)
        for panel in dashboard["panels"]:
            for target in panel["targets"]:
                self.assertIn('source="nok-cgnat/clab-sros-nat444-nat"', target["expr"])
                self.assertIn('nat_group_id="2"', target["expr"])
                self.assertNotIn("dslite_forward", target["expr"])

    def test_nat444_sr7_observability_is_separate_and_queries_mda_metrics(self):
        target = yaml.safe_load((RECIPE / "nat444-sr7/network-device-target.yaml").read_text())
        self.assertEqual(target["spec"]["address"], "172.21.41.11")
        self.assertEqual(target["spec"]["hostname"], "clab-sros-nat444-sr7-nat-a")
        self.assertFalse(target["spec"]["sdcio"]["enabled"])
        self.assertTrue(target["spec"]["gnmic"]["enabled"])
        dashboard = json.loads((RECIPE / "grafana-dashboards/cgnat-nat444-sr7.json").read_text())
        self.assertEqual(dashboard["uid"], "cgnat-nat444-sr7")
        self.assertEqual(dashboard["title"], "CG-NAT NAT444 - SR7 ISA")
        self.assertEqual(len(dashboard["panels"]), 7)
        expressions = []
        for panel in dashboard["panels"]:
            for target in panel["targets"]:
                expression = target["expr"]
                expressions.append(expression)
                self.assertIn('source="nok-cgnat/clab-sros-nat444-sr7-nat-a"', expression)
                self.assertIn('nat_group_id="2"', expression)
                self.assertNotIn("_esa_", expression)
        self.assertTrue(any("_mda_" in expression for expression in expressions))


@unittest.skipUnless(os.environ.get("NOK_RUN_NAT444_TESTS") == "yes", "Requires the isolated NAT444 lab")
class Nat444RuntimeTests(unittest.TestCase):
    lab = os.environ.get("NOK_NAT444_LAB", "sros-nat444")

    def container_name(self, container):
        return f"clab-{self.lab}-{container}"

    def docker(self, container, *command, timeout=20):
        return subprocess.run(
            ["docker", "exec", self.container_name(container), *command],
            check=True, capture_output=True, text=True, timeout=timeout,
        ).stdout

    def test_reverse_udp_survives_initial_mapping_timeout(self):
        for customer, port in (("cpe1", "6303"), ("cpe2", "6304")):
            with self.subTest(customer=customer):
                result = json.loads(self.docker(
                    customer, "ip", "netns", "exec", "customer", "iperf3", "-c", "192.0.2.2",
                    "-p", port, "-u", "-b", "8k", "-l", "100", "-t", "25", "-R", "-J", timeout=40,
                ))
                self.assertNotIn("error", result)
                summary = result["end"].get("sum_received", result["end"].get("sum", {}))
                self.assertGreaterEqual(summary.get("bytes", 0), 24000)
                self.assertEqual(summary.get("lost_packets", 0), 0)

    def test_both_customers_pass_tcp_and_udp_in_both_directions(self):
        for customer, tcp_port, udp_port in (("cpe1", 5203, 5303), ("cpe2", 5204, 5304)):
            self.docker(customer, "ip", "netns", "exec", "customer", "ping", "-c", "3", "-W", "2", "192.0.2.2")
            for protocol, port in (("tcp", tcp_port), ("udp", udp_port)):
                for reverse in (False, True):
                    with self.subTest(customer=customer, protocol=protocol, reverse=reverse):
                        options = ["-u", "-b", "8k", "-l", "100"] if protocol == "udp" else []
                        if reverse:
                            options.append("-R")
                        output = self.docker(customer, "ip", "netns", "exec", "customer", "iperf3",
                                             "-c", "192.0.2.2", "-p", str(port), "-t", "3", "-J", *options)
                        result = json.loads(output)
                        self.assertNotIn("error", result)
                        summary = result["end"].get("sum_received", result["end"].get("sum", {}))
                        self.assertGreater(summary.get("bytes", 0), 0)
                        if protocol == "udp":
                            self.assertEqual(summary.get("lost_packets", 0), 0)

    def test_packet_captures_show_both_nat_stages(self):
        captures = []
        try:
            for container, interface, expression in (
                ("access", "eth2", "src host 100.64.1.10 and udp and dst port 5303"),
                ("inet", "eth1", "src net 198.51.100.128/25 and udp and dst port 5303"),
            ):
                captures.append(subprocess.Popen(
                    ["docker", "exec", self.container_name(container), "timeout", "12",
                     "tcpdump", "-nn", "-i", interface, "-c", "2", expression],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ))
            result = json.loads(self.docker("cpe1", "ip", "netns", "exec", "customer", "iperf3",
                                           "-c", "192.0.2.2", "-p", "5303", "-u", "-b", "8k",
                                           "-l", "100", "-t", "3", "-J"))
            self.assertNotIn("error", result)
            outputs = []
            for capture in captures:
                output, error = capture.communicate(timeout=15)
                self.assertEqual(capture.returncode, 0, error)
                outputs.append(output)
            self.assertRegex(outputs[0], r"IP 100\.64\.1\.10\.\d+ > 192\.0\.2\.2\.5303")
            sources = re.findall(r"IP 198\.51\.100\.(\d+)\.\d+ > 192\.0\.2\.2\.5303", outputs[1])
            self.assertTrue(sources)
            self.assertTrue(all(128 <= int(last_octet) <= 254 for last_octet in sources))
        finally:
            for capture in captures:
                if capture.poll() is None:
                    capture.kill()
                    capture.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
