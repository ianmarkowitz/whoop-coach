# WHOOP Morning Coach

A free, always-on job that pulls your WHOOP recovery/sleep/strain every morning at
6:30 Eastern and pushes a pragmatic training + food recommendation to your phone.
Runs entirely on GitHub Actions — your computer never has to be on.

Your credentials live only in GitHub's encrypted secret vault. This code never
stores them in plaintext, and the refresh token rotates itself each run.

---

## What the morning push looks like

> 🟢 GREEN 71% — PUSH
> Good day for a real Peloton ride or a lifting session. Your body can take load.
> 😴 Sleep 7.4h — solid. Anchor the morning with protein and you're set.
> 📊 HRV 27ms ↑ (30d avg 25) · RHR 65bpm ↓ (30d avg 68) · yest. strain 12.3

On a rough night it flips to a food-risk warning instead — the low-sleep days are
exactly when the starve-then-grab pattern wins, so that's when it nudges hardest.

---

## One-time setup (~10 minutes)

### 1. Get your phone notifications working (ntfy — free, no account)
1. Install the **ntfy** app ([iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)).
2. In the app, tap **+** and subscribe to a topic. Pick something private and
   hard to guess, e.g. `ian-whoop-9f3k2x` (anyone who knows the topic name can
   send you notes, so make it random).
3. Remember that topic name — it becomes the `NTFY_TOPIC` secret below.

### 2. Mint your refresh token (on your own machine)
```bash
python3 get_token.py
```
(Uses only Python's built-in libraries — no `pip install` needed. macOS ships
`python3`; if it's missing, install Apple's tools with `xcode-select --install`.)
Follow the prompts (it reuses the same approve-in-browser step you already did).
It prints three values at the end — keep that terminal open for the next step.

### 3. Create a private GitHub repo and push this folder
```bash
git init
git add .
git commit -m "WHOOP morning coach"
gh repo create whoopcoach --private --source=. --push
```
(Or create the repo on github.com and push the usual way.)

### 4. Create a Personal Access Token so the job can rotate its own token
1. GitHub → **Settings → Developer settings → Fine-grained tokens → Generate new token**.
2. Repository access: **Only select repositories → your `whoopcoach` repo**.
3. Permissions → Repository permissions → **Secrets: Read and write**.
4. Generate it and copy the token — it becomes the `GH_PAT` secret below.

### 5. Add the repo secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret.**
Add each of these:

| Secret name | Value |
|---|---|
| `WHOOP_CLIENT_ID` | from `get_token.py` output |
| `WHOOP_CLIENT_SECRET` | from `get_token.py` output |
| `WHOOP_REFRESH_TOKEN` | from `get_token.py` output |
| `NTFY_TOPIC` | your ntfy topic from step 1 |
| `GH_PAT` | the fine-grained token from step 4 |

### 6. Test it
Repo → **Actions → WHOOP Morning Coach → Run workflow** (leave force = true).
Within a minute you should get a notification on your phone. 🎉

That's it. From now on it fires every morning at 6:30 ET on its own.

---

## Notes & knobs
- **Change the time:** edit the two `cron:` lines in `.github/workflows/whoop-morning.yml`
  (they're in UTC). The script only acts when it's actually 6am Eastern, so keep the
  UTC times matched to 6:30 ET if you move it.
- **Turn it off:** disable the workflow in the Actions tab, or delete the repo.
- **Revoke everything instantly:** delete the app in your WHOOP developer dashboard —
  that kills all access immediately.
- **Adjust the advice:** the recommendation logic is all in `whoop_morning.py`
  (the recovery thresholds and the sleep cutoff). Easy to tweak.
