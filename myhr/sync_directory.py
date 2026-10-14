import frappe

def sync_employees():
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "custom_employee_id", "employee_name", "designation", "department", "cell_number", "company_email"])
    
    for emp in employees:
        if not emp.custom_employee_id:
            continue
            
        payload = {
            "doctype": "Employee Directory",
            "employee_id": emp.custom_employee_id,
            "employee_name": emp.employee_name,
            "designation": emp.designation,
            "department": emp.department,
            "mobile_number": emp.cell_number,
            "employee_email": emp.company_email
        }
        
        if frappe.db.exists("Employee Directory", emp.custom_employee_id):
            doc = frappe.get_doc("Employee Directory", emp.custom_employee_id)
            doc.update(payload)
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc(payload).insert(ignore_permissions=True)
            
    frappe.db.commit()
    print(f"Synced {len(employees)} employees to Directory.")

if __name__ == "__main__":
    sync_employees()
