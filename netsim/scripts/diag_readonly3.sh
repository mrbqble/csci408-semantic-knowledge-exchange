#!/usr/bin/env bash
echo "== netem modules still loaded? =="
grep -E '^sch_(netem|tbf|htb)' /proc/modules || echo "(none loaded)"
echo "== block devices =="
lsblk -o NAME,SIZE,TYPE,FSTYPE,UUID,MOUNTPOINTS 2>&1 | head -20
echo "== is UUID 2f18d9e1 present? =="
ls -l /dev/disk/by-uuid 2>/dev/null | grep -i 2f18d9e1 || echo "no device with UUID 2f18d9e1-436a-4240-beae-90af61681345 (it is gone)"
echo "== D-state tasks =="
ps -eo pid,ppid,stat,etime,wchan:30,comm | awk 'NR==1 || $3 ~ /^D/'
echo "== dmesg events after the first stall line, excluding the stall repeats =="
timeout 10 dmesg | awk '/tasks_rcu_exit_srcu_stall/ {f=1} f' | grep -vE 'tasks_rcu_exit_srcu_stall|Please check any exiting' | head -15