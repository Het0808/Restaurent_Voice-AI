"""Central role-to-permission mapping."""

from restaurant_voice_ai.auth.models import Permission, Role

ROLE_PERMISSIONS = {
    Role.PUBLIC: set(),
    Role.CLIENT: {
        Permission.SEND_TEXT_MESSAGE,
        Permission.OPEN_VOICE_SESSION,
        Permission.RESET_CONVERSATION,
    },
    Role.ADMIN: set(Permission),
    Role.INTERNAL: set(Permission),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
