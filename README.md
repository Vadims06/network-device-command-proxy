# device-command-proxy

Device Command Proxy is an authenticated REST service that lets AI agents,
including a NOC assistant, obtain diagnostic data from real network devices in a
controlled, read-only way.

The agent sends a semantic request such as "get OSPF neighbors from router1".
The proxy resolves the device, validates the request, selects one fixed vendor
command, runs it over SSH, and returns a vendor-neutral response. The agent
never receives device credentials and never chooses a raw CLI command.

Every operation is an explicit allow-listed name (`get_ospf_neighbors`,
`get_route`, ...). The caller can request
"OSPF neighbors on router1" but never an arbitrary shell command.

The service is named `execution-proxy` where it runs: that is the Docker image
name, the container user, and the prefix of its runtime paths.

## What problems it solves

- **Provides live output from real devices.** a NOC assistant can answer questions
  about the current network state instead of relying only on an old snapshot,
  inventory record, or human-pasted CLI output.
- **Supports network automation tools.** An automation tool that needs current
  device output can call a semantic operation and consume the same validated
  response as an AI agent.
- **Controls what an AI agent can do.** The agent can request only an
  allow-listed read-only operation. It cannot send `configure`, `clear`,
  `reload`, or an arbitrary shell command.
- **Keeps credentials and transport details inside the service.** The agent
  receives data, not SSH passwords, private keys, Vault tokens, or device
  connection details.
- **Makes different vendors look the same.** FRR and Junos may use different
  commands and output formats, but the agent consumes one public model.
- **Contains failures.** A batch can return successful results for reachable
  devices and explicit failures for the others without losing the whole batch.

## Architecture

The request path is deliberately one-way:

```text
a NOC assistant, another AI agent, or a network automation tool
  -> authenticated HTTP request
  -> operation registry and argument validation
  -> inventory and credential lookup
  -> BatchExecutor (limits, deadlines, locks, partial failures)
  -> vendor adapter and one fixed CLI command
  -> device output parser (JSON or ordinary CLI text)
  -> shared Pydantic response model
  -> normalized JSON response
```

The caller supplies an operation name and validated arguments, never a
command. `operations.py` is the single registry: it contains every supported
operation, its argument kind, and its response model. `schemas.py` contains
the vendor-neutral public result models. `platforms/<vendor>/driver.py`
contains fixed commands and the parser for that vendor. The shared adapter
owns SSH, timeouts, output limits, and error mapping.

The parser may consume structured JSON when a device supports it or parse raw
CLI text when it does not. The input format is vendor-specific; only the
validated output model is shared.

## Requirements

- **Python 3.12 or newer** (3.11 will refuse to install the package)
- **`openssh-client`** - every device connection runs through the system `ssh`
  binary, and `ssh-keyscan` learns each device's host key on first contact
- `SSH_KNOWN_HOSTS_FILE`, a path for the persistent SSH `known_hosts` file;
  its parent must be writable when the file does not exist
- `SSH_PRIVATE_KEY_DIRECTORY`, optionally set to a writable directory for
  temporary private keys when key authentication is used
- A credential source: environment variables for a lab, or **Vault** KV v2
- Devices reachable over SSH from wherever the proxy runs

Required settings, the host-key scanner, and the known-hosts path are checked
at startup. The private-key directory is checked only when private-key
authentication is used. Whether a device actually answers SSH, and whether
Vault's token can read its secret, are only known once the first request runs.

## Quick start

The shortest path to real output from a device, with no Vault or NetBox.

First give the devices a login the proxy can use: see
[Devices themselves](#devices-themselves). Without it every request comes back
as `device_unreachable`, and the reason is only in the log.

```bash
sudo apt-get install -y openssh-client               # ssh, ssh-keyscan
mkdir -p runtime
export SSH_KNOWN_HOSTS_FILE="$PWD/runtime/known_hosts"

python3.12 -m venv venv
venv/bin/pip install -e .
```

Describe your devices in `inventory.json` (see
[`inventory.example.json`](inventory.example.json)). `host` is an IP address,
not a hostname. Public and private management addresses are supported:

```json
{
  "router1": {
    "host": "192.0.2.11",
    "platform": "frr",
    "interfaces": ["eth0", "eth1"]
  }
}
```

Then run it:

```bash
export EXECUTION_PROXY_TOKEN=replace-with-a-random-value
export STATIC_INVENTORY_PATH=./inventory.json
export DEVICE_USERNAME=diag
export DEVICE_PASSWORD=...

venv/bin/uvicorn device_command_proxy.main:app --host 127.0.0.1 --port 8080
```

```bash
curl -s localhost:8080/health

curl -s -X POST localhost:8080/v1/execute \
  -H "Authorization: Bearer $EXECUTION_PROXY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"operation": "get_ospf_neighbors", "devices": ["router1"]}'
```

`DEVICE_USERNAME` gives every device the same login, which is why it suits a
lab and not production. See [Credentials](#credentials) for Vault.

## API contract

The Pydantic models in `device_command_proxy/schemas.py` are the source of
truth for operation results. FastAPI generates the OpenAPI document from those
models at `/openapi.json` and renders it at `/docs`; neither path needs a token
or reveals device data. Runtime responses are validated against the same models
before they are returned. Tests also validate driver output against the
generated JSON Schema, so the implementation, runtime contract, and published
documentation cannot drift silently. In short:

`EXECUTION_PROXY_TOKEN` is the shared secret between the caller and the proxy.
The proxy compares the token from the `Authorization: Bearer` header before
constructing an operation or contacting inventory. Requests without the token
receive `401 Unauthorized`; it is not used for SSH authentication to devices.

```
POST /v1/execute
Authorization: Bearer <EXECUTION_PROXY_TOKEN>

{"operation": "get_ospf_neighbors", "devices": ["router1"], "request_id": "abc"}
```

```json
{
  "request_id": "abc",
  "results": [
    {
      "device": "router1",
      "operation": "get_ospf_neighbors",
      "platform": "frr",
      "status": "success",
      "duration_ms": 412,
      "unsupported_fields": [],
      "data": {
        "instance": 1,
        "neighbors": [
          {
            "router_id": "10.10.10.3",
            "adjacency_state": "FULL",
            "state_raw": "Full/DR",
            "role": "DR",
            "interface": "eth1",
            "peer_address": "192.168.13.3",
            "dead_time_ms": 39570
          }
        ]
      }
    }
  ]
}
```

The HTTP response is always `200` once the request is well-formed; per-device
failures (unreachable device, unsupported platform, ...) are reported inside
`results[].error`, not as an HTTP error. An unknown operation or a malformed
device list is a `400`, a wrong token a `401`, and a body that fails schema
validation a `422`.

`GET /health` needs no token and answers `{"status": "ok"}`.

### Why error codes exist

The OpenAPI/Pydantic schema describes the **shape** of an error. The stable
`code` describes its **meaning and next action**. An AI agent should branch on
`device_unreachable`, `unsupported_operation`, or `credential_unavailable`,
not try to interpret a human message that may change. Codes also let one batch
contain both successful and failed device results without turning every device
failure into an HTTP failure.

Every per-device failure carries one of these in `results[].error.code`. The
messages are for humans and logs; callers should branch on the code.

| Code | Means |
|---|---|
| `device_unreachable` | Connection, authentication, or the command itself failed. One neutral code on purpose; the cause is in the log at `WARNING` |
| `invalid_request` | The arguments are wrong for this device, usually an interface that is not in its inventory |
| `unsupported_operation` | The operation exists but this platform's driver does not implement it |
| `device_not_found` | The name is not in the inventory |
| `unsupported_platform` | The device's platform has no driver |
| `credential_unavailable` | Vault did not return usable credentials for the device's profile |
| `deadline_exceeded` | Still running when the 30 second request deadline elapsed |
| `queue_full` | The service is already at capacity |
| `output_too_large` | The device returned more than 1 MB |
| `inventory_unavailable` | NetBox did not answer |
| `internal_error` | A bug, or output the driver could not parse. Details are in the log only |

### Operations

| Operation | Arguments | Returns |
|---|---|---|
| `get_ospf_neighbors` | none | Neighbor state per adjacency |
| `get_ospf_neighbor_detail` | none | The above plus area and state-change count |
| `get_ospf_interfaces` | none | OSPF state of every OSPF interface |
| `get_ospf_interface` | `interface` | The same shape, for one interface. An empty list means it is not running OSPF |
| `get_interface_status` | `interface` | Admin/oper state, addresses, MTU, speed |
| `get_ospf_status` | none | Router ID and per-area counters |
| `get_route` | `prefix` | Matching routes and next hops |

Arguments go in an `arguments` object, not at the top level:

```json
{"operation": "get_route", "devices": ["router1"], "arguments": {"prefix": "10.0.0.0/24"}}
```

`get_ospf_interfaces` needs no arguments and no prior knowledge of the
interface list, which is what makes "an interface is OSPF-enabled and up but
has no neighbor" answerable in one call per device.

## Running it

The service reads its configuration from the process environment. `.env` is
**not** read automatically. Docker loads it via `--env-file`, and for a local
run either export the variables or source the file yourself:

```bash
set -a; . ./.env; set +a
```

Copy [`.env.example`](.env.example) for the full list of variables.

Bind to `127.0.0.1` unless something else terminates TLS in front of the
service: the bearer token is sent in a header, so exposing the port directly
puts it on the wire in clear text.

### Docker

The container runs as a fixed non-root user (`execution-proxy`, uid 2000), so
any file bind-mounted **from the host** must be world-readable there, or the
container cannot open it, no matter how permissive its mode looks inside the
image:

```bash
chmod 644 inventory.json profile-paths.json  # any file you bind-mount below
```

`/app/runtime` (the `known_hosts`/private-key directory) is different: use a
**named volume**, not a host bind mount. Docker populates a fresh named volume
from the image's own `/app/runtime`, which the Dockerfile already creates
owned by `execution-proxy` - a host directory bind-mounted at that path would
keep the host's ownership instead and fail the same way an unreadable file
does.

```bash
docker build -t execution-proxy .
docker run -p 127.0.0.1:8080:8080 --env-file .env \
  -v $(pwd)/inventory.json:/etc/execution-proxy/inventory.json:ro \
  -v execution-proxy-runtime:/app/runtime \
  execution-proxy
```

Or `docker compose up --build` using the committed `docker-compose.yml`,
which wires up the same two volumes plus `.env` for the no-Vault, no-NetBox
quick start above.

Publishing on `127.0.0.1` for the same reason as above. Mount the credential
profile mapping as well when credentials come from Vault:

```bash
  -v $(pwd)/profile-paths.json:/etc/execution-proxy/profile-paths.json:ro \
```

Only mount a file that exists: given a missing host path, Docker creates a
directory there, and the service then fails at startup on a file it cannot
parse.

With `.env` pointing at the **container-side** paths, not the ones on your
host:

```
STATIC_INVENTORY_PATH=/etc/execution-proxy/inventory.json
PROFILE_PATHS_FILE=/etc/execution-proxy/profile-paths.json
SSH_KNOWN_HOSTS_FILE=/app/runtime/known_hosts
```

Set `SSH_PRIVATE_KEY_DIRECTORY=/app/runtime/keys` only when the configured
devices use private-key authentication. Password-only deployments do not need
this variable and do not check the directory at startup.

The mounted runtime volume holds the SSH `known_hosts` the proxy builds on
first contact with each device. Without it every recreated container re-learns
every host key, which defeats the point of pinning them.

A device that is rebuilt gets a new host key, and the pinned one then no
longer matches: every request for it becomes `device_unreachable` until its
line is removed from `known_hosts`, after which the next request learns the
new key.

```bash
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R 192.0.2.11
ssh-keygen -f "$SSH_KNOWN_HOSTS_FILE" -R '[192.0.2.11]:2222'  # non-default port
```

If you're using the Vault Proxy Unix-socket mode, mount the socket too: add
`-v /run/vault-proxy/vault.sock:/run/vault-proxy/vault.sock` (or wherever
`VAULT_PROXY_SOCKET_PATH` points).

## Inventory: NetBox or a static file

By default the proxy resolves devices live from NetBox. To run standalone
without NetBox, set `STATIC_INVENTORY_PATH` to a JSON file instead. When
set, NetBox is not used at all.

```json
{
  "router1": {
    "host": "192.0.2.11",
    "port": 22,
    "platform": "frr",
    "credential_profile": "prod-frr-readonly",
    "interfaces": ["eth0", "eth1"]
  }
}
```

`port` defaults to `22`. `host` is an IP address, not a hostname. Public and
private management addresses are supported. `platform` must be one of the
supported platforms above, spelled in lower case (`frr`, `junos`).

`credential_profile` is required only when credentials come from Vault, and is
then cross-checked against `PROFILE_PATHS_FILE` (see
[Credential profiles](#credential-profiles)). With environment credentials one
login covers every device, so the field can be omitted. Both it and `platform`
are checked while the file loads, so a typo in either stops the service at
startup naming the device and the constraint, instead of failing later on
every request for that device.

`interfaces` defaults to `[]`, and an interface that is not listed is rejected:
**list the interfaces you intend to query, or `get_interface_status` and
`get_ospf_interface` will fail on every call.** The argument-free operations,
including `get_ospf_interfaces`, work regardless.

If `STATIC_INVENTORY_PATH` is not set, NetBox is required and the device must
have these NetBox fields populated: `primary_ip4` (used as the SSH host),
custom field `ssh_port` (defaults to `22`), `platform.slug` (`frr` or
`junos`), custom field `credential_profile`, and its interfaces (used to
validate the `interface` argument).

| Variable | Required when | Meaning |
|---|---|---|
| `STATIC_INVENTORY_PATH` | using the static file | Path to the JSON inventory above |
| `NETBOX_URL` | using NetBox (default) | NetBox base URL |
| `NETBOX_TOKEN` | using NetBox (default) | NetBox API token |

## Credentials

Two sources, checked in that order: if `DEVICE_USERNAME` is set the
environment is used, otherwise a Vault is required. Setting neither stops the
service at startup naming both options.

### From the environment

One credential set is shared by every device. That is the whole tradeoff: it
removes the need to stand up a Vault, and it means every device is reached
with the same login and the password is visible to anything that can read the
process environment. Use it for a lab or a first run.

| Variable | Required when | Meaning |
|---|---|---|
| `DEVICE_USERNAME` | using env credentials | SSH username; its presence selects this mode |
| `DEVICE_PASSWORD` | password auth | Exactly one of this or `DEVICE_PRIVATE_KEY_FILE` |
| `DEVICE_PRIVATE_KEY_FILE` | key auth | Path to an OpenSSH private key file |
| `DEVICE_PRIVATE_KEY_PASSPHRASE` | the key is encrypted | Passphrase for the key above |
Key files are read at startup, so a path that does not exist is reported then
rather than on the first request.

### From Vault

SSH credentials are read from Vault KV v2, either directly over HTTP(S) with a
token or through a local Vault Proxy Unix socket, where a sidecar has already
resolved AppRole auth and the proxy itself holds no long-lived token.

| Variable | Required when | Meaning |
|---|---|---|
| `VAULT_ADDR` | connecting directly over HTTP(S) | e.g. `https://vault.example.com:8200` |
| `VAULT_TOKEN` | connecting directly over HTTP(S) | Vault token with read access to the paths below |
| `VAULT_PROXY_SOCKET_PATH` | using a Vault Proxy socket at a non-default path | defaults to `/run/vault-proxy/vault.sock` |
| `VAULT_KV_MOUNT` | your KV v2 engine is not mounted at `secret` | defaults to `secret` |

If `VAULT_ADDR` is set, it takes priority and the Unix-socket path is not
used.

#### Setting up Vault

A dev-mode server is enough to try the Vault path. It keeps everything in
memory and starts unsealed with a single root token, so it is for local use
only:

```bash
vault server -dev -dev-root-token-id=dev-token &
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=dev-token
```

A dev server already has KV v2 mounted at `secret/`, so skip the next command
there. It would answer `path is already in use`. On any other Vault, enable
the mount first, then write one secret per credential profile:

```bash
vault secrets enable -path=secret kv-v2

vault kv put secret/network/prod/frr-readonly \
  username=diag \
  authentication_type=password \
  password=...
```

For key-based auth use `authentication_type=private_key` with `private_key`
and optionally `private_key_passphrase` instead of `password`. Configure the
corresponding authentication method on each device according to its vendor
documentation.

Outside a dev server, give the proxy a token whose policy grants read on the
secrets it uses and nothing else:

```hcl
path "secret/data/network/prod/*" {
  capabilities = ["read"]
}
```

Note the `data/` segment: KV v2 reads go to `<mount>/data/<path>`, so a policy
written without it grants nothing.

### Credential profiles

Each device's `credential_profile` (from NetBox or the static file) is a
logical name, not a Vault path. It maps to the actual KV v2 secret path
under `VAULT_KV_MOUNT`. Set `PROFILE_PATHS_FILE` to a JSON file (see
[`profile-paths.example.json`](profile-paths.example.json)):

```json
{
  "prod-frr-readonly": "network/prod/frr-readonly",
  "prod-junos-readonly": "network/prod/junos-readonly"
}
```

`prod-frr-readonly` above is then read from
`<VAULT_KV_MOUNT>/data/network/prod/frr-readonly`.

Without `PROFILE_PATHS_FILE` the proxy falls back to two built-in demo-lab
profile names, which will not match your Vault. Set it.

| Variable | Required when | Meaning |
|---|---|---|
| `PROFILE_PATHS_FILE` | credentials come from Vault | Path to the JSON mapping above |

## Logging

The proxy writes one structured audit line per executed operation, including
device, operation, arguments, platform, duration, status, and error code, to
stdout.
It never logs passwords, private keys, Vault paths, or raw device output.
`arguments` is filtered to the two keys any operation ever legitimately
takes (`interface`, `prefix`) before being written, so a caller attaching an
arbitrary extra key to a request, accidental or otherwise, cannot get it
logged verbatim, even when that request is itself rejected.

```
2026-01-01T00:00:00+0000 INFO device_command_proxy.audit {"device": "router1", "duration_ms": 412, "operation": "get_ospf_neighbors", "platform": "frr", "status": "success", ...}
```

`LOG_LEVEL` defaults to `INFO`. When a device is reported as
`device_unreachable` the API deliberately returns one neutral code, so the
underlying cause, such as a refused connection, an authentication failure, or
a timeout, appears only in the log at `WARNING`. Read it before investigating the
network.

## Devices themselves

Each device must accept SSH login as the configured user directly into its
CLI. The proxy does not perform a separate `enable` or `vtysh` step.

On FRR that means creating a user whose login shell is `vtysh`, who can reach
the daemons, and who has an authentication method configured for that device:

```bash
useradd -m diag
usermod -aG frrvty diag
usermod -s /usr/bin/vtysh diag

passwd diag
```

On Junos the standard CLI login is already what the proxy expects. Give the
account a read-only login class. Every operation the proxy issues is a `show`
command.

## Limits

- Up to 20 devices per request, executed concurrently (worker pool of 20,
  queue capacity 100).
- 30 second request deadline; devices still running when it elapses are
  reported as `deadline_exceeded`.
- 1 MB max device output; larger responses are reported as
  `output_too_large`.

## Supported operations

| Operation | Arguments | Result model |
|---|---|---|
| `get_ospf_neighbors` | none | `OspfNeighbors` |
| `get_ospf_neighbor_detail` | none | `OspfNeighborDetails` |
| `get_ospf_interfaces` | none | `OspfInterfaces` |
| `get_ospf_interface` | `interface` | `OspfInterfaces` |
| `get_interface_status` | `interface` | `InterfaceStatus` |
| `get_ospf_status` | none | `OspfStatus` |
| `get_route` | `prefix` | `RouteLookup` |

## Supported platforms

| Platform slug | Driver | Supported operations |
|---|---|---|
| `frr` | `platforms/frr/driver.py` | all operations above |
| `junos` | `platforms/junos/driver.py` | all operations above |

A driver can support only a subset. The adapter returns
`unsupported_operation` for operations it does not implement. Fields the CLI
cannot provide are returned as `null` and listed in `unsupported_fields`.

## Adding an operation

1. Add an `Operation` member in `operation_types.py`.
2. Add one `OperationSpec` in `operations.py`, including the argument kind and
   response model.
3. Add the vendor-neutral Pydantic result model in `schemas.py`.
4. Add the fixed command and inline parser to every driver that supports it.
   The parser may consume JSON or raw text, but must return the shared model.
5. Add literal captured device output and expected results to the adapter tests.
6. Run `pytest tests -q`; the runtime model and generated OpenAPI checks must
   both pass.

Do not add a raw command argument to the request. Do not create a vendor-only
public result model for a field that callers need across platforms; add the
field to the shared model and use `null` plus `unsupported_fields` where a
platform cannot report it.

## Adding a platform driver

1. Choose the platform slug used by inventory records.
2. Add `platforms/<slug>/driver.py` with the Scrapli connection factory and
   handlers for the operations the platform supports.
3. Parse the device's actual output format in the operation method. JSON is
   optional; ordinary CLI text is supported.
4. Register the factory and unsupported fields in `platforms/__init__.py`.
5. Add literal captured output and normalized expected values to the tests.
6. Update the supported-platform table above.

The conformance tests enumerate the operation registry and platform registry,
then validate every driver result against the shared model and generated
OpenAPI schema.

## Tests

```bash
venv/bin/pip install -e ".[test]"
venv/bin/pytest tests -v
```

## License

See [LICENSE](LICENSE).
