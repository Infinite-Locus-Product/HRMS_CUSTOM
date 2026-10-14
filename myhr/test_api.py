import frappe
from myhr.api import get_employee_directory

def run():
    print("Testing get_employee_directory...")
    try:
        res = get_employee_directory()
        print(f"Result count: {len(res) if res else res}")
        if res:
            print(res[:2])
    except Exception as e:
        print(f"Error: {e}")
