# Provenance

Raw output of `vtysh -c '<command>'` captured on FRRouting 10.8 routers of the
13-router containerlab lab running OSPF (areas 0.0.0.0 and 0.0.0.1), one
directory per router, named by its OSPF router-id. Only whitespace was
normalised (JSON re-indented) and each vtysh invocation's one-line startup
banner (unrelated `vtysh.conf` warning, not device output) was dropped; no
value was edited. `123.123.31.31` and `123.123.100.100` are excluded, those
router-ids are already IOS XR demo devices for RSVP/VRF and BGP.

Each demo device answers the eight commands below, with the interface and
prefix arguments shown; any other argument returns `fixture_not_found`.

| Device | Interface | Prefix |
|---|---|---|
| `123.10.10.10` | `eth1` | `123.30.30.30/32` |
| `123.30.30.30` | `eth1` | `123.14.14.14/32` |
| `123.14.14.14` | `eth1` | `123.30.30.30/32` |
| `123.11.11.11` | `eth1` | `123.123.100.100/32` |
| `123.13.13.13` | `eth1` | `123.123.100.100/32` |
| `123.15.15.15` | `eth1` | `123.123.100.100/32` |
| `123.31.31.31` | `eth1` | `123.123.100.100/32` |
| `123.123.101.101` | `eth1` | `123.123.100.100/32` |
| `123.123.110.110` | `eth1` | `123.123.100.100/32` |
| `123.123.111.111` | `eth1` | `123.123.100.100/32` |
| `123.123.30.30` | `eth1` | `123.123.100.100/32` |
