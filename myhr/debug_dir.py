import frappe

def run():
    print("--- DEBUG ---")
    
    # 1. Check if employees exist
    emps = frappe.get_all("Employee", fields=["name", "employee_name", "custom_emp_directory"])
    print(f"Total Employees: {len(emps)}")
    for e in emps:
        print(f"- {e.name}: {e.employee_name} (In dir? {e.custom_emp_directory})")
        
    # 2. Check Employee Directory
    dir_entries = frappe.get_all("Employee Directory", fields=["name", "employee_name"])
    print(f"Total in Directory: {len(dir_entries)}")
    for d in dir_entries:
        print(f"- {d.name}: {d.employee_name}")
        
    print("-------------")
