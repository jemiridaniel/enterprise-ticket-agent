# app/services/intune_service.py
from typing import List, Optional

from .graph_service import graph_client


async def get_user_by_upn(user_upn: str) -> Optional[dict]:
    """
    Look up a user by UPN/email.
    """
    if not graph_client.enabled:
        return None

    # /users/{id-or-userPrincipalName}
    return await graph_client.get(f"users/{user_upn}")


async def get_user_devices(user_id: str) -> List[dict]:
    """
    Get Intune-managed devices for a user.
    """
    if not graph_client.enabled:
        return []

    # Common Intune endpoint for user devices
    # See https://learn.microsoft.com/graph/api/intune-devices-manageddevice-list-userid
    path = f"users/{user_id}/managedDevices"
    data = await graph_client.get(path)
    if not data:
        return []

    # Intune returns a "value" list
    return data.get("value", [])


async def get_device_compliance_state(device: dict) -> str:
    """
    Extract high-level compliance state from a managedDevice object.
    """
    # Typical properties: complianceState, deviceName, operatingSystem, etc.
    return device.get("complianceState", "unknown")
