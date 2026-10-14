import frappe

def run():
    # 1. Force fix the module links in the DB
    doc_types = ["Employee Directory", "Employee Action Centre"]
    
    # Check if Module Def exists
    if not frappe.db.exists("Module Def", "myHR"):
        frappe.get_doc({"doctype": "Module Def", "module_name": "myHR", "app_name": "myhr"}).insert(ignore_permissions=True)
    
    for dt in doc_types:
        if frappe.db.exists("DocType", dt):
            frappe.db.sql(f"UPDATE tabDocType SET module = 'myHR' WHERE name = '{dt}'")
    
    frappe.db.commit()
    print("✅ DocType module meta repaired.")

if __name__ == "__main__":
    run()
