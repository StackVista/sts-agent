#!/bin/sh
# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

PATH=/opt/stackstate-agent/embedded/bin:/opt/stackstate-agent/bin:$PATH

exec /opt/stackstate-agent/bin/supervisord -c /etc/sts-agent/supervisor.conf
