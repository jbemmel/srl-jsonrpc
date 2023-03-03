#!/usr/bin/python3

# This example illustrates a way to use JSON RPC with multiple SRL nodes in parallel,
# creating checkpoints and exclusive configuration sessions to get consistent
# rollback

import requests,json,string,random,time,sys

USERNAME = "admin"
PASSWORD = "NokiaSrl1!"

def _jsonrpcPost(node, json_data, timeout=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    geturl = f"https://{USERNAME}:{PASSWORD}@{node}:443/jsonrpc"
    resp = requests.post(geturl, headers=headers, json=json_data, timeout=timeout, verify=False)
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

RANDOM_ID = "C" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
print( f"Selected random ID: {RANDOM_ID}" )

VLAN = sys.argv[1] if len(sys.argv) > 1 else "10"

cmds = [
 f"enter candidate exclusive name {RANDOM_ID}",
 f"/tools system configuration generate-checkpoint name {RANDOM_ID}",

 # Sample: Create a VLAN on both ports in a MH lag on 2 leaves
 "/interface lag3 vlan-tagging true",
 f"/interface lag3 subinterface 0 vlan encap single-tagged vlan-id {VLAN}",

 "commit stay" # Tried 'commit validate' but it allows invalid vlan config
]

success = True
NODES = ["clab-evpn-lab-leaf2","clab-evpn-lab-leaf3"]
for node in NODES:
  success = success and not "error" in _jsonrpcRunCli(node,cmds)
  if not success: break

time.sleep(20.0) # Wait 20 seconds for parallel testing purposes

for node in NODES:
  _action = "clear" if success else "revert"
  cmds2 = [
    f"enter candidate exclusive name {RANDOM_ID}",
    f"/tools system configuration checkpoint {RANDOM_ID} {_action}"
  ]
  if not success:
    cmds2 += [ f"/tools system configuration checkpoint {RANDOM_ID} clear" ]
  _jsonrpcRunCli(node,cmds2) # May return an error if checkpoint does not exist

print( f"RESULT: {'SUCCESS' if success else 'FAILED'}" )
