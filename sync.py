#!/usr/bin/env python3
"""
iGPSPORT to Intervals.icu Activity Synchronizer
Downloads raw .FIT activity files from iGPSPORT and uploads them directly to Intervals.icu.
"""

import os
import sys
import json
import time
import argparse
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Suppress LibreSSL warnings on macOS
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*")

import requests

# iGPSPORT API Endpoints (International)
LOGIN_URL = "https://prod.en.igpsport.com/service/auth/account/login"
ACTIVITY_QUERY_URL = "https://prod.en.igpsport.com/service/web-gateway/web-analyze/activity/queryMyActivity"
GATEWAY_BASE = "https://prod.en.igpsport.com/service/web-gateway/web-analyze/activity"

STATE_FILE = Path("synced_rides.json")


class StravaClient:
    """Client for uploading activity files to Strava."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()
        self.access_token = None

    def refresh_access_token(self) -> Optional[str]:
        """Obtain short-lived access token using refresh token."""
        url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            resp = requests.post(url, data=payload, timeout=15)
            if not resp.ok:
                print(f"❌ [Strava] Failed to refresh token (HTTP {resp.status_code}): {resp.text}")
                return None
            data = resp.json()
            self.access_token = data.get("access_token")
            return self.access_token
        except Exception as e:
            print(f"❌ [Strava] Token refresh exception: {e}")
            return None

    def upload_fit(self, filename: str, fit_bytes: bytes, title: str, description: str = "") -> bool:
        """Upload raw FIT bytes to Strava."""
        if not self.access_token:
            if not self.refresh_access_token():
                return False

        print(f"⬆️ [Strava] Uploading {filename} ('{title}')...")
        url = "https://www.strava.com/api/v3/uploads"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {
            "data_type": "fit",
            "name": title,
            "description": description or "Synced via igpsport2intervals",
            "activity_type": "ride",
        }
        files = {
            "file": (filename, fit_bytes, "application/octet-stream"),
        }

        try:
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            if resp.status_code in (200, 201):
                res_data = resp.json()
                upload_id = res_data.get("id") or res_data.get("id_str")
                print(f"✅ [Strava] Successfully uploaded! Upload ID: {upload_id}")
                return True
            elif resp.status_code == 409 or "duplicate" in resp.text.lower():
                print(f"ℹ️ [Strava] Activity already exists on Strava (Duplicate ignored).")
                return True
            elif resp.status_code == 429:
                print(f"⚠️ [Strava] Rate limit exceeded (HTTP 429).")
                return False
            else:
                print(f"❌ [Strava] Upload failed (HTTP {resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            print(f"❌ [Strava] Upload exception: {e}")
            return False


class IGPSPORTClient:
    """Client for authenticating and fetching activity data from iGPSPORT."""

    def __init__(self, username: str, password: str):
        self.username = username.strip()
        self.password = password.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "iGPSPORT/2.0.0 (Android; Scale/3.00)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.is_authenticated = False

    def login(self) -> bool:
        """Authenticate with iGPSPORT."""
        print(f"🔑 [iGPSPORT] Attempting login...")
        payload = {
            "appId": "igpsport-web",
            "username": self.username,
            "password": self.password,
        }
        try:
            resp = self.session.post(LOGIN_URL, json=payload, timeout=15)
            if not resp.ok:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

            body = resp.json()
            data = body.get("data") or {}
            token = data.get("access_token")

            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.is_authenticated = True
                print(f"✅ [iGPSPORT] Login successful")
                return True
            else:
                msg = body.get("message") or body.get("msg") or "Missing access_token"
                raise RuntimeError(f"Login rejected: {msg}")
        except Exception as e:
            raise RuntimeError(f"iGPSPORT login failed. Details: {e}")

    def fetch_recent_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch list of recent activities."""
        if not self.is_authenticated:
            self.login()

        page_size = min(limit, 20)
        activities = []
        page_no = 1

        while len(activities) < limit:
            params = {
                "pageNo": str(page_no),
                "pageSize": str(page_size),
                "sort": "1",
                "reqType": "0",  # 0 for FIT
            }
            resp = self.session.get(
                ACTIVITY_QUERY_URL,
                params=params,
                timeout=15,
            )
            if not resp.ok:
                print(f"⚠️ [iGPSPORT] Query activities failed: HTTP {resp.status_code}")
                break

            body = resp.json()
            data = body.get("data") or {}
            rows = data.get("rows") or []
            if not rows:
                break

            for item in rows:
                if len(activities) >= limit:
                    break
                ride_id = item.get("rideId") or item.get("RideId")
                if not ride_id:
                    continue
                title = item.get("title") or item.get("Title") or f"iGPSPORT Activity {ride_id}"
                start_time = (
                    item.get("startTime")
                    or item.get("StartTime")
                    or item.get("startTimeString")
                    or "Unknown Date"
                )
                activities.append({
                    "rideId": int(ride_id),
                    "title": str(title),
                    "startTime": str(start_time),
                    "distance": float(item.get("distance") or 0.0),
                })

            if len(rows) < page_size:
                break
            page_no += 1

        return activities

    def download_fit_bytes(self, ride_id: int) -> Optional[Tuple[str, bytes]]:
        """Resolve download URL and return (filename, bytes)."""
        if not self.is_authenticated:
            self.login()

        fit_url = None

        # 1. Try queryActivityDetail
        try:
            detail_resp = self.session.get(f"{GATEWAY_BASE}/queryActivityDetail/{ride_id}", timeout=15)
            if detail_resp.ok:
                detail_data = detail_resp.json().get("data") or {}
                fit_url = detail_data.get("fitUrl")
        except Exception:
            pass

        # 2. Fallback to getDownloadUrl
        if not fit_url:
            try:
                dl_resp = self.session.get(f"{GATEWAY_BASE}/getDownloadUrl/{ride_id}", timeout=15)
                if dl_resp.ok:
                    fit_url = dl_resp.json().get("data")
            except Exception as e:
                print(f"⚠️ [iGPSPORT] Failed to resolve download URL for ride {ride_id}: {e}")

        if not fit_url:
            print(f"❌ [iGPSPORT] No FIT download URL available for ride {ride_id}")
            return None

        # 3. Download the actual FIT binary
        print(f"⬇️ [iGPSPORT] Downloading FIT file for ride {ride_id}...")
        resp = requests.get(fit_url, timeout=30)
        if not resp.ok:
            print(f"❌ [iGPSPORT] Download failed: HTTP {resp.status_code}")
            return None

        if not resp.content or len(resp.content) < 64:
            print(f"⚠️ [iGPSPORT] FIT file for ride {ride_id} is empty or corrupted ({len(resp.content) if resp.content else 0} bytes).")
            return None

        filename = f"igpsport_{ride_id}.fit"
        return filename, resp.content


class IntervalsClient:
    """Client for uploading activity files to Intervals.icu."""

    def __init__(self, api_key: str, athlete_id: str = "0"):
        self.api_key = api_key.strip()
        self.athlete_id = athlete_id.strip() if athlete_id and athlete_id.strip() else "0"
        self.upload_url = f"https://intervals.icu/api/v1/athlete/{self.athlete_id}/activities"

    def upload_fit(self, filename: str, fit_bytes: bytes, title: str, external_id: str) -> bool:
        """Upload raw FIT bytes to Intervals.icu."""
        print(f"⬆️ [Intervals.icu] Uploading {filename} ('{title}')...")
        files = {
            "file": (filename, fit_bytes, "application/octet-stream"),
        }
        params = {
            "name": title,
            "external_id": external_id,
        }

        resp = requests.post(
            self.upload_url,
            params=params,
            files=files,
            auth=("API_KEY", self.api_key),
            timeout=30,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            act_id = data.get("id") or (data.get("activities", [{}])[0].get("id") if data.get("activities") else "OK")
            print(f"✅ [Intervals.icu] Successfully uploaded! Activity ID: {act_id}")
            return True
        elif resp.status_code == 409 or "duplicate" in resp.text.lower():
            print(f"ℹ️ [Intervals.icu] Activity already exists on Intervals.icu (Duplicate ignored).")
            return True
        else:
            print(f"❌ [Intervals.icu] Upload failed (HTTP {resp.status_code}): {resp.text}")
            return False

    def fetch_existing_external_ids(self) -> set:
        """Fetch external_ids already registered on Intervals.icu to prevent redundant uploads."""
        try:
            resp = requests.get(
                self.upload_url,
                auth=("API_KEY", self.api_key),
                timeout=15,
            )
            if resp.ok:
                acts = resp.json()
                if isinstance(acts, list):
                    return {
                        str(a["external_id"])
                        for a in acts
                        if isinstance(a, dict) and a.get("external_id")
                    }
        except Exception as e:
            print(f"ℹ️ [Intervals.icu] Note: Could not query existing activities ({e}). Proceeding normally.")
        return set()


def parse_activity_timestamp(start_time_val: Any) -> Optional[float]:
    """Parse iGPSPORT startTime to epoch timestamp in seconds."""
    if not start_time_val:
        return None
    if isinstance(start_time_val, (int, float)):
        return start_time_val / 1000.0 if start_time_val > 1e11 else float(start_time_val)
    if isinstance(start_time_val, str):
        val = start_time_val.strip()
        if val.isdigit():
            num = float(val)
            return num / 1000.0 if num > 1e11 else num
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y.%m.%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y.%m.%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y/%m/%d",
        ):
            try:
                dt = datetime.strptime(val, fmt)
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
        try:
            dt = datetime.fromisoformat(val)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            pass
    return None


def load_synced_state() -> Tuple[Optional[float], Dict[int, Dict[str, Any]]]:
    """
    Load state from STATE_FILE.
    Returns (last_sync_timestamp, dict_of_synced_activities_by_ride_id).
    """
    if not STATE_FILE.exists():
        return None, {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # Format 1: Object format {"last_sync_timestamp": ..., "synced_activities": [...]}
            if isinstance(data, dict):
                last_ts = data.get("last_sync_timestamp")
                if last_ts is None and data.get("last_sync_time"):
                    last_ts = parse_activity_timestamp(data.get("last_sync_time"))
                if last_ts is not None:
                    last_ts = float(last_ts)

                activities_raw = data.get("synced_activities", [])
                acts_dict = {}
                if isinstance(activities_raw, list):
                    for item in activities_raw:
                        if isinstance(item, dict) and "rideId" in item:
                            acts_dict[int(item["rideId"])] = item
                        elif isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                            acts_dict[int(item)] = {"rideId": int(item)}
                elif isinstance(activities_raw, dict):
                    acts_dict = {int(k): v for k, v in activities_raw.items() if str(k).isdigit()}
                return last_ts, acts_dict

            # Format 2 (Legacy list format): [{"rideId": 123, ...}]
            elif isinstance(data, list):
                if not data:
                    return None, {}
                acts_dict = {}
                max_ts = 0.0
                for item in data:
                    if isinstance(item, dict) and "rideId" in item:
                        r_id = int(item["rideId"])
                        acts_dict[r_id] = item
                        t = parse_activity_timestamp(item.get("startTime")) or parse_activity_timestamp(item.get("syncedAt"))
                        if t and t > max_ts:
                            max_ts = t
                    elif isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                        acts_dict[int(item)] = {"rideId": int(item)}
                last_ts = max_ts if max_ts > 0 else None
                return last_ts, acts_dict
    except Exception as e:
        print(f"⚠️ [State] Could not parse {STATE_FILE}: {e}. Starting fresh.")
    return None, {}


def save_synced_state(last_sync_timestamp: float, synced_dict: Dict[int, Dict[str, Any]]):
    """Save last sync time and synced activities back to state file."""
    try:
        sorted_acts = sorted(synced_dict.values(), key=lambda x: x.get("rideId", 0), reverse=True)
        iso_str = datetime.fromtimestamp(last_sync_timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state_data = {
            "last_sync_time": iso_str,
            "last_sync_timestamp": last_sync_timestamp,
            "synced_activities": sorted_acts,
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        print(f"💾 [State] Updated {STATE_FILE} (Last sync time: {iso_str}, {len(sorted_acts)} activities recorded).")
    except Exception as e:
        print(f"❌ [State] Failed to save state: {e}")


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
    except Exception:
        pass
    return env_vars


def main():
    env_file_data = load_env_file(Path(".env"))

    def get_val(cli_val, env_key, default=""):
        return cli_val or os.getenv(env_key) or env_file_data.get(env_key) or default

    parser = argparse.ArgumentParser(description="Sync iGPSPORT activities to Intervals.icu and Strava")
    parser.add_argument("--user", default=None, help="iGPSPORT username/phone/email")
    parser.add_argument("--password", default=None, help="iGPSPORT password")
    parser.add_argument("--intervals-key", default=None, help="Intervals.icu API Key")
    parser.add_argument("--intervals-athlete", default=None, help="Intervals.icu Athlete ID")
    parser.add_argument("--strava-id", default=None, help="Strava Client ID (Optional)")
    parser.add_argument("--strava-secret", default=None, help="Strava Client Secret (Optional)")
    parser.add_argument("--strava-token", default=None, help="Strava Refresh Token (Optional)")
    parser.add_argument("--all", action="store_true", default=False, help="Sync all past activities (ignore baseline)")
    parser.add_argument("--limit", type=int, default=None, help="Max activities to inspect")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run without uploading")

    args = parser.parse_args()

    user = get_val(args.user, "IGPSPORT_USER")
    password = get_val(args.password, "IGPSPORT_PASS")
    intervals_key = get_val(args.intervals_key, "INTERVALS_API_KEY")
    intervals_athlete = get_val(args.intervals_athlete, "INTERVALS_ATHLETE_ID", "0")
    strava_id = get_val(args.strava_id, "STRAVA_CLIENT_ID")
    strava_secret = get_val(args.strava_secret, "STRAVA_CLIENT_SECRET")
    strava_token = get_val(args.strava_token, "STRAVA_CLIENT_REFRESH_TOKEN")

    limit_str = get_val(str(args.limit) if args.limit is not None else None, "SYNC_LIMIT", "20")
    limit = int(limit_str) if limit_str.isdigit() else 20
    dry_run = args.dry_run or bool(os.getenv("DRY_RUN")) or (env_file_data.get("DRY_RUN", "").lower() in ("true", "1"))
    sync_all = args.all or bool(os.getenv("SYNC_ALL")) and os.getenv("SYNC_ALL", "").lower() in ("true", "1", "yes")

    missing = []
    if not user:
        missing.append("IGPSPORT_USER")
    if not password:
        missing.append("IGPSPORT_PASS")
    if not intervals_key:
        missing.append("INTERVALS_API_KEY")

    if missing:
        print("=" * 60)
        print("ℹ️ [Notice] Account credentials are not configured yet.")
        print(f"ℹ️ Missing secrets: {', '.join(missing)}")
        print("ℹ️ Please register these secrets in Settings > Secrets and variables > Actions.")
        print("ℹ️ Exiting gracefully without error.")
        print("=" * 60)
        sys.exit(0)

    now_utc = datetime.now(timezone.utc)
    now_ts = now_utc.timestamp()

    print("=" * 60)
    print("🚴 iGPSPORT ➔ Intervals.icu & Strava Activity Synchronizer")
    print(f"🕒 Timestamp (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    if sync_all:
        print("🔄 Mode: SYNC ALL (Historical activities included)")
    print("=" * 60)

    igp_client = IGPSPORTClient(user, password)
    intervals_client = IntervalsClient(intervals_key, intervals_athlete)

    strava_client = None
    if strava_id and strava_secret and strava_token:
        print("🔗 [Strava] Credentials configured. Dual-sync enabled (Intervals.icu ➔ Strava).")
        strava_client = StravaClient(strava_id, strava_secret, strava_token)
    else:
        print("ℹ️ [Strava] Credentials not configured. Syncing to Intervals.icu only.")

    # 1. Login & List activities
    igp_client.login()
    activities = igp_client.fetch_recent_activities(limit=limit)
    print(f"📋 [iGPSPORT] Retrieved {len(activities)} recent activities.")

    # 2. Check local state (last_sync_timestamp)
    last_sync_ts, synced_state = load_synced_state()

    # If first run without --all, initialize baseline to current time
    if last_sync_ts is None and not sync_all:
        print("\n" + "=" * 60)
        print(f"🆕 [First Run] Initialized sync baseline time to {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        print(f"ℹ️ Historical activities before this timestamp will not be synced.")
        print(f"ℹ️ Only new activities recorded after this point will be synchronized.")
        print(f"💡 (Tip: To sync historical activities, run manually with sync_all enabled)")
        print("=" * 60)

        for act in activities:
            r_id = act["rideId"]
            synced_state[r_id] = {
                "rideId": r_id,
                "title": act["title"],
                "startTime": act["startTime"],
                "distance": act["distance"] / 1000.0 if act["distance"] > 100 else act["distance"],
                "syncedAt": now_utc.isoformat(),
                "note": "baseline",
            }
        save_synced_state(now_ts, synced_state)
        return

    if last_sync_ts is not None:
        last_sync_str = datetime.fromtimestamp(last_sync_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"⏱️ [State] Last registered sync time: {last_sync_str}")

    # Pre-check activities already on Intervals.icu to avoid duplicate downloading
    intervals_existing = intervals_client.fetch_existing_external_ids()
    if intervals_existing:
        for act in activities:
            r_id = act["rideId"]
            ext_id = f"igpsport_{r_id}"
            if ext_id in intervals_existing and r_id not in synced_state:
                synced_state[r_id] = {
                    "rideId": r_id,
                    "title": act["title"],
                    "startTime": act["startTime"],
                    "distance": act["distance"] / 1000.0 if act["distance"] > 100 else act["distance"],
                    "syncedAt": now_utc.isoformat(),
                }

    # Filter activities that are newer than last_sync_ts AND not in synced_state
    new_activities = []
    for act in activities:
        r_id = act["rideId"]
        if r_id in synced_state:
            continue
        act_ts = parse_activity_timestamp(act.get("startTime"))
        if not sync_all and last_sync_ts is not None and act_ts is not None and act_ts <= last_sync_ts:
            continue
        new_activities.append(act)

    if not new_activities:
        print("✨ All recent activities are already synchronized. Nothing to do.")
        return

    print(f"🚀 Found {len(new_activities)} new activity/activities to sync.")

    # Sort oldest first so Intervals.icu receives them in chronological order
    new_activities.sort(key=lambda x: x["rideId"])

    synced_count = 0
    failed_count = 0

    latest_synced_ts = last_sync_ts

    for act in new_activities:
        ride_id = act["rideId"]
        title = act["title"]
        start_time = act["startTime"]
        dist_km = act["distance"] / 1000.0 if act["distance"] > 100 else act["distance"]
        external_id = f"igpsport_{ride_id}"

        print(f"\n--- Processing Ride #{ride_id}: {title} ({start_time}, {dist_km:.1f} km) ---")

        if dry_run:
            print(f"🔍 [Dry-Run] Would download and upload ride #{ride_id} to Intervals.icu.")
            if strava_client:
                print(f"🔍 [Dry-Run] Would also upload ride #{ride_id} to Strava after 30s delay.")
            synced_state[ride_id] = {
                "rideId": ride_id,
                "title": title,
                "startTime": start_time,
                "distance": dist_km,
                "syncedAt": datetime.now(timezone.utc).isoformat(),
            }
            synced_count += 1
            act_ts = parse_activity_timestamp(start_time)
            if act_ts and act_ts > latest_synced_ts:
                latest_synced_ts = act_ts
            continue

        # Download FIT
        res = igp_client.download_fit_bytes(ride_id)
        if not res:
            failed_count += 1
            continue

        filename, fit_bytes = res

        # 1. Upload to Intervals.icu first
        success = intervals_client.upload_fit(filename, fit_bytes, title, external_id)
        if success:
            synced_state[ride_id] = {
                "rideId": ride_id,
                "title": title,
                "startTime": start_time,
                "distance": dist_km,
                "syncedAt": datetime.now(timezone.utc).isoformat(),
            }
            synced_count += 1
            act_ts = parse_activity_timestamp(start_time)
            if act_ts and act_ts > latest_synced_ts:
                latest_synced_ts = act_ts

            # 2. Upload to Strava after 30 seconds (if Strava credentials configured)
            if strava_client:
                print("⏳ [Strava] Waiting 30 seconds before uploading to Strava to prioritize Intervals.icu webhooks...")
                time.sleep(30)
                strava_client.upload_fit(filename, fit_bytes, title)
        else:
            failed_count += 1

    # Save state
    save_synced_state(latest_synced_ts, synced_state)

    print("\n" + "=" * 60)
    print(f"🎉 Synchronization complete: {synced_count} synced, {failed_count} failed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
