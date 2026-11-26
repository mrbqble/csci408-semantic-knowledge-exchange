#!/usr/bin/env bash
# READ-ONLY diagnostics (second pass): no module loads, no tc.
echo "uptime since: $(uptime -s)   now: $(date '+%F %T')"
echo "== first RCU-tasks stall message + the 25 lines before it =="
timeout 10 dmesg > /tmp/dmesg.txt 2>&1
n=$(grep -n -m1 'tasks_rcu_exit_srcu_stall' /tmp/dmesg.txt | cut -d: -f1)
echo "first stall at dmesg line: ${n:-none}   total lines: $(wc -l < /tmp/dmesg.txt)"
if [ -n "$n" ]; then s=$((n>25?n-25:1)); sed -n "${s},$((n+2))p" /tmp/dmesg.txt; fi
echo "== other kernel complaints =="
grep -nE 'blocked for more than|Call Trace|BUG:|WARNING:|dxg|hung|Oops|segfault|Out of memory' /tmp/dmesg.txt | head -20
echo "== tasks in D state or exiting (this distro) =="
ps -eo pid,ppid,stat,etime,wchan:28,comm | awk 'NR==1 || $3 ~ /^D/ || $3 ~ /^Z/'
echo "== CONFIG_HZ of the running kernel =="
zcat /proc/config.gz 2>/dev/null | grep -E '^CONFIG_HZ=|CONFIG_TASKS_RCU=|CONFIG_RCU_TASKS'
echo "== done =="