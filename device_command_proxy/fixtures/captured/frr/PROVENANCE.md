# Provenance

Raw output of `vtysh -c '<command>'` captured on FRRouting 10.8 routers of a
containerlab lab running OSPF (areas 0.0.0.0 and 0.0.0.1), one directory per
router. Only whitespace was normalised (JSON re-indented); no value was edited.

Each demo device answers the seven commands below, with the interface and
prefix arguments shown; any other argument returns `fixture_not_found`.

| Device | Interface | Prefix |
|---|---|---|
| `123.10.10.10` | `eth1` | `123.30.30.30/32` |
| `123.30.30.30` | `eth1` | `123.14.14.14/32` |
| `123.14.14.14` | `eth1` | `123.30.30.30/32` |
