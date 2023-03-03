#!/usr/bin/python3

# This example illustrates a way to use JSON RPC with multiple SRL nodes in parallel,

# I initially tried creating checkpoints and exclusive configuration sessions to get consistent
# rollback, but exclusive sessions don't seem to work when opened through JSON RPC
#
# This new version uses 'commit confirmed', which starts a timer that requires explicit 'accept'
# within a configurable deadline.

import requests,json,string,random,time,sys

USERNAME = "admin"
PASSWORD = "NokiaSrl1!"

# Create single session, has a connection pool by default
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

cmds = [
 f"enter candidate exclusive name {RANDOM_ID}",
 # f"/tools system configuration generate-checkpoint name {RANDOM_ID}",

 # Sample: Create a VLAN on both ports in a MH lag on 2 leaves
 "/interface lag3 vlan-tagging true",
 f"/interface lag3 subinterface {SUBIF} vlan encap single-tagged vlan-id {VLAN}",

 # "commit stay" # Tried 'commit validate' but it allows invalid vlan config
 "commit confirmed timeout 30" # Automatic rollback after 30s unless confirmed
]

NODES = ["clab-evpn-lab-leaf2","clab-evpn-lab-leaf3"]

def configure_nodes():

  IN_PROGRESS = "There is a commit already in progress for this candidate" # When using same candidate name in parallel
  # IN_PROGRESS = "commit confirmed in progress" # When using different candidate names

  for node in NODES:
    while "error" in (result := _jsonrpcRunCli(node,cmds)):
      if IN_PROGRESS in result["error"]["message"]:
        # Backoff
        print( "Backing off 5 seconds..." )
        time.sleep(5.0)
      else:
        return False
  return True # success

success = configure_nodes()
time.sleep(20.0) # Wait 20 seconds for parallel testing purposes

if success:
 for node in NODES:
  # _action = "clear" if success else "revert"
  cmds2 = [
    f"enter candidate exclusive name {RANDOM_ID}",
    # f"/tools system configuration checkpoint {RANDOM_ID} {_action}"
    "commit confirmed accept"
  ]
  # if not success:
  #   cmds2 += [ f"/tools system configuration checkpoint {RANDOM_ID} clear" ]
  _jsonrpcRunCli(node,cmds2) # May return an error if checkpoint does not exist

print( f"RESULT: {'SUCCESS' if success else 'FAILED'}" )
