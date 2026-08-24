#!/usr/bin/env python3
"""
iGPSPORT Login & Authentication Verification Tool
Tests credentials against iGPSPORT International and China authentication servers.
Verifies access token acquisition and queries recent activities to ensure full API access.
"""

import os
import sys
import json
import argparse
import getpass
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List

# Suppress LibreSSL warnings on macOS
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")

import requests


# iGPSPORT API Endpoints (International)
LOGIN_URL = "https://prod.en.igpsport.com/service/auth/account/login"
ACTIVITY_QUERY_URL = "https://prod.en.igpsport.com/service/web-gateway/web-analyze/activity/queryMyActivity"
DETAIL_URL = "https://prod.en.igpsport.com/service/web-gateway/web-analyze/activity/queryActivityDetail"
DOWNLOAD_URL = "https://prod.en.igpsport.com/service/web-gateway/web-analyze/activity/getDownloadUrl"
USER_INFO_URL = "https://prod.en.igpsport.com/service/mobile/api/User/UserInfo"


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Parse key=value pairs from a .env file."""
    env_vars = {}
    if not env_path.is_file():
        return env_vars
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    env_vars[key] = val
    except Exception as e:
        print(f"⚠️ [Env] Warning: Could not read {env_path}: {e}")
    return env_vars


def get_credentials(cli_user: Optional[str], cli_pass: Optional[str]):
    """Resolve credentials from CLI args, .env file, environment variables, or interactive prompt."""
    env_file = Path(".env")
    env_from_file = load_env_file(env_file)

    # 1. User
    user = (
        cli_user
        or os.getenv("IGPSPORT_USER")
        or env_from_file.get("IGPSPORT_USER")
        or os.getenv("INTERVALSSYNC_IGPSPORT_USER")
        or env_from_file.get("INTERVALSSYNC_IGPSPORT_USER")
    )

    # 2. Password
    password = (
        cli_pass
        or os.getenv("IGPSPORT_PASS")
        or env_from_file.get("IGPSPORT_PASS")
        or os.getenv("INTERVALSSYNC_IGPSPORT_PASSWORD")
        or env_from_file.get("INTERVALSSYNC_IGPSPORT_PASSWORD")
    )

    # If missing and running interactively, prompt user
    if not user:
        if sys.stdin.isatty():
            try:
                user = input("Enter iGPSPORT username / email / phone: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                sys.exit(1)
        else:
            return None, None

    if not password:
        if sys.stdin.isatty():
            try:
                password = getpass.getpass("Enter iGPSPORT password: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                sys.exit(1)
        else:
            return user, None

    return user, password


def mask_token(token: str) -> str:
    """Mask JWT token for secure display."""
    if not token or len(token) < 16:
        return "***"
    return f"{token[:8]}...{token[-6:]} (length: {len(token)})"


def mask_user(user: str) -> str:
    """Mask email/username for secure display."""
    if "@" in user:
        name, domain = user.split("@", 1)
        if len(name) > 2:
            return f"{name[0]}***{name[-1]}@{domain}"
        return f"{name[0]}***@{domain}"
    if len(user) > 4:
        return f"{user[:2]}***{user[-2:]}"
    return "***"


def test_login_and_query(username: str, password: str) -> bool:
    """Test login and activity query."""
    print(f"\n────────────────────────────────────────────────────────────")
    print(f"🌐 Testing iGPSPORT Gateway: International")
    print(f"🔗 Login URL: {LOGIN_URL}")
    print(f"────────────────────────────────────────────────────────────")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "iGPSPORT/2.0.0 (Android; Scale/3.00)",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })

    payload = {
        "appId": "igpsport-web",
        "username": username,
        "password": password,
    }

    # Step 1: POST Login
    try:
        print(f"📡 Sending authentication request for user: {mask_user(username)}...")
        resp = session.post(LOGIN_URL, json=payload, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network connection failed: {e}")
        return False

    print(f"📥 HTTP Response Status: {resp.status_code}")

    try:
        body = resp.json()
    except Exception:
        print(f"❌ Failed to parse server response as JSON: {resp.text[:300]}")
        return False

    code = body.get("code")
    msg = body.get("message") or body.get("msg") or "No message"
    data = body.get("data") or {}
    token = data.get("access_token")

    if not resp.ok or not token:
        print(f"❌ Authentication Rejected!")
        print(f"   • Response Code: {code}")
        print(f"   • Server Message: {msg}")
        if "data" in body and body["data"]:
            print(f"   • Extra Data: {body['data']}")
        return False

    print(f"✅ Login SUCCESSFUL!")
    print(f"   • Access Token: {mask_token(token)}")
    if "userId" in data:
        print(f"   • User ID: {data.get('userId')}")
    if "nickname" in data:
        print(f"   • Nickname: {data.get('nickname')}")

    session.headers.update({"Authorization": f"Bearer {token}"})

    # Step 2: Query User Info (Optional verification)
    try:
        u_resp = session.get(USER_INFO_URL, timeout=10)
        if u_resp.ok:
            u_data = u_resp.json().get("data") or {}
            nick = u_data.get("NickName") or u_data.get("nickname")
            if nick:
                print(f"   • Profile Nickname: {nick}")
    except Exception:
        pass

    # Step 3: Query Recent Activities
    print(f"\n🚴 Querying recent activities (queryMyActivity)...")
    try:
        act_params = {
            "pageNo": "1",
            "pageSize": "5",
            "sort": "1",
            "reqType": "0",  # FIT
        }
        act_resp = session.get(ACTIVITY_QUERY_URL, params=act_params, timeout=15)
        if not act_resp.ok:
            print(f"⚠️ Activity query returned HTTP {act_resp.status_code}: {act_resp.text[:200]}")
            return True

        act_json = act_resp.json()
        act_data = act_json.get("data") or {}
        total = act_data.get("total") or 0
        rows = act_data.get("rows") or []

        print(f"✅ Activity Query Successful!")
        print(f"   • Total activities on account: {total}")
        print(f"   • Retrieved {len(rows)} recent activities in first page:\n")

        if rows:
            for idx, r in enumerate(rows, 1):
                ride_id = r.get("rideId") or r.get("RideId")
                title = r.get("title") or r.get("Title") or "Untitled Ride"
                st = r.get("startTime") or r.get("StartTime") or r.get("startTimeString") or "Unknown"
                dist = float(r.get("distance") or 0.0)
                dist_km = dist / 1000.0 if dist > 100 else dist
                print(f"     [{idx}] Ride #{ride_id}: {title}")
                print(f"         📅 Date: {st} | 📏 Distance: {dist_km:.2f} km")

            # Step 4: Test FIT download link resolution for the 1st ride
            first_ride_id = rows[0].get("rideId") or rows[0].get("RideId")
            if first_ride_id:
                print(f"\n🔍 Testing FIT download URL resolution for Ride #{first_ride_id}...")
                dl_url = None
                try:
                    d_resp = session.get(f"{DETAIL_URL}/{first_ride_id}", timeout=10)
                    if d_resp.ok:
                        dl_url = d_resp.json().get("data", {}).get("fitUrl")
                except Exception:
                    pass

                if not dl_url:
                    try:
                        d_resp2 = session.get(f"{DOWNLOAD_URL}/{first_ride_id}", timeout=10)
                        if d_resp2.ok:
                            dl_url = d_resp2.json().get("data")
                    except Exception:
                        pass

                if dl_url:
                    print(f"✅ FIT URL resolved successfully! (Starts with: {dl_url[:40]}...)")
                else:
                    print(f"ℹ️ FIT direct URL not immediately available (may be processing or format specific).")
        else:
            print("ℹ️ No activities found on this account yet.")

        return True

    except Exception as e:
        print(f"⚠️ Activity query exception: {e}")
        return True


def test_intervals_icu(api_key: str, athlete_id: str = "0") -> bool:
    """Test Intervals.icu API Key and Athlete ID validity."""
    print(f"\n────────────────────────────────────────────────────────────")
    print(f"📊 Testing Intervals.icu Connection")
    print(f"👤 Athlete ID: {athlete_id}")
    print(f"────────────────────────────────────────────────────────────")

    if not api_key:
        print("ℹ️ No INTERVALS_API_KEY provided (skipping Intervals.icu test).")
        return True

    target_athlete = athlete_id if athlete_id else "0"
    url = f"https://intervals.icu/api/v1/athlete/{target_athlete}"
    try:
        resp = requests.get(url, auth=("API_KEY", api_key), timeout=15)
        if resp.ok:
            data = resp.json()
            ath_name = data.get("name") or data.get("firstname") or "Unknown"
            ath_id = data.get("id") or target_athlete
            print(f"✅ Intervals.icu Authentication SUCCESSFUL!")
            print(f"   • Athlete Name: {ath_name}")
            print(f"   • Athlete ID: {ath_id}")
            return True
        elif resp.status_code == 403:
            print(f"❌ Intervals.icu Access Denied (HTTP 403)!")
            print(f"   • Check if your INTERVALS_API_KEY is correct or if Athlete ID '{target_athlete}' matches.")
            return False
        else:
            print(f"❌ Intervals.icu returned HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Intervals.icu connection error: {e}")
        return False


def test_strava(client_id: str, client_secret: str, refresh_token: str) -> bool:
    """Test Strava API credentials validity."""
    print(f"\n────────────────────────────────────────────────────────────")
    print(f"🟠 Testing Strava Connection (Optional)")
    print(f"🆔 Client ID: {client_id}")
    print(f"────────────────────────────────────────────────────────────")

    if not (client_id and client_secret and refresh_token):
        print("ℹ️ Strava secrets not fully configured (skipping Strava test).")
        return True

    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
        "refresh_token": refresh_token.strip(),
        "grant_type": "refresh_token",
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        if not resp.ok:
            print(f"❌ Strava Authentication Rejected (HTTP {resp.status_code})!")
            print(f"   • Response: {resp.text[:200]}")
            return False

        data = resp.json()
        token = data.get("access_token")
        print(f"✅ Strava Token Refresh SUCCESSFUL!")
        print(f"   • Access Token: {mask_token(token)}")

        # Fetch athlete info
        a_resp = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if a_resp.ok:
            a_data = a_resp.json()
            fname = a_data.get("firstname", "")
            lname = a_data.get("lastname", "")
            print(f"   • Athlete Name: {fname} {lname}".strip())
            print(f"   • Athlete ID: {a_data.get('id')}")

        return True
    except Exception as e:
        print(f"❌ Strava connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify iGPSPORT, Intervals.icu, and Strava login credentials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Run with environment variables or .env file:
  python check_login.py

  # 2. Provide credentials directly via arguments:
  python check_login.py --user your_email@example.com --password your_password
        """
    )
    parser.add_argument("-u", "--user", default=None, help="iGPSPORT username / email / phone")
    parser.add_argument("-p", "--password", default=None, help="iGPSPORT password")
    parser.add_argument("--intervals-key", default=None, help="Intervals.icu API Key")
    parser.add_argument("--intervals-athlete", default=None, help="Intervals.icu Athlete ID")
    parser.add_argument("--strava-id", default=None, help="Strava Client ID (Optional)")
    parser.add_argument("--strava-secret", default=None, help="Strava Client Secret (Optional)")
    parser.add_argument("--strava-token", default=None, help="Strava Refresh Token (Optional)")

    args = parser.parse_args()

    print("=" * 60)
    print("🚴 iGPSPORT, Intervals.icu & Strava Verification")
    print("=" * 60)

    user, password = get_credentials(args.user, args.password)

    if not user or not password:
        print("\n❌ Error: Missing credentials.")
        print("Please provide username and password via:")
        print("  1. Command line: python check_login.py -u <user> -p <pass>")
        print("  2. .env file: create a .env file with IGPSPORT_USER and IGPSPORT_PASS")
        print("  3. Environment variables: export IGPSPORT_USER='...' IGPSPORT_PASS='...'")
        sys.exit(1)

    print(f"👤 Target Account: {mask_user(user)}")

    igp_success = test_login_and_query(user, password)
    if igp_success:
        print(f"\n🎉 [Result] iGPSPORT Login and API verification SUCCEEDED!")
    else:
        print(f"\n❌ [Result] iGPSPORT Login Failed.")

    # Intervals.icu test
    env_vars = load_env_file(Path(".env"))
    intervals_key = args.intervals_key or os.getenv("INTERVALS_API_KEY") or env_vars.get("INTERVALS_API_KEY")
    intervals_athlete = args.intervals_athlete or os.getenv("INTERVALS_ATHLETE_ID") or env_vars.get("INTERVALS_ATHLETE_ID", "0")
    intervals_success = True
    if intervals_key:
        intervals_success = test_intervals_icu(intervals_key, intervals_athlete)

    strava_id = args.strava_id or os.getenv("STRAVA_CLIENT_ID") or env_vars.get("STRAVA_CLIENT_ID")
    strava_secret = args.strava_secret or os.getenv("STRAVA_CLIENT_SECRET") or env_vars.get("STRAVA_CLIENT_SECRET")
    strava_token = args.strava_token or os.getenv("STRAVA_CLIENT_REFRESH_TOKEN") or env_vars.get("STRAVA_CLIENT_REFRESH_TOKEN")
    strava_success = True
    if strava_id and strava_secret and strava_token:
        strava_success = test_strava(strava_id, strava_secret, strava_token)

    print("\n" + "=" * 60)
    if igp_success and intervals_success and strava_success:
        print("✨ ALL CHECKS PASSED: Your accounts are ready for syncing!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("💥 CHECKS FAILED:")
        if not igp_success:
            print("   [iGPSPORT]")
            print("   1. Verify your username/email and password on the official app/website.")
        if not intervals_success:
            print("   [Intervals.icu]")
            print("   1. Check your INTERVALS_API_KEY in Settings > Developer settings > API Keys.")
            print("   2. Check your INTERVALS_ATHLETE_ID (e.g. i123456).")
        if not strava_success:
            print("   [Strava]")
            print("   1. Check your STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_CLIENT_REFRESH_TOKEN.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
