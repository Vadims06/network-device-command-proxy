# Provenance

Captured `show rsvp session detail` output and Genie's parsed expectation for
it, copied from `CiscoTestAutomation/genieparser` (Apache License 2.0):
`src/genie/libs/parser/iosxr/tests/ShowRSVPSessionDetail/cli/equal/`.

Only the captured device output and Genie's expected-result dicts are copied
here, never Genie's parser code. Genie stays a test oracle, not a runtime
dependency (see `docs/rsvp-lsp-schema-freeze.md`).

| File | Upstream source | What it gives |
|---|---|---|
| `show_rsvp_session_detail_headend.txt` | `golden_output_1_output.txt` | one head-end session: `OutLabel`, `FRR OutLabel` naming its bypass, full Resv-side record route |
| `show_rsvp_session_detail_headend_genie_expected.py` | `golden_output_1_expected.py` | Genie's parsed result for the same input |
| `show_rsvp_session_detail_egress_multi.txt` | `golden_output_2_output.txt` | one device, 5 sessions, all egress on this device, including `NHOP_*`/`NNHOP_*` backup tunnels |
| `show_rsvp_session_detail_egress_multi_genie_expected.py` | `golden_output_2_expected.py` | Genie's parsed result for the same input |
| `show_vrf_all_detail.txt` | `ShowVrfAllDetail/cli/equal/golden_output_1_output.txt` | `show vrf all detail`, two VRFs with IPv4/IPv6 address families and route targets |
| `show_vrf_all_detail_genie_expected.py` | `ShowVrfAllDetail/cli/equal/golden_output_1_expected.py` | Genie's parsed result for the same input |
