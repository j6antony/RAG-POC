
class Autherization:
    def __init__(self,supabase):
        self.supabase = supabase
    def get_roles(self, user_id):
        response = (
            self.supabase.table("user_roles").select("role").eq("user_id", user_id).execute()
        )
        return [row["role"] for row in response.data]
    def get_permissions(self, roles):
        if not roles:
            return []

        response = (
            self.supabase
            .table("role_permissions")
            .select("permission")
            .in_("role", roles)
            .execute()
        )

        return [row["permission"] for row in response.data]
    def get_department(self, user_id):
        response = (
            self.supabase
            .table("user_departments")
            .select("department")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        return response.data["department"]