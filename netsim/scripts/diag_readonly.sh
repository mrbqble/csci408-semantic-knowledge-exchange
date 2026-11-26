#!/usr/bin/env bash
# READ-ONLY diagnostics: never loads a module, never calls tc.
K=$(uname -r)
echo "== stuck processes (module/tc related) =="
ps -eo pid,ppid,stat,etime,wchan:30,args | grep -E 'insmod|modprobe|tc qdisc|timeout' | grep -v grep
for p in $(pgrep -x -f 'insmod|modprobe' 2>/dev/null); do echo "-- /proc/$p --"; timeout 3 cat /proc/$p/wchan; echo; timeout 3 cat /proc/$p/stack 2>&1 | head -12; done
echo "== kernel log (tail) =="
timeout 5 dmesg 2>&1 | tail -30
echo "== sysctl =="
sysctl kernel.modules_disabled kernel.modprobe 2>&1
echo "== loaded sched modules =="
grep -E 'sch_|netem' /proc/modules || echo "(none loaded)"
echo "== how /lib/modules is provided =="
readlink -f /lib/modules
mount | grep -E 'modules' || echo "(no dedicated mount)"
ls -la /lib/modules/$K/ 2>&1 | head -8
echo "== module file (userland read only) =="
timeout 10 modinfo /lib/modules/$K/kernel/net/sched/sch_netem.ko 2>&1 | head -12; echo "modinfo_exit=$?"
echo "== done =="