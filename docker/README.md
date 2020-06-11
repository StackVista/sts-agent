The docker image can be build manually and pushed to docker hub with:

```
docker build --tags stackstate/sts-agent:<version> --build-arg STS_AGENT_VERSION=<version> --build-arg STS_LICENSE_KEY=<key> .

docker push stackstate/sts-agent:<version>
```

For example the latest version at time of writing is version 1.3.0.

