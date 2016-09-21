#!/bin/sh

PATH=/opt/stackstate-agent/embedded/bin:/opt/stackstate-agent/bin:$PATH

exec /opt/stackstate-agent/bin/supervisord -c /etc/sts-agent/supervisor.conf
