import requests

url = "https://spbe.kommo.com/api/v4/leads/17332060"
message = "Kimak Kimak"
payload = { "custom_fields_values": [
        {
            "field_id": 1069656,
            "field_name": "Custom Message",
            "field_code": None,
            "field_type": "textarea",
            "values": [{ "value": message }]
        }
    ] }
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVlZDEyNmVmNTkwNmNiNTc5YzE3YThkODI5YTM1YmYzOTA5Y2U1NzY4MmIzYWY2OWY1NmQ1ZTM0M2Y0YjUyYWJkYjZjNmEzNmVhNjRiNGZkIn0.eyJhdWQiOiI0Y2M3YzVjNS0zYTNjLTQzMTQtYjJhYi1hM2IyYzE1OTZiZWQiLCJqdGkiOiJlZWQxMjZlZjU5MDZjYjU3OWMxN2E4ZDgyOWEzNWJmMzkwOWNlNTc2ODJiM2FmNjlmNTZkNWUzNDNmNGI1MmFiZGI2YzZhMzZlYTY0YjRmZCIsImlhdCI6MTc1MDgzMTgwNiwibmJmIjoxNzUwODMxODA2LCJleHAiOjE3Nzc1OTM2MDAsInN1YiI6IjEyODUxNDgzIiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjM0MjkwNDE5LCJiYXNlX2RvbWFpbiI6ImtvbW1vLmNvbSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNDNhZDg4YzktZGNlYi00MzMyLTgyMTctYzI3YWFkYjA2MWM1IiwiYXBpX2RvbWFpbiI6ImFwaS1jLmtvbW1vLmNvbSJ9.Q3OlfATV51Nq_V5TW8sOLL9XNwvmgQSa7tCOKoK50BPp4kBUTYvPrsetqjqxMvEXu_bLYchidFFwpzQPbTksEbrXc3Cl1sLLDO5vXaIEwZPZIBYy9YTYgEI-GSwj0EJJ11SS-VEGFit-QmIV3BGd441BERm8tJlUVHdDcFRD5YgMqPbpy10hJLwElYOygY9SxePX0cGwDlFC5CucF2OOYFQd40fokOaIquAK4fSN87mLOeYzxesEbP6Y6GI1vXSShkpmAeWcrJoVzY-pDAH4w-am0q1yf25UbXFJ7NwGk1P8RlutU-hcIHaTqJbjyYT9frEmefyrAf0enC6SNhVBZA"
}

response = requests.patch(url, json=payload, headers=headers)

print(response.text)