import requests
import json

# ===================== ANTHROPIC (CLAUDE) CHECKER =====================
def check_claude(api_key):
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return "✅ AKTIF", resp.status_code, "Valid"
        elif resp.status_code == 401:
            return "❌ INVALID", resp.status_code, "Unauthorized"
        else:
            return "⚠️ ERROR", resp.status_code, resp.text[:50]
    except Exception as e:
        return "❌ GAGAL", 0, str(e)[:50]

# ===================== DEEPSEEK CHECKER =====================
def check_deepseek(api_key):
    url = "https://api.deepseek.com/user/balance"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            balance = data.get("balance_infos", [{}])[0].get("total_balance", "N/A")
            return f"✅ AKTIF (Balance: {balance})", resp.status_code, "Valid"
        elif resp.status_code == 401:
            return "❌ INVALID", resp.status_code, "Unauthorized"
        else:
            return "⚠️ ERROR", resp.status_code, resp.text[:50]
    except Exception as e:
        return "❌ GAGAL", 0, str(e)[:50]

# ===================== CEK SEMUA KEY KAMU =====================
keys = [
    "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",  # Anthropic
]

print("=" * 60)
print("CEK API KEY")
print("=" * 60)

for key in keys:
    # Deteksi provider dari prefix
    if key.startswith("sk-ant"):
        provider = "Anthropic (Claude)"
        status, code, detail = check_claude(key)
    elif "deepseek" in key.lower() or len(key) < 60:  # DeepSeek key biasanya pendek
        provider = "DeepSeek"
        status, code, detail = check_deepseek(key)
    else:
        provider = "Unknown"
        status, code, detail = "❓ SKIP", 0, "Provider tidak dikenali"

    masked = key[:15] + "..." + key[-6:]
    print(f"\nProvider : {provider}")
    print(f"Key      : {masked}")
    print(f"Status   : {status}")
    print(f"Kode HTTP: {code}")
    print(f"Detail   : {detail}")
