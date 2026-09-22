# network-device-command-proxy

Authenticated, read-only REST access to live network-device state for AI agents
and automation tools. A caller selects a named operation such as
`get_ospf_neighbors`; it never sends a raw CLI command and never receives device
credentials. The proxy runs one approved `show` command over SSH and returns a
vendor-neutral, typed JSON result.

```
agent / script ──HTTP──▶ network-device-command-proxy ──SSH──▶ router
                          (allow-listed operations,           (one read-only
                           inventory, credentials,             show command)
                           parsing to a neutral model)
```

For LLM agents use the companion MCP server,
[network-device-command-mcp](https://github.com/Vadims06/network-device-command-mcp):
it exposes each operation below as an MCP tool.

## What is supported

Platforms: **FRR**, **Junos**, **Cisco IOS XR**. Sixteen operations, all
read-only. A platform implements only the operations marked below; asking for
another returns `unsupported_operation` for that device.

| Operation | Arguments | FRR | Junos | IOS XR |
|---|---|:-:|:-:|:-:|
| `get_ospf_neighbors` | none | ✓ | ✓ | |
| `get_ospf_neighbor_detail` | none | ✓ | ✓ | |
| `get_ospf_interfaces` | none | ✓ | ✓ | |
| `get_ospf_interface` | `interface` | ✓ | ✓ | |
| `get_ospf_status` | none | ✓ | ✓ | |
| `get_interface_status` | `interface` | ✓ | ✓ | |
| `get_route` | `prefix` | ✓ | ✓ | |
| `get_rsvp_lsps` | none | | | ✓ |
| `get_vrf_detail` | none | | | ✓ |
| `get_bgp_summary` | none | | | ✓ |
| `get_bgp_neighbor_detail` | none | | | ✓ |
| `get_isis_neighbors` | none | | | ✓ |
| `get_isis_interface` | none | | | ✓ |
| `get_isis_database` | none | | | ✓ |
| `get_mpls_forwarding` | none | | | ✓ |
| `get_ldp_neighbors` | none | | | ✓ |

### Device commands behind each operation

| Operation | FRR | Junos | IOS XR |
|---|---|---|---|
| `get_ospf_neighbors` | `show ip ospf neighbor json` | `show ospf neighbor \| display json` | |
| `get_ospf_neighbor_detail` | `show ip ospf neighbor detail json` | `show ospf neighbor detail \| display json` | |
| `get_ospf_interfaces` | `show ip ospf interface json` | `show ospf interface detail \| display json` | |
| `get_ospf_interface` | `show ip ospf interface <interface> json` | `show ospf interface <interface> detail \| display json` | |
| `get_ospf_status` | `show ip ospf json` | `show ospf overview \| display json` | |
| `get_interface_status` | `show interface <interface> json` | `show interfaces <interface> \| display json` | |
| `get_route` | `show ip route <prefix> json` | `show route <prefix> \| display json` | |
| `get_rsvp_lsps` | | | `show rsvp session detail` |
| `get_vrf_detail` | | | `show vrf all detail` |
| `get_bgp_summary` | | | `show bgp instance all all all summary` |
| `get_bgp_neighbor_detail` | | | `show bgp instance all all all neighbors detail` |
| `get_isis_neighbors` | | | `show isis neighbors` |
| `get_isis_interface` | | | `show isis interface` |
| `get_isis_database` | | | `show isis database detail` |
| `get_mpls_forwarding` | | | `show mpls forwarding` |
| `get_ldp_neighbors` | | | `show mpls ldp neighbor detail` |

`interface` accepts letters, digits and `_ . : / -`; `prefix` must parse as an
IP network. Anything else is rejected with `invalid_request` before a device is
contacted.

### What comes back

Every device in a request gets one result:

```json
{
  "device": "frr1",
  "operation": "get_ospf_neighbors",
  "platform": "frr",
  "status": "success",
  "data": {
    "instance": 1,
    "neighbors": [
      {"router_id": "10.10.10.3", "adjacency_state": "full", "state_raw": "full/dr",
       "role": "dr", "interface": "eth1", "peer_address": "192.168.13.3",
       "dead_time_ms": 39570}
    ]
  },
  "duration_ms": 2,
  "unsupported_fields": [],
  "data_source": "live"
}
```

- `status` is `success` or `error`; on error `data` is `null` and `error` holds
  `{code, message}` (see [error codes](#error-codes)).
- `unsupported_fields` lists fields this vendor can never report. Such a field is
  `null`, never omitted and never invented. Junos, for example, has no OSPF
  `instance` or neighbor `role`.
- `data_source` is `live` for a real device and `fixture` for a replayed capture
  (see [Try it without devices](#try-it-without-devices)).
- Enum-like values (protocol, adjacency state, role) are lower-case. Device
  names, interfaces, addresses and router IDs are returned as the device
  printed them.

**[docs/operations.md](docs/operations.md) shows the request and a real response
for every operation.** A running service also serves the full machine-readable
schema at `/openapi.json` and an interactive page at `/docs`, both without a
token and without device data.

## Try it without devices

Devices with `"transport": "fixture"` never open SSH. The proxy replays captured
FRR and IOS XR output through the same parser a live device goes through. This
is the quickest way to check an install and to see real output for OSPF, routes,
RSVP, BGP, IS-IS, VRF, MPLS and LDP.

Requirements: Python 3.12+ and `openssh-client` (the service checks for the
`ssh` binary at startup).

```bash
python3.12 -m venv venv
venv/bin/pip install -e .

cat > inventory.demo.json <<'EOF'
{
  "123.10.10.10":    {"host": "123.10.10.10",    "platform": "frr",   "transport": "fixture"},
  "123.30.30.30":    {"host": "123.30.30.30",    "platform": "frr",   "transport": "fixture"},
  "123.14.14.14":    {"host": "123.14.14.14",    "platform": "frr",   "transport": "fixture"},
  "123.11.11.11":    {"host": "123.11.11.11",    "platform": "frr",   "transport": "fixture"},
  "123.13.13.13":    {"host": "123.13.13.13",    "platform": "frr",   "transport": "fixture"},
  "123.15.15.15":    {"host": "123.15.15.15",    "platform": "frr",   "transport": "fixture"},
  "123.31.31.31":    {"host": "123.31.31.31",    "platform": "frr",   "transport": "fixture"},
  "123.123.101.101": {"host": "123.123.101.101", "platform": "frr",   "transport": "fixture"},
  "123.123.110.110": {"host": "123.123.110.110", "platform": "frr",   "transport": "fixture"},
  "123.123.111.111": {"host": "123.123.111.111", "platform": "frr",   "transport": "fixture"},
  "123.123.30.30":   {"host": "123.123.30.30",   "platform": "frr",   "transport": "fixture"},
  "123.123.31.31":   {"host": "123.123.31.31",   "platform": "iosxr", "transport": "fixture"},
  "123.123.100.100": {"host": "123.123.100.100", "platform": "iosxr", "transport": "fixture"},
  "123.123.200.200": {"host": "123.123.200.200", "platform": "iosxr", "transport": "fixture"}
}
EOF

export EXECUTION_PROXY_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export STATIC_INVENTORY_PATH="$PWD/inventory.demo.json"
export DEVICE_USERNAME=demo DEVICE_PASSWORD=unused   # required by startup, never used by fixtures
venv/bin/uvicorn device_command_proxy.main:app --host 127.0.0.1 --port 8080
```

In a second shell:

```bash
curl -s localhost:8080/health

curl -s -X POST localhost:8080/v1/execute \
  -H "Authorization: Bearer $EXECUTION_PROXY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"get_ospf_neighbors","devices":["123.10.10.10"]}'
```

Each demo device answers only the commands it has a capture for:

| Device | Operations |
|---|---|
| `123.10.10.10`, `123.30.30.30`, `123.14.14.14`, `123.11.11.11`, `123.13.13.13`, `123.15.15.15`, `123.31.31.31`, `123.123.101.101`, `123.123.110.110`, `123.123.111.111`, `123.123.30.30` (FRR) | every FRR operation, with `interface` `eth1`; `prefix` per device, see [PROVENANCE.md](device_command_proxy/fixtures/captured/frr/PROVENANCE.md) |
| `123.123.31.31` | `get_rsvp_lsps`, `get_vrf_detail`, `get_mpls_forwarding`, `get_ldp_neighbors` |
| `123.123.100.100` | `get_bgp_summary`, `get_bgp_neighbor_detail` |
| `123.123.200.200` | `get_isis_neighbors`, `get_isis_interface`, `get_isis_database` |

Any other operation, or an argument other than the ones above, returns
`fixture_not_found`. To demo another operation, add a captured `.txt` file under `device_command_proxy/fixtures/captured/` and map
the exact command to it in `device_command_proxy/fixtures/demo/<device>.json`.

## Run against real devices

### Docker

Copy [`.env.example`](.env.example) to `.env`, fill in one inventory mode and one
credential mode, and copy [`inventory.example.json`](inventory.example.json) to
`inventory.json`. Then:

```bash
docker compose up --build
```

The compose file publishes the service on `127.0.0.1:8080`, mounts
`inventory.json` read-only and keeps a named volume at `/app/runtime` for SSH
`known_hosts` and temporary private keys. Do not bind-mount a host directory
over `/app/runtime`. Terminate TLS in a trusted reverse proxy before exposing
the port: the bearer token travels in an HTTP header.

For Vault credentials, also mount `profile-paths.json` (copy from
[`profile-paths.example.json`](profile-paths.example.json)):

```yaml
volumes:
  - ./profile-paths.json:/etc/execution-proxy/profile-paths.json:ro
```

```env
STATIC_INVENTORY_PATH=/etc/execution-proxy/inventory.json
PROFILE_PATHS_FILE=/etc/execution-proxy/profile-paths.json
#SSH_KNOWN_HOSTS_FILE=/app/runtime/known_hosts
```

### Local process

```bash
sudo apt-get install -y openssh-client
python3.12 -m venv venv
venv/bin/pip install -e .
mkdir -p runtime
export SSH_KNOWN_HOSTS_FILE="$PWD/runtime/known_hosts"
export EXECUTION_PROXY_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export STATIC_INVENTORY_PATH="$PWD/inventory.json"
export DEVICE_USERNAME=diag
export DEVICE_PASSWORD=replace-with-device-password
venv/bin/uvicorn device_command_proxy.main:app --host 127.0.0.1 --port 8080
```

`inventory.json`:

```json
{
  "router1": {"host": "192.0.2.11", "platform": "frr"},
  "router2": {"host": "192.0.2.12", "platform": "junos"}
}
```

```bash
curl -s -X POST localhost:8080/v1/execute \
  -H "Authorization: Bearer $EXECUTION_PROXY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"get_route","devices":["router1"],"arguments":{"prefix":"10.10.10.6/32"}}'
```

### Device requirements

The SSH user must land directly in the device CLI; the proxy runs no separate
`enable` or `vtysh` step. Use a read-only account.

- **FRR:** the user's shell is `vtysh` and it is in the `frrvty` group:
  ```bash
  useradd -m diag
  usermod -aG frrvty diag
  usermod -s /usr/bin/vtysh diag
  ```
- **Junos:** a read-only login class.
- **IOS XR:** a user in the `operator` task group. No `crypto` or `root-system`
  privilege is needed.

## Configuration

`.env` is not read by a local process; export the variables or run
`set -a; . ./.env; set +a`. Docker loads it with `env_file`. A missing required
variable stops the service at startup with a message naming it.

### Always required

| Variable | Purpose |
|---|---|
| `EXECUTION_PROXY_TOKEN` | Bearer token required by `/v1/execute`. Generate it yourself and configure the same value in the client (agent or MCP server) |
| `SSH_KNOWN_HOSTS_FILE` | Optional. Persistent host-key file with strict fingerprint checking; see [SSH host keys](#ssh-host-keys) |
| `SSH_PRIVATE_KEY_DIRECTORY` | Only for private-key authentication; must be writable by the service user |

### Inventory: choose one

| Variable | Purpose |
|---|---|
| `STATIC_INVENTORY_PATH` | JSON inventory; disables NetBox |
| `NETBOX_URL`, `NETBOX_TOKEN` | NetBox base URL and read token |

Static inventory fields:

| Field | Required | Meaning |
|---|---|---|
| `host` | yes | Device IP address |
| `port` | no | SSH port, default `22` |
| `platform` | yes | `frr`, `junos` or `iosxr` |
| `credential_profile` | Vault only | Logical Vault profile name |
| `transport` | no | `ssh` (default) or `fixture` |

With NetBox, each device must provide `primary_ip4`, `ssh_port`,
`platform.slug`, `credential_profile` and its interfaces.

### Credentials: choose one

**Environment credentials** (lab use). Setting `DEVICE_USERNAME` selects this
mode. Exactly one authentication method is required:

| Variable | Purpose |
|---|---|
| `DEVICE_USERNAME` | SSH username shared by all devices |
| `DEVICE_PASSWORD` | Password authentication |
| `DEVICE_PRIVATE_KEY_FILE` | OpenSSH private-key file |
| `DEVICE_PRIVATE_KEY_PASSPHRASE` | Optional key passphrase |
| `DEVICE_SSH_CERTIFICATE_FILE` | Optional OpenSSH user certificate |

Production should use Vault so one process environment does not hold the
credentials of every device.

**Vault over HTTP(S).** Leave `DEVICE_USERNAME` unset and set:

| Variable | Purpose |
|---|---|
| `VAULT_ADDR` | Vault URL |
| `VAULT_TOKEN` | Token with read access to the KV v2 paths |
| `VAULT_KV_MOUNT` | KV v2 mount, default `secret` |
| `PROFILE_PATHS_FILE` | Maps each `credential_profile` to a Vault path |

```json
{
  "prod-frr-readonly": "network/prod/frr-readonly",
  "prod-junos-readonly": "network/prod/junos-readonly"
}
```

The proxy reads `<VAULT_KV_MOUNT>/data/<path>`, so the policy needs the `data/`
segment:

```hcl
path "secret/data/network/prod/*" {
  capabilities = ["read"]
}
```

**Vault Proxy Unix socket.** Leave both `DEVICE_USERNAME` and `VAULT_ADDR` unset.
The default socket is `/run/vault-proxy/vault.sock`; override it with
`VAULT_PROXY_SOCKET_PATH` and mount the socket into the container. If
`VAULT_ADDR` is set it takes priority.

## API

`GET /health` is unauthenticated and returns `{"status":"ok"}`.

`POST /v1/execute` requires `Authorization: Bearer <EXECUTION_PROXY_TOKEN>`:

```json
{
  "operation": "get_route",
  "devices": ["router1", "router2"],
  "arguments": {"prefix": "10.0.0.0/24"},
  "request_id": "optional-correlation-id"
}
```

Arguments go in `arguments`, not at the top level. A well-formed batch returns
`200` even if some devices failed; per-device failures are in `results[].error`.
Unknown operations and malformed requests return `400`, a wrong token `401`,
and a body that fails schema validation `422`.

### Error codes

Callers should branch on `error.code`, never on the message.

| Code | Meaning |
|---|---|
| `device_unreachable` | Transport failure: SSH connect or session error |
| `authentication_failed` | The device rejected the credentials |
| `command_failed` | The device was reached but the command errored or is unsupported on this release |
| `parse_error` | Output was retrieved but could not be parsed into the model |
| `invalid_request` | Invalid arguments, for example an interface name with illegal characters |
| `unsupported_operation` | The platform does not implement the operation |
| `device_not_found` | Device is not in the inventory |
| `unsupported_platform` | No driver for the platform |
| `credential_unavailable` | The credential source returned no usable credentials |
| `deadline_exceeded` | The device exceeded the 30-second request deadline |
| `queue_full` | The service is at capacity |
| `output_too_large` | Device output exceeded 1 MB |
| `inventory_unavailable` | NetBox did not respond |
| `fixture_not_found` | A fixture device has no capture for this command |
| `internal_error` | Anything else; details are in the log |

The public code stays deliberately neutral for `device_unreachable`,
`authentication_failed`, `command_failed` and `internal_error`; the service log
holds the cause. A record parsed with some fields missing is a success with
`null` values plus `unsupported_fields`, never a separate error.

## SSH host keys

If `SSH_KNOWN_HOSTS_FILE` is unset, host-key verification is disabled, which is
convenient for a lab but leaves the connection open to a man-in-the-middle. When
it is set, the device key is added with `ssh-keyscan` on first contact and
existing entries are checked strictly. If a rebuilt device legitimately has a new
key, remove only its entry:

```bash
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R 192.0.2.11
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R '[192.0.2.11]:2222'   # non-default port
```

## Limits and logs

- 20 devices per request, executed concurrently.
- 100 queued requests.
- 30-second request deadline.
- 1 MB maximum output per device.

Structured audit records go to stdout with device, operation, filtered
arguments, platform, duration, status and error code. Passwords, private keys,
Vault paths and raw device output are never logged. `LOG_LEVEL` defaults to
`INFO`.

## Development

```bash
venv/bin/pip install -e ".[test]"
venv/bin/pytest tests -q
```

`pip install -e ".[genie]"` additionally enables the cross-check tests that
compare each IOS XR text parser against an independent implementation; they are
skipped otherwise, and Genie is never a runtime dependency.

The response models are the contract:

- `operations.py` binds each operation to exactly one response model.
- `schemas.py` holds a union of per-operation result models discriminated by
  `operation`, so `data` is typed per operation, never a bare `dict`.
- `tests/test_openapi_conformance.py` ties driver output, the public model and
  the generated OpenAPI together, so the published structure cannot drift from
  what a driver returns.

Two invariants: no raw CLI argument ever reaches the API, and no field is added
to a model without a device command that reports it.

### Adding a platform

1. `operation_types.Operation`, only if the vendor brings a new operation.
2. `schemas.py`: the response model and its entry in the discriminated union.
3. `operations.py`: the `OperationSpec` binding operation to model.
4. `platforms/<vendor>/driver.py`: Scrapli driver factory, `create_adapter`, an
   adapter class with one handler per supported operation, and
   `UNSUPPORTED_FIELDS` for what the vendor cannot report.
5. `platforms/__init__.py`: register it in `PLATFORMS` and `UNSUPPORTED_FIELDS`.
6. `tests/golden_device_output.py`: captured device output for the platform.
7. This README: the two tables above and the device requirements.

`tests/test_openapi_conformance.py` picks the platform up once its output and
adapter are registered. See `platforms/iosxr/` for a complete text-parsing
example (line parsers cross-checked against an independent oracle, see
[docs/rsvp-parsing.md](docs/rsvp-parsing.md)), and [AGENTS.md](AGENTS.md) if an
AI agent is working on this repository.

The captured IOS XR outputs used as fixtures come from the Genie Parser test
suite (Apache License 2.0); see
[PROVENANCE.md](device_command_proxy/fixtures/captured/cisco_iosxr/PROVENANCE.md).

## License

Apache License 2.0, see [LICENSE](LICENSE).
