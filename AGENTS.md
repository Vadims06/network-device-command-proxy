# AGENTS.md — network-device-command-proxy

Guide for an AI agent working **on this repository**. Read
[README.md](README.md) first, especially "Adding a platform".

## What belongs here — and what does not

This repo is a vendor-CLI adapter. Its whole job is: an allow-listed
operation in, SSH to one device, one approved `show` command, a typed
neutral result out. It never learns a caller's concept - see
`network-device-command-mcp`'s AGENTS.md for the other side of that line.

| Belongs here | Belongs elsewhere |
|---|---|
| Vendor commands and parsers | Which devices to poll, and why (the caller) |
| Credentials, SSH, host keys | MCP tool registration, agent-facing docstrings |
| The neutral pydantic response models | Caller-specific concepts (graph IDs, ticket IDs) |
| Audit logging | Retry/backoff policy for a caller's own workflow |

If a change teaches this repo what a caller does with the data, it is in the
wrong repo.

## Layout

| File | Role |
|---|---|
| `contracts.py` | `ErrorCode`, `ExecutionError`, `DeviceProfile`/`DeviceCredentials`, the `InventoryProvider`/`CredentialProvider` protocols |
| `operation_types.py` | `Operation`, `ArgumentKind` - the closed string sets of the public contract |
| `operations.py` | `OPERATION_SPECS` - one operation to one response model |
| `schemas.py` | Every public response model, discriminated by `operation` |
| `platforms/base.py` | `DeviceAdapter` - transport, validation, `OutputFormat` |
| `platforms/<vendor>/driver.py` | One platform: Scrapli driver factory, adapter, `UNSUPPORTED_FIELDS` |
| `platforms/__init__.py` | `PLATFORMS`, `UNSUPPORTED_FIELDS` registries |
| `executor.py` | Fans an operation out across devices, applies the deadline |
| `api.py` | FastAPI app, bearer auth, `/v1/execute`, `/openapi.json` |

## Adding a platform

Follow the README's "Adding a platform" checklist - it is the single source
of the file list and file order; this section only adds what an agent
specifically needs to know.

- Read `platforms/iosxr/` first if the new platform's `show` output is text,
  not structured JSON/XML - it is the only text-parsing example, including
  the line-parser style (`re.match` per line, a small state machine) and how
  a parser is cross-checked against an independent oracle
  (`tests/test_rsvp_parser_genie_oracle.py`,
  `docs/rsvp-parsing.md`).
- Every new response model field needs a one-line reason: which vendor
  command reports it, in what shape. A field with no vendor behind it yet is
  speculative and does not belong in the model.
- `UNSUPPORTED_FIELDS` is static capability metadata, not adapter state -
  reportable even when the command failed and no adapter object exists.

## Errors

`ExecutionError(code, message)` is the only way a platform reports failure;
`code` is always an `ErrorCode` member, never a bare string. `_send_command`
in `platforms/base.py` already separates transport failure
(`device_unreachable`), bad credentials (`authentication_failed`), a command
that ran but errored (`command_failed`), output too large, and unparseable
output (`parse_error`) - a new platform's own handler only needs to raise
`ExecutionError` for anything specific to its own parsing, everything else is
already handled by the shared transport.

## Tests

```bash
pytest tests -q                                    # never installs Genie
pip install -e ".[genie]" && pytest tests -q        # cross-checks a text parser's oracle tests too
```

A platform's own unit tests assert literal, hand-verified expected values
against a captured fixture - never values derived from the parser under test.
The Genie oracle test (where one exists) is a second, independent proof, not
a replacement for the literal one.
