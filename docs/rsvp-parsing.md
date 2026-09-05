# RSVP-TE session parsing: neutral schema notes

How a text `show`-style RSVP-TE session command maps onto the neutral
`RsvpLspInventory` / `RsvpSession` schema in `schemas.py`. Written before the
first parser, kept as the reference every later platform is held to.

First platform: IOS XR (`show rsvp session detail`). Fixtures and the
independent oracle used to pin the mapping down: `tests/fixtures/cisco_iosxr/`
(captured device output plus the `genieparser` expected dicts, Apache-2.0 -
see `PROVENANCE.md`; Genie is a test oracle, never a runtime dependency).

## Field-by-field

| Device field | Neutral model field | Notes |
|---|---|---|
| session `Addr` | `destination` | session's tail-end IP; equals local router-id when this device is egress |
| `TunID` | `tunnel_id` | opaque pass-through, cross-reference only |
| `ExtID` | `head_end` | the head-end router-id; identity uses this |
| `LSPId` | `lsp_id` | opaque pass-through |
| `Tunnel Name` | `tunnel_name` | local to the head-end, not globally unique |
| Path `InLabel` | `in_label` | `{interface, label}`; `"No intf"/"No label"` on the tail-end |
| Path `Incoming Address` | `incoming_address` | `"Unknown"` on the head-end |
| Path `Explicit Route` | `explicit_route` | list of `{path_status: strict\|loose, route_address}` |
| Path `Record Route` | *(dropped)* | upstream (Path-side) record route; the Resv-side one carries the protection flags and is what `RsvpRecordRouteHop` models |
| Path `Tspec` | `tspec` | requested reservation; see Bandwidth below |
| Resv `OutLabel` | `out_label` | `{interface, label}` |
| Resv `FRR OutLabel` | `frr_out_label` | `{interface, label}`; interface names the bypass tunnel protecting this session |
| Resv `Record Route` | `record_route` | list of `RsvpRecordRouteHop`, see Record route below |
| Resv `Fspec` | `fspec` | signaled reservation; see Bandwidth below |

RSVP soft-state counters (`PSBs`/`RSBs`/`Requests`) are not carried - no
bearing on tunnel identity or protection state.

## Record route: flat alternating list -> paired hops

The device emits address entries and label entries as separate indexed items,
each with its own flags (address, label, address, label, ...).
`RsvpRecordRouteHop` models one *hop* as address + outgoing label + decoded
flags in a single object. Pairing rule, left to right over the Resv-side
record route:

- An address entry starts a new hop: `address` = its address, `flags` decoded
  from that entry's flags (see Protection state below).
- Pair each label entry with the address entry immediately before it, as that
  hop's `label_out` on the segment toward the next hop.
- A record route with no address/label entries yields an empty list, never a
  placeholder hop.

## Protection state: record-route flags, not named fields

Per RFC 3209 the address-flags byte carries, low to high bit: local protection
available, local protection in use, bandwidth protection, node protection.
Only those four low bits are decoded, into `RsvpRecordRouteFlags`. Vendor
extensions in higher bits (e.g. the IOS XR `0x20` node-id) have no independent
oracle and are not mapped - the raw byte is preserved in `flags_raw`.

When `FRR OutLabel` is present it names the bypass directly - treat that as the
primary "this session is FRR-protected" signal and the per-hop flags as
corroborating detail.

## Identity fields

`head_end` (from `ExtID`) plus `tunnel_name` is the tunnel identity.
`tunnel_id`/`lsp_id` are opaque pass-through, kept on the model only for
cross-referencing against the router's own CLI - never used for identity or
comparison.

## Bandwidth: unverified unit

`tspec`/`fspec` average rate is the candidate bandwidth field. Every captured
sample shows `avg rate=0` for every session - **no available sample proves the
unit** (kbps vs bits/sec). The field is published as the Tspec/Fspec average
rate with its unit recorded as unverified in the model docstring, until a
sample with a non-zero reservation appears. A green test suite does not confirm
the unit.

## Role: derived, not read

The command carries no role field and mixes ingress/transit/egress sessions in
one response. Role is derived by the consumer that knows the queried device's
own router-id: router-id == `head_end` -> ingress, router-id == `destination`
-> egress, neither -> transit. Only ingress carries full state; egress shows
`OutLabel: No intf, No label` and an empty Resv-side record route. The proxy
`RsvpSession` model therefore has no `role` field - it does not know the
device's router-id - and this is stated in its docstring.
