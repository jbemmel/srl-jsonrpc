#!/usr/bin/python3

# This example illustrates a way to use JSON RPC with multiple SRL nodes in parallel,
# creating checkpoints and exclusive configuration sessions to get consistent
# rollback

import requests,json

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
    return resp.json() if resp.text else ""

def _jsonrpcRunCli(node,cmds):
    data = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "cli",
        "params": {
            "commands": cmds
        }
    }
    return _jsonrpcPost(node,data)

RANDOM_ID = "xyz"

cmds = [
 f"enter candidate exclusive name {RANDOM_ID}",
 f"/tools system configuration generate-checkpoint name {RANDOM_ID}",

 # Sample: Create a VLAN on both ports in a MH lag on 2 leaves
 "/interface lag3 vlan-tagging true",
 "/interface lag3 subinterface 1 vlan encap single-tagged vlan-id 20",

 "commit now"
]

success = True
NODES = ["clab-evpn-lab-leaf2","clab-evpn-lab-leaf3"]
for node in NODES:
  success = success and not "error" in _jsonrpcRunCli(node,cmds)

for node in NODES:
  cmds2 = [
    f"enter candidate exclusive name {RANDOM_ID}"
  ]
  if not success:
    cmds2 += [
      f"/tools system configuration checkpoint {RANDOM_ID} revert"
    ]
  ]
  cmds2 += [
    f"/tools system configuration checkpoint {RANDOM_ID} clear"
  ]
  _jsonrpcRunCli(node,cmds2)
