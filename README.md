# 🚴 iGPSPORT to Intervals.icu Auto-Sync

**iGPSPORT**의 오리지널 `.FIT` 라이딩 기록을 **Intervals.icu**로 자동 동기화해 주는 **GitHub Actions 클라우드 동기화 봇**입니다.


## 🚀 3분 초간단 설정 가이드

### 1단계: 이 저장소 Fork(포크)하기
1. 페이지 우측 상단의 **[Fork]** 버튼을 클릭합니다.
2. **Repository name**을 그대로 두고 **[Create fork]**를 누릅니다.
   > 💡 **Tip:** 저장소를 **Public(공개)** 상태로 유지하시면 GitHub Actions 무료 실행 시간을 **무제한**으로 사용할 수 있습니다.

---

### 2단계: GitHub Secrets 등록하기
포크한 내 저장소의 **`Settings` ➔ `Secrets and variables` ➔ `Actions`** 메뉴로 이동하여 **[New repository secret]** 버튼으로 아래 시크릿을 등록합니다.

#### 필수 Secret (iGPSPORT & Intervals.icu)
| Secret 이름 | 설명 | 예시 |
| :--- | :--- | :--- |
| **`IGPSPORT_USER`** | iGPSPORT 로그인 이메일 | `user@gmail.com` |
| **`IGPSPORT_PASS`** | iGPSPORT 계정 비밀번호 | `mypassword123!` |
| **`INTERVALS_API_KEY`** | Intervals.icu API Key (*발급 방법 하단 참고*) | `a1b2c3d4e5...` |
| **`INTERVALS_ATHLETE_ID`** | Intervals.icu Athlete ID | `i123456` |

#### 선택 Secret (Strava 동시 등록)
> 💡 Strava에도 함께 기록을 올리고 싶을 때만 아래 3가지를 추가로 등록합니다.  
> 등록 시 **Intervals.icu에 먼저 업로드되고 30초 후 Strava로 등록**되어 인터벌스의 Webhook이 정상 트리거됩니다.

| Secret 이름 | 설명 |
| :--- | :--- |
| **`STRAVA_CLIENT_ID`** | Strava API Application Client ID |
| **`STRAVA_CLIENT_SECRET`** | Strava API Application Client Secret |
| **`STRAVA_CLIENT_REFRESH_TOKEN`** | `activity:write` 권한이 부여된 Strava Refresh Token |

#### 🔑 Intervals.icu API Key 발급 방법:
1. [Intervals.icu](https://intervals.icu) 로그인 후 좌측 하단 **Settings** 메뉴로 이동합니다.
2. 페이지 가장 아래로 스크롤하여 **Developer settings** 섹션의 **API Keys**를 찾습니다.
3. **[New API Key]**를 생성하여 복사합니다.

#### 🔑 (선택) Strava API 키 및 Refresh Token 발급 방법:
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

### 3단계: GitHub Actions 활성화 및 즉시 테스트
1. 내 저장소의 **`Actions`** 탭으로 이동합니다.
2. *"Workflows aren't running on this forked repository"* 안내가 나오면 녹색 **[I understand my workflows, go ahead and enable them]** 버튼을 클릭합니다.
3. 좌측 목록에서 **`iGPSPORT to Intervals.icu Sync`**를 선택합니다.
4. 우측의 **[Run workflow]** 버튼을 눌러 첫 동기화를 즉시 실행해 봅니다.

---

## 🕒 자동 실행 주기
* **스케줄:** 비정형 5분 간격 (`2-59/5 * * * *`)
  * 매시 **2분, 7분, 12분, 17분, 22분, 27분, 32분, 37분, 42분, 47분, 52분, 57분**에 자동 실행됩니다.
  * 정각 몰림 현상을 피해 대기열 지연 없이 쾌적하게 동작합니다.
* **수동 즉시 실행:** 라이딩 직후 바로 동기화하고 싶다면 언제든지 Actions 탭에서 **[Run workflow]**를 눌러 수동으로 즉시 동기화할 수 있습니다.
* 💡 **참고 (GitHub 60일 비활성 방지):** GitHub 정책상 Fork한 저장소에 60일간 아무 커밋이 없으면 스케줄 Actions가 일시 중지됩니다. 평소 라이딩을 지속하면 자동 커밋이 발생해 계속 활성 상태가 유지되나, 비시즌 등 2달 이상 라이딩을 쉰 경우 Actions 탭에서 **[Enable workflows]**를 눌러주시면 다시 정상 동작합니다.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).