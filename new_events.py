"""
new_events.py

event-driven-ansible source plugin example

Poll Red Hat Hybrid Cloud Console API for new events triggered on the day of execution.
This script can be tested outside of ansible-rulebook by specifying
environment variables for HCC_HOST (optional), HCC_PROXY (optional), HCC_TOKEN_URL (optional), HCC_CLIENT_ID, and HCC_CLIENT_SECRET

Arguments:
  - instance:       (optional) Red Hat Hybrid Cloud Console URL. Default is https://console.redhat.com
  - proxy:          (optional) Proxy URL. Defaults to no proxy
  - token_url:      (optional) Access server token URL. Default is https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
  - client_id:      Public identifier required for authorization
  - client_secret:  Secret required for authorization
  - query:          (optional) Events to query. Defaults to all events created today
  - interval:       (optional) How often to poll for new events. Default is 60 seconds

- name: Watch for new events
  hosts: localhost
  sources:
    - new_events:
        instance: "{{ HCC_HOST | default('https://console.redhat.com') }}"
        proxy: "{{ HCC_PROXY | default('') }}"
        token_url: "{{ HCC_TOKEN_URL | default('https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token') }}"
        client_id: "{{ HCC_CLIENT_ID }}"
        client_secret: "{{ HCC_CLIENT_SECRET }}"
        interval: 60
  rules:
    - name: New event received
      condition: event.id is defined
      action:
        run_playbook:
            name: playbooks/new_event.yml
"""

import asyncio
import time
import os
import sys
from datetime import date
from datetime import timedelta
from typing import Any, Dict
import aiohttp

async def get_token(args: Dict[str, Any]):
    token_url = args.get("token_url")
    if f'{token_url}' == 'None': token_url = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
    proxy = args.get("proxy")
    if f'{proxy}' == 'None': proxy = ""
    client_id = args.get("client_id")
    client_secret = args.get("client_secret")
    scope = 'api.console'
    grant_type = 'client_credentials'

    data = {'client_id': client_id, 'client_secret': client_secret, 'scope': scope, 'grant_type': grant_type}

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{token_url}', data=data, proxy=f'{proxy}') as resp:
            if resp.status == 200:
                token = await resp.json()
            else:
                sys.exit(f'Error requesting access token: {resp.status}')
    return token

# Entrypoint from ansible-rulebook
async def main(queue: asyncio.Queue, args: Dict[str, Any]):

    instance = args.get("instance")
    if f'{instance}' == 'None': instance = "https://console.redhat.com"
    proxy = args.get("proxy")
    if f'{proxy}' == 'None': proxy = ""
    today = date.today()
    yesterday = today - timedelta(days = 1)
    query    = args.get("query", "endDate=" + today.strftime('%Y-%m-%d') +"&startDate=" + yesterday.strftime('%Y-%m-%d') + "&includePayload=true&limit=20")
    interval = int(args.get("interval", 60))

    token = await get_token(args)
    access_token = token.get('access_token')
    headers =  {'accept': 'application/json','Authorization': "Bearer {}".format(access_token)}

    start_time = time.time()
    start_time_str = time.strftime('%Y-%m-%d', time.gmtime(start_time))
    printed_events = set()

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(f'{instance}/api/notifications/v1.0/notifications/events?{query}', proxy=f'{proxy}', headers=headers) as resp:
                if resp.status == 200:
                    events = await resp.json()
                    for event in events['data']:
                        if event['created'] > start_time_str and event['id'] not in printed_events:
                            printed_events.add(event['id'])
                            await queue.put(event)
                elif resp.status == 401:
                    # Token is likely expired and returning a 401 Unauthorized error
                    if __debug__:
                        print(f'Error querying notifications apis: {resp.status}')
                    token = await get_token(args)
                    headers =  {'accept': 'application/json','Authorization': "Bearer {}".format(token.get('access_token'))}
                    continue
                else:
                    sys.exit(f'Error querying notifications apis: {resp.status}')
            await asyncio.sleep(interval)

# this is only called when testing plugin directly, without ansible-rulebook
if __name__ == "__main__":
    instance = os.environ.get('HCC_HOST')
    proxy = os.environ.get('HCC_PROXY')
    token_url = os.environ.get('HCC_TOKEN_URL')
    client_id = os.environ.get('HCC_CLIENT_ID')
    client_secret = os.environ.get('HCC_CLIENT_SECRET')

    class MockQueue:
        print(f"Waiting for events...")
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), {"instance": instance, "client_id": client_id, "client_secret": client_secret, "token_url": token_url, "proxy": proxy}))
