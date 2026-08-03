# device-command-proxy

Authenticated, read-only REST access to live network-device state for AI agents
and automation tools. Callers select a named operation; they never send a raw
CLI command or receive device credentials.

## Docker quick start

Copy [`.env.example`](.env.example) to `.env`, fill in one inventory mode and
one credential mode, then run:

```bash
docker compose up --build
```

The committed compose file mounts `inventory.json` and a named runtime volume.
The runtime volume can store SSH `known_hosts` and temporary private keys. Do not
bind-mount a host directory over `/app/runtime`.

For Vault credentials, also mount `profile-paths.json` and set its container
path in `.env`:

```yaml
volumes:
  - ./profile-paths.json:/etc/execution-proxy/profile-paths.json:ro
```

```env
STATIC_INVENTORY_PATH=/etc/execution-proxy/inventory.json
PROFILE_PATHS_FILE=/etc/execution-proxy/profile-paths.json
#SSH_KNOWN_HOSTS_FILE=/app/runtime/known_hosts
```

Bind the service to loopback unless TLS is terminated by a trusted proxy. The
bearer token is sent in the HTTP header.

## Local quick start

Requirements: Python 3.12+, `openssh-client`, reachable devices, and either a
static inventory plus environment credentials or NetBox plus Vault credentials.

```bash
sudo apt-get install -y openssh-client
python3.12 -m venv venv
venv/bin/pip install -e .
mkdir -p runtime
export SSH_KNOWN_HOSTS_FILE="$PWD/runtime/known_hosts"
export EXECUTION_PROXY_TOKEN="$(venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export STATIC_INVENTORY_PATH="$PWD/inventory.json"
export DEVICE_USERNAME=diag
export DEVICE_PASSWORD=replace-with-device-password
venv/bin/uvicorn device_command_proxy.main:app --host 127.0.0.1 --port 8080
```

Copy [`inventory.example.json`](inventory.example.json) to `inventory.json`:

```json
{
  "router1": {
    "host": "192.0.2.11",
    "platform": "frr"
  }
}
```

Check the service and execute an operation:

```bash
curl -s http://localhost:8080/health
curl -s -X POST localhost:8199/v1/execute \
  -H "Authorization: Bearer $EXECUTION_PROXY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"get_route","devices":["r10"],"arguments":{"prefix":"123.30.30.30/32"}}'
```
Output
```json
{"request_id":"","results":[{"device":"r10","operation":"get_route","platform":"frr","status":"success","data":{"prefix":"123.30.30.30/32","matched_prefix":"123.30.30.30/32","found":true,"routes":[{"protocol":"ospf","selected":true,"distance":110,"metric":1,"next_hops":[{"address":"10.1.30.2","interface":"eth5","active":true}]}]},"duration_ms":273,"unsupported_fields":[]}]}
```

The proxy connects directly to the device CLI. On FRR, the SSH user must be
able to enter `vtysh`; on Junos, use a read-only login class.

## Configuration

`.env` is not read automatically by a local process. Export variables or use
`set -a; . ./.env; set +a`. Docker loads it with `env_file`.

### Always required

| Variable | Purpose |
|---|---|
| `EXECUTION_PROXY_TOKEN` | Bearer token required by `/v1/execute` |
| `SSH_KNOWN_HOSTS_FILE` | Optional persistent SSH host-key file and fingerprint pinning |

Generate `EXECUTION_PROXY_TOKEN` locally; no provider issues it. Configure the
same secret in the agent or MCP client that calls the proxy and keep it out of
source control and logs. For example:

```bash
python3.12 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

`SSH_PRIVATE_KEY_DIRECTORY` is additionally required when private-key
authentication is used. The directory must be writable by the service user.

### Inventory: choose one

| Variable | Purpose |
|---|---|
| `STATIC_INVENTORY_PATH` | JSON inventory; disables NetBox |
| `NETBOX_URL` | NetBox base URL |
| `NETBOX_TOKEN` | NetBox read token |

Static inventory fields:

| Field | Required | Meaning |
|---|---|---|
| `host` | yes | Device IP address |
| `port` | no | SSH port, default `22` |
| `platform` | yes | `frr` or `junos` |
| `credential_profile` | Vault only | Logical Vault profile name |
Without static inventory, NetBox must provide `primary_ip4`, `ssh_port`,
`platform.slug`, `credential_profile`, and the device interfaces.

### Credentials: choose one

#### Environment credentials

Setting `DEVICE_USERNAME` selects this mode. Exactly one authentication method
is required:

| Variable | Purpose |
|---|---|
| `DEVICE_USERNAME` | SSH username shared by all devices |
| `DEVICE_PASSWORD` | Password authentication |
| `DEVICE_PRIVATE_KEY_FILE` | OpenSSH private-key file |
| `DEVICE_PRIVATE_KEY_PASSPHRASE` | Optional encrypted-key passphrase |
| `DEVICE_SSH_CERTIFICATE_FILE` | Optional OpenSSH user certificate |

This mode is suitable for a lab. Production deployments should use Vault so a
single process environment does not contain credentials for every device.

#### Vault over HTTP(S)

Leave `DEVICE_USERNAME` unset and set:

| Variable | Purpose |
|---|---|
| `VAULT_ADDR` | Vault URL |
| `VAULT_TOKEN` | Token with read access to the KV v2 paths |
| `VAULT_KV_MOUNT` | KV v2 mount, default `secret` |
| `PROFILE_PATHS_FILE` | Maps inventory profile names to Vault paths |

Example profile mapping:

```json
{
  "prod-frr-readonly": "network/prod/frr-readonly",
  "prod-junos-readonly": "network/prod/junos-readonly"
}
```

The proxy reads the corresponding KV v2 path under
`<VAULT_KV_MOUNT>/data/<path>`. The Vault policy therefore needs the `data/`
segment, for example:

```hcl
path "secret/data/network/prod/*" {
  capabilities = ["read"]
}
```

#### Vault Proxy Unix socket

Leave both `DEVICE_USERNAME` and `VAULT_ADDR` unset. The default socket is
`/run/vault-proxy/vault.sock`; override it with `VAULT_PROXY_SOCKET_PATH` and
mount the socket into the container.

If `VAULT_ADDR` is set, it takes priority over the Unix socket.

## API

`GET /health` is unauthenticated and returns `{"status":"ok"}`.

`POST /v1/execute` requires:

```http
Authorization: Bearer <EXECUTION_PROXY_TOKEN>
Content-Type: application/json
```

```json
{
  "operation": "get_route",
  "devices": ["router1"],
  "arguments": {"prefix": "10.0.0.0/24"},
  "request_id": "optional-id"
}
```

Arguments belong in `arguments`, not at the top level. The response is `200`
for a well-formed batch; per-device failures are returned in `results[].error`.
Unknown operations and malformed requests are `400`, a wrong token is `401`,
and schema validation failures are `422`.

To see the current list of supported operations and their arguments, open the
deployed service at `/docs` (interactive Swagger UI) or fetch `/openapi.json`
(machine-readable OpenAPI). These endpoints do not reveal device data and do
not need a token.

### Operations

| Operation | Arguments | Returns |
|---|---|---|
| `get_ospf_neighbors` | none | OSPF neighbor states |
| `get_ospf_neighbor_detail` | none | Neighbors plus area and state-change count |
| `get_ospf_interfaces` | none | All OSPF interface states |
| `get_ospf_interface` | `interface` | OSPF state for one interface |
| `get_interface_status` | `interface` | Admin/oper state, addresses, MTU, speed |
| `get_ospf_status` | none | Router ID and area counters |
| `get_route` | `prefix` | Matching routes and next hops |

The Pydantic response models are the public contract. Fields unavailable on a
platform are `null` and listed in `unsupported_fields`.

### live smoke test

Check live OSPF neighbors with:

```bash
curl -s -X POST localhost:8199/v1/execute \
  -H "Authorization: Bearer $EXECUTION_PROXY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"operation":"get_ospf_neighbors","devices":["r10"]}'
```

```json
{"request_id":"","results":[{"device":"r10","operation":"get_ospf_neighbors","platform":"frr","status":"success","data":{"instance":1,"neighbors":[{"router_id":"123.123.100.100","adjacency_state":"full","state_raw":"full/-","role":"dr_other","interface":"eth1","peer_address":"123.1.1.100","dead_time_ms":30510},{"router_id":"123.123.100.100","adjacency_state":"full","state_raw":"full/-","role":"dr_other","interface":"eth2","peer_address":"10.10.100.2","dead_time_ms":30510},{"router_id":"123.123.101.101","adjacency_state":"full","state_raw":"full/-","role":"dr_other","interface":"eth3","peer_address":"10.10.101.2","dead_time_ms":31039},{"router_id":"123.11.11.11","adjacency_state":"full","state_raw":"full/-","role":"dr_other","interface":"eth4","peer_address":"10.10.11.2","dead_time_ms":30510},{"router_id":"123.30.30.30","adjacency_state":"full","state_raw":"full/dr","role":"dr","interface":"eth5","peer_address":"10.1.30.2","dead_time_ms":30778}]},"duration_ms":271,"unsupported_fields":[]}]}
```

The normalized response uses lowercase values for protocol, state, role and
other enum fields. Device names, interface names, addresses and router IDs are
returned as supplied by the device and are not case-normalized.

### Error codes

| Code | Meaning |
|---|---|
| `device_unreachable` | SSH, authentication, or command failure |
| `invalid_request` | Invalid operation arguments, often an unlisted interface |
| `unsupported_operation` | Driver does not implement the operation |
| `device_not_found` | Device is absent from inventory |
| `unsupported_platform` | No driver for the platform |
| `credential_unavailable` | Credential source returned no usable credentials |
| `deadline_exceeded` | Device exceeded the 30-second request deadline |
| `queue_full` | Service is at capacity |
| `output_too_large` | Device output exceeded 1 MB |
| `inventory_unavailable` | NetBox did not respond |
| `internal_error` | Driver or parsing failure; details are in logs |

Callers should branch on `error.code`, not on the human-readable message.
For `device_unreachable`, inspect the warning log: the API deliberately keeps
the public error code neutral.

## SSH host keys

`SSH_KNOWN_HOSTS_FILE` is optional. If it is unset, host-key verification is
disabled to simplify lab and first-run deployments. This is less secure because
the connection is not protected against a man-in-the-middle device key.

When it is set, `ssh-keyscan` adds the device host key on first contact and
existing entries are checked strictly. If a rebuilt device legitimately has a
new key, remove only that device's entry:

```bash
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R 192.0.2.11
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R '[192.0.2.11]:2222'
```

## Limits and logs

- 20 devices per request, executed concurrently.
- 100 queued requests.
- 30-second request deadline.
- 1 MB maximum output per device.

The proxy writes structured audit records to stdout with device, operation,
filtered arguments, platform, duration, status, and error code. It never logs
passwords, private keys, Vault paths, or raw device output. `LOG_LEVEL` defaults
to `INFO`.

## Device requirements

Each device must accept the configured SSH user directly into its CLI. The
proxy does not run a separate `enable` or `vtysh` step.

For FRR, a typical user has the `vtysh` shell and membership in `frrvty`:

```bash
useradd -m diag
usermod -aG frrvty diag
usermod -s /usr/bin/vtysh diag
```

On Junos, use a read-only login class.

## Development

The agent uses [device-command-mcp](https://github.com/Vadims06/device-command-mcp)
as its MCP-facing adapter. The MCP server maps each tool to one operation here;
it owns MCP authentication, while this proxy owns inventory, credentials, SSH,
validation and vendor normalization. Read both READMEs when changing the
cross-repository contract.

```bash
venv/bin/pip install -e ".[test]"
venv/bin/pytest tests -q
```

When adding an operation, update the operation registry, shared response model,
drivers, captured-output tests, and OpenAPI conformance tests. Never add a raw
CLI command argument.

## License

See [LICENSE](LICENSE).
