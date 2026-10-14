import requests

session = requests.Session()
# Login as Administrator
res = session.post("http://127.0.0.1:8000/api/method/login", data={"usr": "Administrator", "pwd": "admin"})
print(f"Login: {res.status_code}")

# Get directory
res2 = session.get("http://127.0.0.1:8000/api/method/myhr.api.get_employee_directory")
print(f"GET Directory: {res2.status_code} - {res2.text[:200]}")

res3 = session.post("http://127.0.0.1:8000/api/method/myhr.api.get_employee_directory")
print(f"POST Directory: {res3.status_code} - {res3.text[:200]}")
