# Event-Driven Ansible source plugin for pulling Red Hat Insigths events

This directory contains an example source plugin (`new_events.py`) for Event-Drive Ansible (EDA) along with a rulebook and playbook to execute. The source plugin accepts arguments for Hybrid Cloud Console instance, and username, password for basic authentication.

The plugin queries the Insights API Notifications get_events to retrieve a list of triggered events for the account on that day. It then processes all events and wait until the next query (interval value in seconds). The next result will be checked for new event ids and will be processed accordingly.

**Note** this plugin is a proof-of-concept and is meant to be an example to get started. It is in no way ready for production use. The defaultvalues queries all events triggered today (smalest window range on the API) and happens every 60 sec.

## Testing

### pre-requisites
- ansible-rulebook>=0.10.1 [[install instructions]](https://github.com/ansible/event-driven-ansible#getting-started)
- ansible-core>=2.14.1
- ansible collection(s):
    - ansible.eda>=1.3.3
----

- To test the script independently, first set environment variables for `HCC_HOST`, `HCC_USERNAME`, `HCC_PASSWORD` and run:
~~~
python new_events.py
~~~

- To test the script from `ansible-rulebook` (the CLI component of EDA), set environment variables for `HCC_HOST`, `HCC_USERNAME`, `HCC_PASSWORD` and run:
~~~
ansible-rulebook --rulebook new_events_rulebook.yml \
        -i inventory.yml \
        -S . \
        --env-vars HCC_HOST,HCC_USERNAME,HCC_PASSWORD \
        --print-events
~~~

In above command, `-S` tells `ansible-rulebook` where to look for source plugins. Typically, these source plugins would be contained within an ansible collection, but this flag works well for testing.

`--print-events` is useful to show the entire event that triggered the action. With this enabled, you'll see all event data printed before the playbook output. 

The `--env-vars` flag passes the specified environment variables into the execution of this rulebook. These environment variables match the names of the variable pulled in as a part of the arguents passed into the source plugin as defined in the source configuration in the rulebook:

~~~
  sources:
    - new_events:
        instance: "{{ HCC_HOST }}"
        username: "{{ HCC_USERNAME }}"
        password: "{{ HCC_PASSWORD }}" 
        interval: 60
~~~~

