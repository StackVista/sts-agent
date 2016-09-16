#!/bin/sh

echo "Lines that might need renaming:"

grep -r etc/dd | grep -v README | grep -v CHANGELOG | grep -ve "^[^:]*:\\s*\#.*"
grep -r datadog\\.conf . | grep -v sts-check-naming | grep -v Binary | grep -v CHANGELOG | grep -ve "^[^:]*:\\s*\#.*" | grep -v README | grep -v git/logs
grep -r ddagent.py . | grep -v sts-check-naming | grep -v Binary | grep -v git/logs
grep -r datadog_agent . | grep -v sts-check-naming | grep -v git/logs
grep -r opt/datadog . | grep -v sts-check-naming
grep -re "echo.*DataDog" . | grep -v sts-check-naming
grep -r "from ddagent import" . | grep -v sts-check-naming
