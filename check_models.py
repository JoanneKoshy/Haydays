import requests

API_KEY = ""

response = requests.get(
    "https://integrate.api.nvidia.com/v1/models",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

models = response.json()
for m in models["data"]:
    if any(x in m["id"].lower() for x in ["vision", "phi", "llama", "visual"]):
        print(m["id"])