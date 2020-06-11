FROM debian:latest

COPY rootfs/usr /usr/
COPY rootfs/etc/supervisor.conf /etc/supervisor.conf

RUN apt-get -qy update && \
  apt-get install -qy wget && \
  wget -q https://5fzd4zyw2d.execute-api.eu-west-1.amazonaws.com/prod/getfile/stackstate-agent_1.3.0-1_amd64.deb?licencekey=89B30-03X84-D33B3 -O agent.deb && \
  apt-get install -qy ./agent.deb && \
  /usr/local/bin/apt_clean && \
  rm agent.deb

# Prepare agent setup
RUN mkdir /var/log/stackstate && \
  chown sts-agent:sts-agent /var/log/stackstate && \
  cp /etc/sts-agent/stackstate.conf.example /etc/sts-agent/stackstate.conf

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]