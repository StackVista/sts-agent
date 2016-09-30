#!/bin/bash

set -e

STSURL="`grep '^dd_url: ' /etc/sts-agent/stackstate.conf | sed 's/^dd_url: //'`" /opt/stackstate-agent/bin/connbeat -c /etc/sts-agent/connbeat.yml -path.logs /var/log/stackstate -path.data /var/lib/stackstate/connbeat
