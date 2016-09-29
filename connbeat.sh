#!/bin/bash

STSURL="`grep '^dd_url: ' /etc/sts-agent/stackstate.conf | sed 's/^dd_url: //'`" /opt/stackstate-agent/bin/connbeat -c /etc/sts-agent/connbeat.yml -path.logs /var/log/connbeat -path.data /var/lib/connbeat
