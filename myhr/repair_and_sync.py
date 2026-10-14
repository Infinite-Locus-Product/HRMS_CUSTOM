import frappe

def run():
    # 1. Force fix the module links in the DB (Corrected table name)
    doc_types = ["Employee Directory", "Employee Action Centre"]
    
    # Check if 'myHR' Module Def exists
    if not frappe.db.exists("Module Def", "myHR"):
        frappe.get_doc({"doctype": "Module Def", "module_name": "myHR", "app_name": "myhr"}).insert(ignore_permissions=True)
    
    for dt in doc_types:
        if frappe.db.exists("DocType", dt):
            # Using standard ORM to avoid SQL syntax/table name issues
            frappe.db.set_value("DocType", dt, "module", "myHR")
            frappe.db.set_value("DocType", dt, "custom", 0)
    
    frappe.db.commit()
    print("✅ DocType module meta repaired.")

    # 4. Sync Data (using frappe.get_all directly to avoid import issues)
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "custom_employee_id", "employee_name", "designation", "department", "cell_number", "company_email"])
    
    for emp in employees:
        if not emp.custom_employee_id: continue
        payload = {
            "doctype": "Employee Directory",
            "employee_id": emp.custom_employee_id,
            "employee_name": emp.employee_name,
            "designation": emp.designation,
            "department": emp.department,
            "mobile_number": emp.cell_number,
            "employee_email": emp.company_email
        }
        if not frappe.db.exists("Employee Directory", emp.custom_employee_id):
            frappe.get_doc(payload).insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("✅ Employee Directory populated.")

if __name__ == "__main__":
    run()
