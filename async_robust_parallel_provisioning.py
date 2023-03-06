#!/usr/bin/python3

# This example illustrates a way to use JSON RPC with multiple SRL nodes in parallel,
# using Python 3.11 asyncio TaskGroup to parallelize execution

# I initially tried creating checkpoints and exclusive configuration sessions to get consistent
# rollback, but exclusive sessions don't seem to work when opened through JSON RPC. Further investigation
# suggests that the SRL JSON RPC server closes the connection afer every request (using gunicorn with sync workers)
# which is likely why the 'exclusive' candidate doesn't stay in place
#
# This new version uses 'commit confirmed', which starts a timer that requires explicit 'accept'
# within a configurable deadline.

import requests,json,string,random,time,sys

USERNAME = "admin"
PASSWORD = "NokiaSrl1!"

# Create single session, has a connection pool by default
# BUT: Server closes the connection after every request
session = requests.Session()

def _jsonrpcPost(node, json_data, timeout=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    geturl = f"https://{USERNAME}:{PASSWORD}@{node}:443/jsonrpc"
    resp = session.post(geturl, headers=headers, json=json_data, timeout=timeout, verify=False)
    resp.raise_for_status()
    print( json.dumps(resp.json()) )
    return resp.json()

def _jsonrpcRunCli(node,cmds):
    data = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "cli",
        "params": {
            "commands": cmds
        }
    }
    print( f"Sending commands: {cmds}" )
    return _jsonrpcPost(node,data)

RANDOM_ID = "C" # + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
print( f"Selected random ID: {RANDOM_ID}" )

SUBIF = sys.argv[1] if len(sys.argv) > 1 else "0"
VLAN = sys.argv[2] if len(sys.argv) > 2 else "10"

NODES = ["clab-evpn-lab-leaf2","clab-evpn-lab-leaf3"]

# Async version
import asyncio

async def configure_node(node):
  cmds = [
   # Could optionally still use an exclusive candidate here, until 'commit confirmed'
   f"enter candidate name {RANDOM_ID}",

   # Sample: Create a VLAN on both ports in a MH lag on 2 leaves
   "/interface lag3 vlan-tagging true",
   f"/interface lag3 subinterface {SUBIF} vlan encap single-tagged vlan-id {VLAN}",

   "commit confirmed timeout 30" # Automatic rollback after 30s unless confirmed
  ]

  while "error" in (result := _jsonrpcRunCli(node,cmds)):
    if "in progress" in result["error"]["message"]:
      # Backoff
      print( "Backing off 5 seconds..." )
      await asyncio.sleep(5.0)
    else:
      return False
  return True # success

async def finalize_node(node,accept):
  cmds = [
    f"enter candidate name {RANDOM_ID}",
    f"commit confirmed {'accept' if accept else 'reject'}"
  ]
  return _jsonrpcRunCli(node,cmds)

async def main():
    results = []
    async with asyncio.TaskGroup() as tg: # Since Python 3.11
      for node in NODES:
        task = tg.create_task(configure_node(node))
        results.append( task )
    print( f"All node configuration tasks have completed now. {results}")

    success = all( [ t.result() for t in results ] )

    async with asyncio.TaskGroup() as tg: # Since Python 3.11
      for node in NODES:
        task = tg.create_task(finalize_node(node,success))
    print( f"All nodes confirmed; success={success}" )

asyncio.run(main())
