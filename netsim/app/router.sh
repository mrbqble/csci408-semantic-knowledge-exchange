#!/bin/sh
# Router between the edge network (cameras) and the core network (ingest). The shared bottleneck
# lives on its egress towards the core: NETEM_UP shapes camera->ingest traffic for all cameras at once,
# NETEM_DOWN shapes the return path (acks).
set -eu
iface_of() { ip -o -4 addr show | awk -v ip="$1" '$4 ~ ("^" ip "/") {print $2; exit}'; }
EDGE_IF=$(iface_of "$EDGE_IP")
CORE_IF=$(iface_of "$CORE_IP")
echo "[router] edge=$EDGE_IF core=$CORE_IF forward=$(cat /proc/sys/net/ipv4/ip_forward)"
if [ -n "${NETEM_UP:-}" ];   then tc qdisc replace dev "$CORE_IF" root netem $NETEM_UP;   echo "[router] uplink  (cameras->ingest) on $CORE_IF: $NETEM_UP"; fi
if [ -n "${NETEM_DOWN:-}" ]; then tc qdisc replace dev "$EDGE_IF" root netem $NETEM_DOWN; echo "[router] downlink (ingest->cameras) on $EDGE_IF: $NETEM_DOWN"; fi
tc qdisc show dev "$CORE_IF"
tc qdisc show dev "$EDGE_IF"
echo "[router] ready"
exec sleep infinity