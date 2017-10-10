#!/bin/sh

PATH=/opt/stackstate-agent/embedded/bin:/opt/stackstate-agent/bin:$PATH

if [ "$STACKSTATE_ENABLED" = "no" ]; then
    echo "Disabled via STACKSTATE_ENABLED env var. Exiting."
    exit 0
fi

exec /opt/stackstate-agent/bin/supervisord -c /etc/sts-agent/supervisor.conf
