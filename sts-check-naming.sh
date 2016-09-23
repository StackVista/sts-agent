#!/bin/sh

echo "This script looks for references to 'datadog' in the codebase."
echo -n
echo "When it produces any output beyond this header, decide whether to change the code or update the script to remove the false positive:"

grep -r etc/dd . | grep -v README | grep -v CHANGELOG | grep -ve "^[^:]*:\\s*\#.*"
grep -r datadog\\.conf . | grep -v sts-check-naming | grep -v Binary | grep -v CHANGELOG | grep -ve "^[^:]*:\\s*\#.*" | grep -v README | grep -v git/logs
grep -r ddagent.py . | grep -v sts-check-naming | grep -v Binary | grep -v git/logs
grep -r dd-agent . | grep -v dd-agent-testing | grep -v README | grep -v CONTRIBUTING | grep -v appveyor | grep -v dd-agent/wiki | grep -v dd-agent/issues | grep -v .git/config | grep -ve ".py:\\s*#" | grep -v sts-check-naming | grep -v Binary | grep -v git/logs | grep -v CHANGELOG | grep -ve "^./ci/" | grep -v smartos | grep -v win32 | grep -v osx | grep -v blah | grep -v /source/ | grep -ve "^./tests" | grep -v git/logs | grep -ve "^./.git"
grep -r datadog_agent . | grep -v sts-check-naming | grep -v git/logs
grep -r opt/datadog . | grep -v sts-check-naming | grep -v CHANGELOG
grep -re "echo.*DataDog" . | grep -v sts-check-naming
grep -r "from ddagent import" . | grep -v sts-check-naming
grep -rie "log\.info.*DataDog" . | grep -v sts-check-naming
grep -rie "log\.warn.*DataDog" . | grep -v sts-check-naming
grep -rie "log\.error.*DataDog" . | grep -v sts-check-naming
grep -r datadoghq . | grep -v sts-check-naming | grep -v CHANGELOG | grep -ve "^./ci/" | grep -v centos | grep -v "/source/" | grep -v win32 | grep -ve "^./tests/" | grep -v README | grep -v CONTRIBUTING | grep -v LICENSE | grep -v git/logs | grep -v osx | grep -ve "^./.git/"

# Pending a decision on how far we go renaming dogstatsd, too
# grep -r dogstatsd . | grep -v sts-check-naming | grep -ve "^./\\w*.py:\\s*\"\"\"" | grep -v CHANGELOG | grep -v CONTRIBUTING
# grep -r "from dogstatsd import" . | grep -v sts-check-naming
