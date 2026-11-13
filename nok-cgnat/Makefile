CLAB ?= containerlab
DOCKER ?= docker
PYTHON ?= python3
KUBECTL ?= kubectl
KUBE_CONTEXT ?= kind-nok-demo

.PHONY: test nat444-build nat444-deploy nat444-test nat444-observe nat444-destroy nat444-traffic-start nat444-traffic-stop nat444-sr7-deploy nat444-sr7-test nat444-sr7-observe nat444-sr7-destroy nat444-sr7-traffic-start nat444-sr7-traffic-stop

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

nat444-build:
	$(DOCKER) build -t nok-nat44-cpe:local -f configs/hosts/Dockerfile.nat44 configs/hosts

nat444-deploy: nat444-build
	@test -s srsim-lic-26.7.txt || { echo "Missing authorized SR-SIM 26.7 license: srsim-lic-26.7.txt" >&2; exit 1; }
	$(CLAB) deploy -t topo-nat444.yaml

nat444-test: nat444-traffic-stop
	PYTHONDONTWRITEBYTECODE=1 NOK_RUN_NAT444_TESTS=yes $(PYTHON) -m unittest discover -s tests -v

nat444-traffic-stop:
	@for customer in cpe1 cpe2; do \
		$(DOCKER) exec clab-sros-nat444-$$customer pkill -x iperf3 >/dev/null 2>&1 || true; \
		$(DOCKER) exec clab-sros-nat444-$$customer pkill -x ping >/dev/null 2>&1 || true; \
	done

nat444-traffic-start: nat444-traffic-stop
	@$(DOCKER) exec clab-sros-nat444-inet pkill -x iperf3 >/dev/null 2>&1 || true
	$(DOCKER) exec clab-sros-nat444-inet sh /startup.sh
	@for customer in cpe1 cpe2; do \
		$(DOCKER) exec -e START_TRAFFIC=yes clab-sros-nat444-$$customer sh /startup.sh || exit 1; \
	done

nat444-observe:
	$(KUBECTL) --context "$(KUBE_CONTEXT)" create configmap cgnat-nat444-dashboard -n nok-cgnat --from-file=dashboard.json=grafana-dashboards/cgnat-nat444.json --dry-run=client -o yaml | $(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f -
	$(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f nat444/grafana-dashboard.yaml
	$(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f nat444/network-device-target.yaml

nat444-destroy:
	$(CLAB) destroy --cleanup -t topo-nat444.yaml

nat444-sr7-deploy: nat444-build
	@test -s srsim-lic-26.7.txt || { echo "Missing authorized SR-SIM 26.7 license: srsim-lic-26.7.txt" >&2; exit 1; }
	$(CLAB) deploy -t topo-nat444-sr7.yaml

nat444-sr7-test: nat444-sr7-traffic-stop
	NOK_NAT444_LAB=sros-nat444-sr7 NOK_RUN_NAT444_TESTS=yes $(PYTHON) -m unittest discover -s tests -v

nat444-sr7-traffic-stop:
	@for customer in cpe1 cpe2; do \
		$(DOCKER) exec clab-sros-nat444-sr7-$$customer pkill -x iperf3 >/dev/null 2>&1 || true; \
		$(DOCKER) exec clab-sros-nat444-sr7-$$customer pkill -x ping >/dev/null 2>&1 || true; \
	done

nat444-sr7-traffic-start: nat444-sr7-traffic-stop
	@$(DOCKER) exec clab-sros-nat444-sr7-inet pkill -x iperf3 >/dev/null 2>&1 || true
	$(DOCKER) exec clab-sros-nat444-sr7-inet sh /startup.sh
	@for customer in cpe1 cpe2; do \
		$(DOCKER) exec -e START_TRAFFIC=yes clab-sros-nat444-sr7-$$customer sh /startup.sh || exit 1; \
	done

nat444-sr7-observe:
	$(KUBECTL) --context "$(KUBE_CONTEXT)" create configmap cgnat-nat444-sr7-dashboard -n nok-cgnat --from-file=dashboard.json=grafana-dashboards/cgnat-nat444-sr7.json --dry-run=client -o yaml | $(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f -
	$(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f nat444-sr7/grafana-dashboard.yaml
	$(KUBECTL) --context "$(KUBE_CONTEXT)" apply -f nat444-sr7/network-device-target.yaml

nat444-sr7-destroy:
	$(CLAB) destroy --cleanup -t topo-nat444-sr7.yaml