"""One credential set shared by every device, taken from the environment.

Exists so the service has a credential source that does not require standing
up a Vault first, which is a larger step than the whole of the rest of the
setup. Every device gets the same login, which is exactly why it belongs in a
lab or a first run rather than in production.
"""

from __future__ import annotations

from device_command_proxy.contracts import CredentialProvider, DeviceCredentials


class EnvCredentialProvider(CredentialProvider):
    def __init__(self, credentials: DeviceCredentials):
        self._credentials = credentials

    def get_credentials(self, credential_profile: str) -> DeviceCredentials:
        # The profile names intent in the inventory, but there is nothing to
        # resolve it against here: one credential set covers every device.
        return self._credentials
