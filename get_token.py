#!/usr/bin/env python3
"""One-time helper to mint your WHOOP refresh token on your own machine.
Uses curl (built into macOS) so Cloudflare lets the request through.
Run:  python3 get_token.py
"""
import json, secrets, subprocess, urllib.parse

AUTH_URL="https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL="https://api.prod.whoop.com/oauth/oauth2/token"
REDIRECT="https://example.com/whoop-callback"
SCOPES="read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement offline"

client_id=input("WHOOP Client ID: ").strip()
client_secret=input("WHOOP Client Secret: ").strip()
state=secrets.token_urlsafe(12)
params={"client_id":client_id,"redirect_uri":REDIRECT,"response_type":"code","scope":SCOPES,"state":state}
url=AUTH_URL+"?"+urllib.parse.urlencode(params,quote_via=urllib.parse.quote)
print("\n1) Open this URL in your browser and click Approve:\n")
print(url)
print("\n2) Your browser lands on an 'Example Domain' page. Copy the FULL URL")
print("   from the address bar (it contains ?code=...).\n")
returned=input("Paste the full redirect URL here: ").strip()
q=urllib.parse.parse_qs(urllib.parse.urlparse(returned).query)
code=q["code"][0]

cmd=["curl","-s","-X","POST",TOKEN_URL,
     "-H","Content-Type: application/x-www-form-urlencoded",
     "--data-urlencode","grant_type=authorization_code",
     "--data-urlencode","code="+code,
     "--data-urlencode","client_id="+client_id,
     "--data-urlencode","client_secret="+client_secret,
     "--data-urlencode","redirect_uri="+REDIRECT]
res=subprocess.run(cmd,capture_output=True,text=True)
try:
    tok=json.loads(res.stdout)
except Exception:
    print("Token exchange failed:",res.stdout[:400] or res.stderr[:200]); raise SystemExit(1)
if "refresh_token" not in tok:
    print("Error from WHOOP:",json.dumps(tok)); raise SystemExit(1)

print("\n=== SUCCESS ===")
print("Paste these into your GitHub repo secrets:\n")
print("WHOOP_CLIENT_ID     =",client_id)
print("WHOOP_CLIENT_SECRET =",client_secret)
print("WHOOP_REFRESH_TOKEN =",tok["refresh_token"])
print("\nDone. You can close this terminal.")
