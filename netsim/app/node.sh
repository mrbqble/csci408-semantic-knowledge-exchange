#!/bin/sh
# Entry point of sender and ingest containers: add the route through the router, optionally
# shape this node's own egress (per-link mode), then exec the python program.
set -eu
if [ -n "${ROUTE_NET:-}" ]; then
  ip route replace "$ROUTE_NET" via "$ROUTE_GW"
fi
if [ -n "${NETEM_EGRESS:-}" ]; then
  # shellcheck disable=SC2086
  tc qdisc replace dev eth0 root netem $NETEM_EGRESS
  echo "[node] netem egress: $NETEM_EGRESS"
fi
exec python -u "$@"