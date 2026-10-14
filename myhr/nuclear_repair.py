import frappe

def run():
    # 1. Clean up stale Module Def if it exists under wrong name
    frappe.db.sql("DELETE FROM tabModule WHERE name = 'myHR'")
    frappe.db.commit()
    
    # 2. Re-create correct Module Def
    if not frappe.db.exists("Module Def", "myHR"):
        frappe.get_doc({
            "doctype": "Module Def", 
            "module_name": "myHR", 
            "app_name": "myhr"
        }).insert(ignore_permissions=True)
    
    # 3. Associate DocTypes to this module
    doc_types = ["Employee Directory", "Employee Action Centre"]
    for dt in doc_types:
        if frappe.db.exists("DocType", dt):
            frappe.db.sql(f"UPDATE tabDocType SET module = 'myHR', custom = 0 WHERE name = '{dt}'")
    
    frappe.db.commit()
    print("✅ Module and DocType links fixed.")
    
    # 4. Sync Data
    from myhr.sync_directory import sync_employees
    sync_employees()
    print("✅ Employee Data Synced.")
    
    # 5. Setup Dummies (A-Z)
    from myhr.setup_dummies import run as setup_dummies
    setup_dummies()
    print("✅ Dummy Employees Created (A-Z).")

if __name__ == "__main__":
    run()
