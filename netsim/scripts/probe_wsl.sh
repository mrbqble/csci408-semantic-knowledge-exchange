#!/usr/bin/env bash
# Read-mostly probe of the WSL2 environment for the netsim layer.
echo "kernel: $(uname -r)"
echo "cpus: $(nproc)  mem: $(free -g | awk 'NR==2{print $2" GB"}')"
echo "tc: $(command -v tc || echo missing)"
if [ -r /proc/config.gz ]; then
  zcat /proc/config.gz | grep -E '^CONFIG_NET_SCH_(NETEM|TBF|HTB)='
else
  echo "no /proc/config.gz"
fi
echo "-- netem on lo --"
timeout 10 tc qdisc replace dev lo root netem delay 10ms 2>&1
echo "add_exit=$?"
timeout 5 tc qdisc show dev lo 2>&1
timeout 5 tc qdisc del dev lo root 2>&1
echo "-- gpu in WSL --"
timeout 10 nvidia-smi -L 2>&1 | head -2
echo "-- docker in WSL --"
timeout 10 docker --version 2>&1 | head -1
echo "-- done --"
