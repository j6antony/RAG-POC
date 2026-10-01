from fastapi import HTTPException

ROLE_ACCESS_LEVELS = {"user": 1, "manager": 2, "admin": 3}


def get_user_role(supabase, user_id):
    response = (
        supabase.table("user_roles")
        .select("role")
        .eq("user_id", str(user_id))
        .execute()
    )
    roles = {row["role"] for row in (response.data or [])}
    if not roles or not roles.issubset(ROLE_ACCESS_LEVELS):
        raise HTTPException(
            status_code=403,
            detail="Account role is missing or invalid. Check the user_roles assignment.",
        )
    # A user can have multiple role assignments; use the highest assigned level.
    return max(roles, key=ROLE_ACCESS_LEVELS.get)

def get_user_permissions(supabase, role):
    response = (
        supabase.table("role_permissions")
        .select("permission")
        .eq("role", role)
        .execute()
    )
    """
    This will return like [ {permission: "chat"}, {permission: "upload_document"}, {permission: "web_search"}]
    so iterate through and extract the permissions
    """
    permissions = []
    for i in response.data:
        permissions.append(i["permission"])
    return permissions

def get_user_access(supabase, user_id):
    return ROLE_ACCESS_LEVELS[get_user_role(supabase, user_id)]

# this function will be useful for further implementation but as of now it is unused
def has_permission(supabase, user_id, action):
    role = get_user_role(supabase, user_id)
    permissions = get_user_permissions(supabase, role)
    if action in permissions:
        return True
    return False
