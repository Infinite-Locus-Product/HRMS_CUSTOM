import requests

session = requests.Session()
# Login as Administrator
res = session.post("http://127.0.0.1:8000/api/method/login", data={"usr": "Administrator", "pwd": "admin"})

# Get directory via ticketnext
res2 = session.post("http://127.0.0.1:8000/api/method/ticketnext.ticketnext.api.get_employee_directory")
print(f"ticketnext POST Directory: {res2.status_code} - {res2.text[:200]}")
