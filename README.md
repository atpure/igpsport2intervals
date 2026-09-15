# 🚴 iGPSPORT to Intervals.icu Auto-Sync

**iGPSPORT**의 오리지널 `.FIT` 라이딩 기록을 **Intervals.icu**(및 선택 시 **Strava**)로 자동 동기화해 주는 **GitHub Actions 클라우드 동기화 봇**입니다.

* ⚡ **무설치 클라우드 실행**: PC를 켜둘 필요 없이 GitHub Actions가 클라우드에서 24시간 자동 실행됩니다.
* 📦 **오리지널 .FIT 파일 전송**: iGPSPORT 원본 바이너리 데이터를 직접 전달하여 파워, 케이던스, 심박, 기어비, GPS 원본 데이터를 온전히 보존합니다.
* 🔄 **Intervals.icu 기본 동기화 & (선택) Strava 동시 동기화**: 기본적으로 Intervals.icu로 자동 동기화되며, Strava 시크릿을 추가 등록할 경우에 한해 Intervals.icu에 먼저 업로드 후 30초 대기열을 거쳐 Strava로 순차 등록되어 Intervals의 Webhook 자동 연동이 완벽하게 지원됩니다.
* 🛡️ **Fork 지원 & 무료 무제한**: 이 저장소를 본인 계정으로 Fork(포크)만 하면 무료로 즉시 사용할 수 있습니다.

---

## 🚀 3분 초간단 설정 가이드

### 1단계: 이 저장소 Fork(포크)하기
1. 페이지 우측 상단의 **[Fork]** 버튼을 클릭합니다.
2. **Repository name**을 그대로 두고 **[Create fork]**를 누릅니다.
   > 💡 **Tip:** 저장소를 **Public(공개)** 상태로 유지하시면 GitHub Actions 무료 실행 시간을 **무제한**으로 사용할 수 있습니다.

---

### 2단계: 저장소 쓰기 권한(Workflow permissions) 활성화
GitHub Actions가 동기화 기록(`synced_rides.json`)을 저장소에 자동 커밋(`git push`)할 수 있도록 쓰기 권한을 설정합니다:
1. 포크한 내 저장소의 **`Settings` ➔ `Actions` ➔ `General`** 메뉴로 이동합니다.
2. 페이지 가장 아래의 **`Workflow permissions`** 섹션을 찾습니다.
3. 두 가지 라디오 옵션 중 첫 번째인 **`◉ Read and write permissions`**를 선택합니다.
   * `Workflows have read and write permissions in the repository for all scopes.` 항목에 체크
   * (*참고: 하단의 'Allow GitHub Actions to create and approve pull requests' 체크박스는 선택하지 않아도 됩니다.*)
4. 바로 아래 **[Save]** 버튼을 클릭하여 저장합니다.

---

### 3단계: GitHub Secrets 등록하기
포크한 내 저장소의 **`Settings` ➔ `Secrets and variables` ➔ `Actions`** 메뉴로 이동하여 **[New repository secret]** 버튼으로 아래 시크릿을 등록합니다.

#### 필수 Secret (iGPSPORT & Intervals.icu)
| Secret 이름 | 설명 | 예시 |
| :--- | :--- | :--- |
| **`IGPSPORT_USER`** | iGPSPORT 앱 로그인 이메일 | `user@gmail.com` |
| **`IGPSPORT_PASS`** | iGPSPORT 앱 계정 비밀번호 | `mypassword123!` |
| **`INTERVALS_API_KEY`** | [Intervals.icu](https://intervals.icu) API Key (*발급 방법 하단 참고*) | `a1b2c3d4e5...` |
| **`INTERVALS_ATHLETE_ID`** | [Intervals.icu](https://intervals.icu) Athlete ID (기본값: `0`) | `i123456` 또는 `0` |

> 💡 **iGPSPORT 계정 안내:** 스마트폰의 **iGPSPORT 공식 앱(Android / iOS)**에서 회원가입 및 로그인할 때 사용하는 이메일과 비밀번호를 등록하시면 됩니다.

#### 선택 Secret (Strava 동시 등록)
> 💡 Strava에도 함께 기록을 올리고 싶을 때만 아래 3가지를 추가로 등록합니다.  
> 등록 시 **Intervals.icu에 먼저 업로드되고 30초 후 Strava로 등록**되어 인터벌스의 Webhook이 정상 트리거됩니다.

| Secret 이름 | 설명 |
| :--- | :--- |
| **`STRAVA_CLIENT_ID`** | Strava API Application Client ID |
| **`STRAVA_CLIENT_SECRET`** | Strava API Application Client Secret |
| **`STRAVA_CLIENT_REFRESH_TOKEN`** | `activity:write` 권한이 부여된 Strava Refresh Token |

---

### 4단계: GitHub Actions 활성화 및 첫 실행
1. 내 저장소의 **`Actions`** 탭으로 이동합니다.
2. *"Workflows aren't being run on this forked repository"* 안내가 나오면 녹색 **[I understand my workflows, go ahead and enable them]** 버튼을 클릭합니다.
3. 좌측 목록에서 **`iGPSPORT to Intervals.icu Sync`**를 클릭합니다.
4. 화면 상단에 *"This scheduled workflow is disabled because scheduled workflows are disabled by default in forks."* 안내가 나타나면 **[Enable workflow]** 버튼을 클릭합니다.
5. 활성화된 후 우측 상단의 **[Run workflow]** 버튼을 누르면 팝업 설정창이 나타납니다:
   * **기본 실행 (추천 - 앞으로의 신규 라이딩만 자동 동기화):**  
     옵션을 건드리지 않고(체크박스 해제 상태 그대로) 초록색 **[Run workflow]** 버튼을 클릭하면, 기존 기록은 건너뛰고 **앞으로 새롭게 타는 라이딩부터 5분마다 자동 동기화**가 시작됩니다.
   * **과거 기록도 함께 가져오고 싶을 때:**  
     **`[✓] 과거 기록도 함께 업로드`** 체크박스를 체크한 뒤 초록색 **[Run workflow]**를 클릭하면, iGPSPORT에 남아있던 최근 20개의 이전 기록도 Intervals.icu로 함께 업로드됩니다. (가져올 개수 변경 가능)

---

## 🔑 API Key 발급 안내

### Intervals.icu API Key
1. [Intervals.icu](https://intervals.icu) 로그인 후 좌측 하단 **Settings** 메뉴로 이동합니다.
2. 페이지 가장 아래로 스크롤하여 **Developer settings** 섹션의 **API Keys**를 찾습니다.
3. **[New API Key]**를 생성하여 복사합니다.

### (선택) Strava API 키 및 Refresh Token
1. [Strava API Settings](https://www.strava.com/settings/api)에 접속하여 새 API Application을 생성합니다. (Authorization Callback Domain은 `localhost` 입력)
2. 발급된 **`Client ID`**와 **`Client Secret`**을 확인합니다.
3. 브라우저 주소창에 아래 URL을 입력하여 권한 승인을 진행합니다 (*`YOUR_CLIENT_ID`를 실제 Client ID로 변경*):
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all,activity:write
   ```
4. **[승인]** 버튼 클릭 후 브라우저가 이동한 URL(`http://localhost/?state=&code=...&scope=...`)에서 **`code=` 뒤의 문자열**을 복사합니다.
5. 터미널에서 아래 명령어를 실행하여 영구 갱신용 `refresh_token`을 획득합니다:
   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -F client_id=YOUR_CLIENT_ID \
     -F client_secret=YOUR_CLIENT_SECRET \
     -F code=복사한_CODE \
     -F grant_type=authorization_code
   ```
6. 반환된 JSON에서 `"refresh_token"` 값을 복사하여 GitHub Secrets의 **`STRAVA_CLIENT_REFRESH_TOKEN`**에 등록합니다.

---

## 🕒 동작 방식 & 자동 실행 주기

* **스케줄:** 2분 오프셋 55분 간격 (`2-59/55 * * * *`)
  * 매시 **2분, 57분**에 자동 실행됩니다.
  * 정각 몰림 현상을 피해 GitHub Actions 대기열 지연 없이 쾌적하게 동작합니다.
* **수동 즉시 실행:** 라이딩 직후 바로 동기화하고 싶다면 언제든지 Actions 탭에서 **[Run workflow]**를 눌러 즉시 동기화할 수 있습니다.
* **중복 방지 & 상태 추적:** 동기화된 활동은 `synced_rides.json` 및 Intervals.icu의 고유 `external_id`를 통해 이중 체크되므로 중복 업로드가 발생하지 않습니다.
* 💡 **참고 (GitHub 60일 비활성 방지):** GitHub 정책상 Fork한 저장소에 60일간 아무 커밋이 없으면 스케줄 Actions가 일시 중지됩니다. 평소 라이딩을 지속하면 자동 커밋이 발생해 계속 활성 상태가 유지되나, 비시즌 등 2달 이상 라이딩을 쉰 경우 Actions 탭에서 **[Enable workflows]**를 눌러주시면 다시 정상 동작합니다.

---

## 💻 로컬 테스트 (선택 사항)

로컬 환경에서 iGPSPORT 계정 접속 및 동작을 미리 확인해보고 싶다면:

```bash
# 가상환경 생성 및 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 로그인 및 계정 연동 테스트
python check_login.py

# 로컬에서 1회성 동기화 실행 (Dry-run 모드)
python sync.py --dry-run
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).