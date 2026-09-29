def get_user_role(supabase, user_id):
    role = (
        supabase.table("user_roles")
        .select("role")
        .eq("user_id", user_id)
        .execute()
    )
    """
    This will return [{role: "role"}]
    """
    if role.data:
        return role.data[0]["role"]
    # if no role assign an automatic default of user class
    return "user"

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
    ROLE_ACCESS_LEVELS = {"user": 1, "manager": 2, "admin": 3}
    role = get_user_role(supabase, user_id)
    access_level = ROLE_ACCESS_LEVELS.get(role)
    print("ACCESS DEBUG - role:", role)
    print("ACCESS DEBUG - resolved access level:", access_level)
    return access_level

# this function will be useful for further implementation but as of now it is unused
def has_permission(supabase, user_id, action):
    role = get_user_role(supabase, user_id)
    permissions = get_user_permissions(supabase, role)
    if action in permissions:
        return True
    return False
