[![Build Status](https://travis-ci.org/StackVista/sts-agent.svg?branch=master)](https://travis-ci.org/StackVista/sts-agent)

The StackState Agent collects events and metrics and brings them to your
[StackState](http://stackstate.com) instance for further analysis.

It includes telemetry information from various sources, as well as topology
information based on [connbeat](https://github.com/raboof/connbeat).

## Setup your environment

Required:
- python 2.7
- bundler (to get it: `gem install bundler`)

```
# Clone the repository
git clone git@github.com:DataDog/dd-agent.git

# Create a virtual environment and install the dependencies:
cd dd-agent
bundle install
rake setup_env
# NOTE: on mac osx python2 might be missing as an exectuable, failing the setup_env. Add this as a symlink

# Activate the virtual environment
source venv/bin/activate

# Lint
bundle exec rake lint

# Run a flavored test
bundle exec rake ci:run[apache]
```

## Test suite

More about how to write tests and run them [here](tests/README.md)

# How to configure the Agent

If you are using packages on linux, the main configuration file lives
in `/etc/dd-agent/datadog.conf`. Per-check configuration files are in
`/etc/dd-agent/conf.d`. We provide an example in the same directory
that you can use as a template.

# How to write your own checks

Writing your own checks is easy using our checks.d interface. Read more about
how to use it on our [Guide to Agent Checks](http://docs.datadoghq.com/guides/agent_checks/).