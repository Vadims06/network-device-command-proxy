# Provenance

Captured `show` command output copied from `CiscoTestAutomation/genieparser`
(Apache License 2.0), `src/genie/libs/parser/iosxr/tests/`. Only the raw
device output is copied here, never Genie's parser code or its stored
expected-result dicts - those are unused weight, since each oracle test
(`tests/test_*_parser_genie_oracle.py`) re-parses this same raw text with
the installed `genie` package at test time and compares live, rather than
reading a pre-computed file. Genie stays a test oracle, not a runtime
dependency (see `docs/rsvp-parsing.md`). PyPI's `genie` package does not
ship these `.txt` files at all - fetched from the GitHub source tree.

| File | Upstream source | What it gives |
|---|---|---|
| `show_rsvp_session_detail_headend.txt` | `ShowRSVPSessionDetail/cli/equal/golden_output_1_output.txt` | one head-end session: `OutLabel`, `FRR OutLabel` naming its bypass, full Resv-side record route |
| `show_rsvp_session_detail_egress_multi.txt` | `ShowRSVPSessionDetail/cli/equal/golden_output_2_output.txt` | one device, 5 sessions, all egress on this device, including `NHOP_*`/`NNHOP_*` backup tunnels |
| `show_vrf_all_detail.txt` | `ShowVrfAllDetail/cli/equal/golden_output_1_output.txt` | `show vrf all detail`, two VRFs with IPv4/IPv6 address families and route targets |
| `show_bgp_instance_summary.txt` | `ShowBgpInstanceSummary/cli/equal/golden_output1_output.txt` | `show bgp instance all all all summary`, two address families (VPNv4/VPNv6), two neighbors each |
| `show_bgp_instance_neighbors_detail.txt` | `ShowBgpInstanceNeighborsDetail/cli/equal/golden_output1_output.txt` | `show bgp instance all all all neighbors detail`, one established iBGP session |
| `show_isis_neighbors.txt` | `ShowIsisNeighbors/cli/equal/golden_output_1_output.txt` | `show isis neighbors`, two L1L2 adjacencies |
| `show_isis_interface.txt` | `ShowIsisInterface/cli/equal/golden_output_1_output.txt` | `show isis interface`, six interfaces including a TE tunnel, with differing per-level adjacency counts |
| `show_isis_database_detail.txt` | `ShowIsisDatabaseDetail/cli/equal/golden_output_1_output.txt` | `show isis database detail`, separate Level-1 and Level-2 sections, 11 LSPs each |
| `show_mpls_forwarding.txt` | `ShowMplsForwarding/cli/equal/golden_output_1_output.txt` | `show mpls forwarding`, 12 label entries mixing `Pop` and swap outgoing labels |
| `show_mpls_ldp_neighbor_detail.txt` | `ShowMplsLdpNeighborDetail/cli/equal/golden_output_1_output.txt` | `show mpls ldp neighbor detail`, one peer with discovery sources and bound addresses |
