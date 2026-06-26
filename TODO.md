# TODO - Fix Render OTP email failure

## Plan summary
The Render logs show: `Error: [Errno 101] Network is unreachable` when sending OTP email (SMTP to Gmail). This usually happens because the server cannot reach the mail host or outgoing SMTP is blocked. Fix by:
1) making OTP sending non-blocking and returning a clean API error,
2) adding a Render-friendly OTP fallback (show OTP only when email fails via a safe dev flag),
3) improving logging to store the exact SMTP/network error in `app_errors.log` and return a stable message.

## Steps
- [ ] Inspect OTP code paths in `app.py` (done conceptually).
- [ ] Update `send_email_otp()` to raise/log errors with clearer context.
- [ ] Update `/api/send-otp` to:
  - return `success: false` with user-safe message on network failure,
  - only include “Dev OTP” when an env flag like `ALLOW_DEV_OTP=true` is set.
- [ ] Update documentation: `README.md` + `render.yaml` env var guidance.
- [ ] Run local smoke test for `/api/send-otp`.
- [ ] Commit and push to GitHub.

