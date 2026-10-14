import frappe
from myhr.api import get_employee_directory

def run():
    frappe.session.user = "arjun@sample.com" # Assuming this user exists
    if not frappe.db.exists("User", "arjun@sample.com"):
        print("User arjun@sample.com doesn't exist, using Administrator")
        frappe.session.user = "Administrator"
    else:
        print(f"Testing as {frappe.session.user}...")
        
    try:
        # Check permissions specifically
        perms = frappe.permissions.get_roles(frappe.session.user)
        print(f"Roles: {perms}")
        print(f"Has read perm: {frappe.has_permission('Employee Directory', 'read')}")
        
        res = get_employee_directory()
        print(f"Result count: {len(res) if res else res}")
        if res:
            print(res[:1])
            
        # Try raw SQL
        sql_res = frappe.db.sql("SELECT name FROM `tabEmployee Directory`", as_dict=True)
        print(f"SQL Result count: {len(sql_res)}")
    except Exception as e:
        print(f"Error: {e}")
