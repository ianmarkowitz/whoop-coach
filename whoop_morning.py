#!/usr/bin/env python3
"""WHOOP morning coach — pulls last night's recovery/sleep/strain, computes a
pragmatic training + food recommendation, pushes it to your phone via ntfy.
Uses curl so Cloudflare lets requests through. Standard library otherwise.
Runs on GitHub Actions each morning; reads secrets from env vars. Rotates the
refresh token and writes the new one to new_refresh_token.txt for the workflow.
"""
import os, sys, json, subprocess, datetime
from zoneinfo import ZoneInfo

TOKEN_URL="https://api.prod.whoop.com/oauth/oauth2/token"
API="https://api.prod.whoop.com/developer/v2"
TZ=ZoneInfo("America/New_York")

CLIENT_ID=os.environ["WHOOP_CLIENT_ID"]
CLIENT_SECRET=os.environ["WHOOP_CLIENT_SECRET"]
REFRESH_TOKEN=os.environ["WHOOP_REFRESH_TOKEN"]
NTFY_TOPIC=os.environ.get("NTFY_TOPIC","").strip()
NTFY_SERVER=os.environ.get("NTFY_SERVER","https://ntfy.sh").rstrip("/")

FORCE=os.environ.get("FORCE_RUN","").lower() in ("1","true","yes")
now_et=datetime.datetime.now(TZ)
if not FORCE and now_et.hour!=6:
    print(f"Local ET hour is {now_et.hour}, not 6 — skipping this UTC firing.")
    sys.exit(0)

def curl(url, data=None, headers=None, method="GET"):
    cmd=["curl","-s","-X",method,url]
    for k,v in (headers or {}).items():
        cmd+=["-H",f"{k}: {v}"]
    if data:
        cmd+=["-H","Content-Type: application/x-www-form-urlencoded"]
        for k,v in data.items():
            cmd+=["--data-urlencode",f"{k}={v}"]
    res=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    if not res.stdout:
        raise RuntimeError(f"empty response from {url}: {res.stderr[:200]}")
    return json.loads(res.stdout)

def refresh():
    tok=curl(TOKEN_URL, method="POST", data={
        "grant_type":"refresh_token","refresh_token":REFRESH_TOKEN,
        "client_id":CLIENT_ID,"client_secret":CLIENT_SECRET,"scope":"offline"})
    if "access_token" not in tok:
        raise RuntimeError("refresh failed: "+json.dumps(tok))
    if tok.get("refresh_token"):
        open("new_refresh_token.txt","w").write(tok["refresh_token"])
    return tok["access_token"]

def get(access, path, params=None):
    url=API+path
    if params:
        import urllib.parse; url+="?"+urllib.parse.urlencode(params)
    return curl(url, headers={"Authorization":f"Bearer {access}"})

def paginate(access, path, days_back=35):
    end=datetime.datetime.now(datetime.timezone.utc); start=end-datetime.timedelta(days=days_back)
    out,nx=[],None
    while True:
        p={"limit":25,"start":start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),"end":end.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        if nx: p["nextToken"]=nx
        j=get(access,path,p); out+=j.get("records",[]); nx=j.get("next_token")
        if not nx: break
    return out

def scored(r): return [x for x in r if x.get("score_state")=="SCORED" and isinstance(x.get("score"),dict)]
def mean(xs): xs=[x for x in xs if x is not None]; return sum(xs)/len(xs) if xs else None

def push(title, body):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC not set — skipping push."); return
    subprocess.run(["curl","-s","-X","POST",f"{NTFY_SERVER}/{NTFY_TOPIC}",
        "-H",f"Title: {title}","-H","Tags: muscle","-d",body],
        capture_output=True,text=True,timeout=20)
    print("Pushed to phone via ntfy.")

def main():
    access=refresh()
    rec=scored(paginate(access,"/recovery")); slp=scored(paginate(access,"/activity/sleep")); cyc=scored(paginate(access,"/cycle"))
    rec.sort(key=lambda r:r.get("created_at","")); cyc.sort(key=lambda c:c.get("start",""))
    sm=[s for s in slp if not s.get("nap")]; sm.sort(key=lambda s:s.get("end",s.get("start","")))
    if not rec:
        push("WHOOP coach","No recovery data yet this morning — WHOOP may still be syncing."); return
    sc=rec[-1]["score"]; r=sc.get("recovery_score"); hrv=sc.get("hrv_rmssd_milli"); rhr=sc.get("resting_heart_rate")
    sh=None
    if sm:
        ss=sm[-1]["score"].get("stage_summary",{}); tib=ss.get("total_in_bed_time_milli"); aw=ss.get("total_awake_time_milli",0) or 0
        if tib: sh=round((tib-aw)/3600000.0,1)
    strain=cyc[-1]["score"].get("strain") if cyc else None
    hrv_avg=mean([x["score"].get("hrv_rmssd_milli") for x in rec[-30:]]); rhr_avg=mean([x["score"].get("resting_heart_rate") for x in rec[-30:]])
    if r>=67: head=f"🟢 GREEN {r:.0f}% — PUSH"; train="Good day for a real Peloton ride or a lifting session. Your body can take load."
    elif r>=34: head=f"🟡 YELLOW {r:.0f}% — MODERATE"; train="Keep it Zone 2: easy spin or a brisk walk. Don't chase a hard number today."
    else: head=f"🔴 RED {r:.0f}% — REST"; train="Walk only. Protect recovery — pushing today costs more than it gives."
    lines=[train]
    if sh is not None and sh<6.5:
        lines.append(f"⚠️ Low sleep ({sh}h) = high-risk food day. Protein breakfast FIRST, keep controlled snacks in reach. The starve-grab wins today if you skip meals.")
    elif sh is not None:
        lines.append(f"😴 Sleep {sh}h — solid. Anchor the morning with protein and you're set.")
    sb=[]
    if hrv is not None and hrv_avg: sb.append(f"HRV {hrv:.0f}ms {'↑' if hrv>=hrv_avg else '↓'} (30d avg {hrv_avg:.0f})")
    if rhr is not None and rhr_avg: sb.append(f"RHR {rhr:.0f}bpm {'↓' if rhr<=rhr_avg else '↑'} (30d avg {rhr_avg:.0f})")
    if strain is not None: sb.append(f"yest. strain {strain:.1f}")
    if sb: lines.append("📊 "+" · ".join(sb))
    body="\n".join(lines); print(head+"\n"+body); push(head,body)

if __name__=="__main__":
    main()
