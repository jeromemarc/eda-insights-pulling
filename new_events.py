"""
new_events.py

event-driven-ansible source plugin example

Poll Insights API for new events
Only retrieves records created after the script began executing
This script can be tested outside of ansible-rulebook by specifying
environment variables for HCC_HOST, HCC_USERNAME, HCC_PASSWORD

Arguments:
  - instance: Hybrid Cloud Console URL (e.g. https://console.redhat.com)
  - username: Insights username
  - password: Insights password
  - query:    (optional) Events to query. Defaults to all events created today
  - interval: (optional) How often to poll for new records. Defaults to 60 seconds

- name: Watch for new events
  hosts: localhost
  sources:
    - cloin.servicenow.new_records:
        instance: https://console.redhat.com
        username: rh-jmarc
        password: *******
        interval: 60
  rules:
    - name: New event received
      condition: event.id is defined
      action:
        debug:
"""

import asyncio
import time
import os
from datetime import date
from datetime import timedelta
from typing import Any, Dict
import aiohttp

# Entrypoint from ansible-rulebook
async def main(queue: asyncio.Queue, args: Dict[str, Any]):

    instance = args.get("instance")
    token = args.get("token")
    today = date.today()
    yesterday = today - timedelta(days = 1)
    query    = args.get("query", "endDate=" + today.strftime('%Y-%m-%d') +"&startDate=" + yesterday.strftime('%Y-%m-%d') + "&includePayload=true&limit=20")
    interval = int(args.get("interval", 60))
    headers =  {'accept': 'application/json','Authorization': "Bearer {}".format(token)}

    start_time = time.time()
    start_time_str = time.strftime('%Y-%m-%d', time.gmtime(start_time))
    printed_events = set()
    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            async with session.get(f'{instance}/api/notifications/v1.0/notifications/events?{query}') as resp:
                if resp.status == 200:

                    events = await resp.json()
                    for event in events['data']:

                        if event['created'] > start_time_str and event['id'] not in printed_events:
                            printed_events.add(event['id'])
                            await queue.put(event)

                else:
                    print(f'Error {resp.status}')
            await asyncio.sleep(interval)


# this is only called when testing plugin directly, without ansible-rulebook
if __name__ == "__main__":
    instance = os.environ.get('HCC_HOST')
    token = os.environ.get('HCC_TOKEN')

    class MockQueue:
        print(f"Waiting for events...")
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), {"instance": instance, "token": token}))
