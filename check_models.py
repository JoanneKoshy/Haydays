import requests

API_KEY = "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"

response = requests.get(
    "https://integrate.api.nvidia.com/v1/models",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

models = response.json()
for m in models["data"]:
    if any(x in m["id"].lower() for x in ["vision", "phi", "llama", "visual"]):
        print(m["id"])