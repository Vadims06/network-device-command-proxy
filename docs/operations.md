# Operations reference

Every operation below is called through `POST /v1/execute`. Each section lists the platforms that implement it and a real response. Lists are shortened to the first two entries.

The examples are produced by the built-in fixture devices, which replay device output captured with `vtysh` (FRR) and from IOS XR through the same parsers a live device uses. Their `data_source` is therefore `fixture`; a live device reports `data_source: "live"`. Junos returns the same models, with the fields listed in `unsupported_fields` set to `null`.

## Response envelope

Every device in a request gets one entry in `results`. Check `status` per device: one failing device does not fail the batch.

| Field | Meaning |
|---|---|
| `device` | Inventory name as sent in the request |
| `operation` | The operation that ran |
| `platform` | `frr`, `junos`, `iosxr`, or `unknown` when the device was not found |
| `status` | `success` or `error` |
| `data` | Operation-specific object; `null` on error |
| `error` | `{code, message}`; present only on error. See error codes in the README |
| `duration_ms` | Time spent on this device |
| `unsupported_fields` | Fields of `data` this vendor can never report; they are `null`, never omitted |
| `data_source` | `live` (real device), `fixture` (replayed capture) or `unknown` |

## get_ospf_neighbors

Platforms: FRR, Junos. OSPF adjacencies. One row per neighbor per interface.

Request:

```json
{"operation": "get_ospf_neighbors", "devices": ["123.10.10.10"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_ospf_neighbors",
      "platform": "frr",
      "status": "success",
      "data": {
        "instance": 1,
        "neighbors": [
          {
            "router_id": "123.123.100.100",
            "adjacency_state": "full",
            "state_raw": "full/-",
            "role": "dr_other",
            "interface": "eth1",
            "peer_address": "123.1.1.100",
            "dead_time_ms": 35616
          },
          {
            "router_id": "123.123.100.100",
            "adjacency_state": "full",
            "state_raw": "full/-",
            "role": "dr_other",
            "interface": "eth2",
            "peer_address": "10.10.100.2",
            "dead_time_ms": 35615
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_ospf_neighbor_detail

Platforms: FRR, Junos. Adds the area and the adjacency state-change counter (flap indicator).

Request:

```json
{"operation": "get_ospf_neighbor_detail", "devices": ["123.10.10.10"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_ospf_neighbor_detail",
      "platform": "frr",
      "status": "success",
      "data": {
        "instance": 1,
        "neighbors": [
          {
            "router_id": "123.123.100.100",
            "adjacency_state": "full",
            "state_raw": "full/-",
            "role": "dr_other",
            "interface": "eth1",
            "peer_address": "123.1.1.100",
            "dead_time_ms": 35583,
            "area": "0.0.0.0",
            "state_changes": 5
          },
          {
            "router_id": "123.123.100.100",
            "adjacency_state": "full",
            "state_raw": "full/-",
            "role": "dr_other",
            "interface": "eth2",
            "peer_address": "10.10.100.2",
            "dead_time_ms": 35583,
            "area": "0.0.0.0",
            "state_changes": 5
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_ospf_interfaces

Platforms: FRR, Junos. Every OSPF interface: cost, timers, network type, neighbor counts.

Request:

```json
{"operation": "get_ospf_interfaces", "devices": ["123.10.10.10"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_ospf_interfaces",
      "platform": "frr",
      "status": "success",
      "data": {
        "interfaces": [
          {
            "interface": "eth1",
            "up": true,
            "enabled": true,
            "state": "Point-To-Point",
            "network_type": "point_to_point_network",
            "network_type_raw": "pointopoint",
            "area": "0.0.0.0",
            "cost": 15,
            "hello_interval_ms": 10000,
            "dead_interval_sec": 40,
            "neighbors": 1,
            "adjacent_neighbors": 1
          },
          {
            "interface": "eth2",
            "up": true,
            "enabled": true,
            "state": "Point-To-Point",
            "network_type": "point_to_point_network",
            "network_type_raw": "pointopoint",
            "area": "0.0.0.0",
            "cost": 10,
            "hello_interval_ms": 10000,
            "dead_interval_sec": 40,
            "neighbors": 1,
            "adjacent_neighbors": 1
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_ospf_interface

Platforms: FRR, Junos. Same model as get_ospf_interfaces, filtered to one interface.

Request:

```json
{"operation": "get_ospf_interface", "devices": ["123.10.10.10"], "arguments": {"interface": "eth1"}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_ospf_interface",
      "platform": "frr",
      "status": "success",
      "data": {
        "interfaces": [
          {
            "interface": "eth1",
            "up": true,
            "enabled": true,
            "state": "Point-To-Point",
            "network_type": "point_to_point_network",
            "network_type_raw": "pointopoint",
            "area": "0.0.0.0",
            "cost": 15,
            "hello_interval_ms": 10000,
            "dead_interval_sec": 40,
            "neighbors": 1,
            "adjacent_neighbors": 1
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_ospf_status

Platforms: FRR, Junos. Router ID and per-area counters.

Request:

```json
{"operation": "get_ospf_status", "devices": ["123.10.10.10"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_ospf_status",
      "platform": "frr",
      "status": "success",
      "data": {
        "instance": 1,
        "router_id": "123.10.10.10",
        "areas": [
          {
            "area": "0.0.0.0",
            "active_interfaces": 6,
            "full_neighbors": 5,
            "spf_runs": 24,
            "lsa_count": 33
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_interface_status

Platforms: FRR, Junos. Admin/oper state, addresses, MTU and speed of one interface.

Request:

```json
{"operation": "get_interface_status", "devices": ["123.10.10.10"], "arguments": {"interface": "eth1"}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_interface_status",
      "platform": "frr",
      "status": "success",
      "data": {
        "interface": "eth1",
        "admin_up": true,
        "oper_up": true,
        "addresses": [
          "123.1.1.10/24",
          "fe80::a8c1:abff:fe6f:4dd0/64"
        ],
        "mtu": 9500,
        "speed_mbps": 10000
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_route

Platforms: FRR, Junos. Routes matching one prefix, with next hops.

Request:

```json
{"operation": "get_route", "devices": ["123.10.10.10"], "arguments": {"prefix": "123.30.30.30/32"}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.10.10.10",
      "operation": "get_route",
      "platform": "frr",
      "status": "success",
      "data": {
        "prefix": "123.30.30.30/32",
        "matched_prefix": "123.30.30.30/32",
        "found": true,
        "routes": [
          {
            "protocol": "ospf",
            "selected": true,
            "distance": 110,
            "metric": 1,
            "next_hops": [
              {
                "address": "10.1.30.2",
                "interface": "eth5",
                "active": true
              }
            ]
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_rsvp_lsps

Platforms: IOS XR. RSVP-TE sessions seen by this device (ingress, transit or egress), with explicit route, labels, FRR label and record route.

Request:

```json
{"operation": "get_rsvp_lsps", "devices": ["123.123.31.31"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.31.31",
      "operation": "get_rsvp_lsps",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "sessions": [
          {
            "destination": "109.109.109.109",
            "tunnel_id": "50000",
            "head_end": "17.17.17.17",
            "lsp_id": "15",
            "tunnel_name": "50000_F17-ASR9922_F109-ASR9001",
            "in_label": {
              "interface": "No intf",
              "label": "No label"
            },
            "incoming_address": "Unknown",
            "explicit_route": [
              {
                "path_status": "strict",
                "route_address": "20.50.0.1/32"
              },
              {
                "path_status": "strict",
                "route_address": "21.50.0.2/32"
              }
            ],
            "tspec": {
              "average_rate": 0.0,
              "burst": 1.0,
              "burst_unit": "K",
              "peak_rate": 0.0
            },
            "out_label": {
              "interface": "HundredGigE0/0/0/0",
              "label": "24023"
            },
            "frr_out_label": {
              "interface": "tunnel-te53300",
              "label": "3"
            },
            "record_route": [
              {
                "address": "141.141.141.141",
                "label_out": "24023",
                "flags": {
                  "local_protection_available": true,
                  "local_protection_in_use": false,
                  "soft_preempt": false,
                  "local_node_protection": false
                },
                "flags_raw": "0x21"
              },
              {
                "address": "20.50.0.1",
                "label_out": "24023",
                "flags": {
                  "local_protection_available": true,
                  "local_protection_in_use": false,
                  "soft_preempt": false,
                  "local_node_protection": false
                },
                "flags_raw": "0x1"
              }
            ],
            "fspec": {
              "average_rate": 0.0,
              "burst": 1.0,
              "burst_unit": "K",
              "peak_rate": 0.0
            }
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_vrf_detail

Platforms: IOS XR. VRFs with route distinguisher, interfaces and import/export route targets per address family.

Request:

```json
{"operation": "get_vrf_detail", "devices": ["123.123.31.31"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.31.31",
      "operation": "get_vrf_detail",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "vrfs": [
          {
            "name": "VRF1",
            "route_distinguisher": "200:1",
            "interfaces": [
              "GigabitEthernet0/0/0/1",
              "GigabitEthernet0/0/0/0.415"
            ],
            "families": [
              {
                "afi": "ipv4",
                "safi": "unicast",
                "import_route_targets": [
                  "200:1",
                  "200:2"
                ],
                "export_route_targets": [
                  "200:1"
                ]
              },
              {
                "afi": "ipv6",
                "safi": "unicast",
                "import_route_targets": [
                  "200:1",
                  "200:2"
                ],
                "export_route_targets": [
                  "200:1"
                ]
              }
            ]
          },
          {
            "name": "VRF2",
            "route_distinguisher": "200:2",
            "interfaces": [
              "GigabitEthernet0/0/0/2"
            ],
            "families": [
              {
                "afi": "ipv4",
                "safi": "unicast",
                "import_route_targets": [
                  "200:2"
                ],
                "export_route_targets": [
                  "200:2"
                ]
              },
              {
                "afi": "ipv6",
                "safi": "unicast",
                "import_route_targets": [
                  "200:2"
                ],
                "export_route_targets": [
                  "200:2"
                ]
              }
            ]
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_bgp_summary

Platforms: IOS XR. BGP sessions per address family, all instances.

Request:

```json
{"operation": "get_bgp_summary", "devices": ["123.123.100.100"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.100.100",
      "operation": "get_bgp_summary",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "address_families": [
          {
            "address_family": "vpnv4 unicast",
            "router_id": "10.4.1.1",
            "local_as": 100,
            "neighbors": [
              {
                "neighbor": "10.16.2.2",
                "remote_as": 100,
                "messages_received": 59,
                "messages_sent": 56,
                "up_down": "00:50:38",
                "state_or_prefixes_received": "10"
              },
              {
                "neighbor": "10.36.3.3",
                "remote_as": 100,
                "messages_received": 68,
                "messages_sent": 58,
                "up_down": "00:47:11",
                "state_or_prefixes_received": "10"
              }
            ]
          },
          {
            "address_family": "vpnv6 unicast",
            "router_id": "10.4.1.1",
            "local_as": 100,
            "neighbors": [
              {
                "neighbor": "10.16.2.2",
                "remote_as": 100,
                "messages_received": 59,
                "messages_sent": 56,
                "up_down": "00:50:38",
                "state_or_prefixes_received": "10"
              },
              {
                "neighbor": "10.36.3.3",
                "remote_as": 100,
                "messages_received": 68,
                "messages_sent": 58,
                "up_down": "00:47:11",
                "state_or_prefixes_received": "10"
              }
            ]
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_bgp_neighbor_detail

Platforms: IOS XR. Per-neighbor state, timers and message counters.

Request:

```json
{"operation": "get_bgp_neighbor_detail", "devices": ["123.123.100.100"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.100.100",
      "operation": "get_bgp_neighbor_detail",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "neighbors": [
          {
            "neighbor": "10.4.1.1",
            "remote_as": 65000,
            "local_as": 65000,
            "remote_router_id": "10.4.1.1",
            "state": "Established",
            "up_time": "1w1d",
            "hold_time_sec": 180,
            "keepalive_interval_sec": 60,
            "messages_received": 44766,
            "messages_sent": 40667
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_isis_neighbors

Platforms: IOS XR. IS-IS adjacencies.

Request:

```json
{"operation": "get_isis_neighbors", "devices": ["123.123.200.200"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.200.200",
      "operation": "get_isis_neighbors",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "instance": "test",
        "neighbors": [
          {
            "system_id": "R1_xe",
            "interface": "Gi0/0/0/0.115",
            "snpa": "fa16.3eff.4f49",
            "state": "up",
            "holdtime_sec": 24,
            "circuit_type": "l1l2"
          },
          {
            "system_id": "R3_nx",
            "interface": "Gi0/0/0/1.115",
            "snpa": "5e00.40ff.0209",
            "state": "up",
            "holdtime_sec": 25,
            "circuit_type": "l1l2"
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_isis_interface

Platforms: IOS XR. Per-interface IS-IS state; adjacency count and metric are kept per level.

Request:

```json
{"operation": "get_isis_interface", "devices": ["123.123.200.200"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.200.200",
      "operation": "get_isis_interface",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "interfaces": [
          {
            "interface": "Loopback0",
            "state": "enabled",
            "circuit_type": "level-1-2",
            "media_type": "Loop",
            "adjacency_count_l1": 0,
            "adjacency_count_l2": 0,
            "metric_l1": 10,
            "metric_l2": 10
          },
          {
            "interface": "GigabitEthernet0/0/0/0",
            "state": "enabled",
            "circuit_type": "level-1-2",
            "media_type": "LAN",
            "adjacency_count_l1": 0,
            "adjacency_count_l2": 1,
            "metric_l1": 10,
            "metric_l2": 10
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_isis_database

Platforms: IOS XR. LSP summary per level (LSP ID, sequence number, checksum, remaining lifetime, ATT/P/OL bits).

Request:

```json
{"operation": "get_isis_database", "devices": ["123.123.200.200"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.200.200",
      "operation": "get_isis_database",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "instance": "test",
        "levels": [
          {
            "level": "Level-1",
            "lsps": [
              {
                "lsp_id": "R3.00-00",
                "own_lsp": true,
                "sequence_number": "0x0000000d",
                "checksum": "0x0476",
                "holdtime_sec": 578,
                "att_p_ol": "1/0/0"
              },
              {
                "lsp_id": "R3.03-00",
                "own_lsp": false,
                "sequence_number": "0x00000007",
                "checksum": "0x8145",
                "holdtime_sec": 988,
                "att_p_ol": "0/0/0"
              }
            ]
          },
          {
            "level": "Level-2",
            "lsps": [
              {
                "lsp_id": "R2.00-00",
                "own_lsp": false,
                "sequence_number": "0x00000009",
                "checksum": "0x5188",
                "holdtime_sec": 1082,
                "att_p_ol": "0/0/0"
              },
              {
                "lsp_id": "R3.00-00",
                "own_lsp": true,
                "sequence_number": "0x00000011",
                "checksum": "0x4c4c",
                "holdtime_sec": 979,
                "att_p_ol": "0/0/0"
              }
            ]
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_mpls_forwarding

Platforms: IOS XR. MPLS label forwarding table.

Request:

```json
{"operation": "get_mpls_forwarding", "devices": ["123.123.31.31"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.31.31",
      "operation": "get_mpls_forwarding",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "entries": [
          {
            "local_label": "16001",
            "outgoing_label": "Pop",
            "prefix_or_id": "SR Pfx (idx 1)",
            "outgoing_interface": "Gi0/0/0/0",
            "next_hop": "10.1.3.1",
            "bytes_switched": 0
          },
          {
            "local_label": "16002",
            "outgoing_label": "16002",
            "prefix_or_id": "SR Pfx (idx 2)",
            "outgoing_interface": "Gi0/0/0/0",
            "next_hop": "10.1.3.1",
            "bytes_switched": 0
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## get_ldp_neighbors

Platforms: IOS XR. LDP sessions.

Request:

```json
{"operation": "get_ldp_neighbors", "devices": ["123.123.31.31"], "arguments": {}}
```

Response:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.31.31",
      "operation": "get_ldp_neighbors",
      "platform": "iosxr",
      "status": "success",
      "data": {
        "neighbors": [
          {
            "peer_ldp_identifier": "192.168.70.6:0",
            "state": "Oper",
            "up_time": "00:02:44",
            "session_holdtime_sec": 180,
            "messages_sent": 851,
            "messages_received": 232
          }
        ]
      },
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture"
    }
  ]
}
```

## Errors

Unsupported platform/operation pair (IOS XR has no `get_route`):

```json
{
  "request_id": "",
  "results": [
    {
      "device": "123.123.31.31",
      "operation": "get_route",
      "platform": "iosxr",
      "status": "error",
      "data": null,
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "fixture",
      "error": {
        "code": "unsupported_operation",
        "message": "operation is not supported by platform"
      }
    }
  ]
}
```

Device missing from the inventory:

```json
{
  "request_id": "",
  "results": [
    {
      "device": "no-such-device",
      "operation": "get_ospf_neighbors",
      "platform": "unknown",
      "status": "error",
      "data": null,
      "duration_ms": 0,
      "unsupported_fields": [],
      "data_source": "unknown",
      "error": {
        "code": "device_not_found",
        "message": "device not found"
      }
    }
  ]
}
```
