FROM debian:latest

ARG STS_AGENT_VERSION
ARG STS_LICENSE_KEY

COPY rootfs/usr /usr/
COPY rootfs/etc/supervisor.conf /etc/supervisor.conf

RUN apt-get -qy update && \
  apt-get install -qy wget && \
  wget -q "https://5fzd4zyw2d.execute-api.eu-west-1.amazonaws.com/prod/getfile/stackstate-agent_${STS_AGENT_VERSION}-1_amd64.deb?licencekey=${STS_LICENSE_KEY}" -O agent.deb && \
  apt-get install -qy ./agent.deb && \
  /usr/local/bin/apt_clean && \
  rm agent.deb

# Prepare agent setup
RUN mkdir /var/log/stackstate && \
  chown sts-agent:sts-agent /var/log/stackstate && \
  cp /etc/sts-agent/stackstate.conf.example /etc/sts-agent/stackstate.conf

USER sts-agent

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]