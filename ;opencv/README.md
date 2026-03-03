# 📸 사진 자동 자르기 (Photo Cropper) v9.0

🌐 [English](README_EN.md) | 한국어

스캔된 사진이나 배경 위에 놓인 사진을 자동으로 감지하여 정확하게 자르는 Python 애플리케이션입니다.

## ✨ v9.0 새 기능

### 🎨 UI/UX 리팩토링
- **새로운 색상 테마**: 인디고 퍼플 액센트 (#818cf8)
- **에메랄드/로즈/앰버 팔레트**: 성공/오류/경고 색상 개선
- **그라데이션 토스트 알림**: 더 세련된 알림 UI
- **프로그레스 UI 개선**: 새 색상 팔레트 적용

### ⚡ 성능 최적화
- **CLAHE 객체 캐싱**: 이미지 처리 속도 향상
- **커널 캐싱**: 모폴로지 연산 최적화
- **Import 최적화**: 불필요한 inline import 제거

### 🛡️ 안정성 업데이트 (2026-02)
- **Watch/Batch 파이프라인 일치**: 감시 모드도 배치와 동일한 후처리(얼굴 보정/스마트 보정/리사이즈/분류 폴더/워터마크)를 적용
- **후처리 순서 고정**: 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 라우팅(워터마크 전) → 워터마크
- **AI 설정 반영 경로 보강**: 이미지 분류/얼굴 감지 토글이 실제 저장 경로와 결과 이미지에 반영
- **유니코드 워터마크 경로 안정화**: 이미지 워터마크 로딩을 `np.fromfile + cv2.imdecode`로 처리
- **그레이스케일 워터마크 호환성**: `to_grayscale + 이미지 워터마크` 조합에서도 채널 불일치 없이 적용
- **DNN 얼굴 감지 폴백 안정화**: 모델 자동 다운로드/검증 실패 시 Haar로 즉시 폴백
- **대용량 입력 제한 반영**: `performance.max_image_size_mb`를 처리 전 실제 파일 크기 필터에 적용
- **skip_processed 보강**: 자동 분류 하위 폴더까지 중복 결과를 탐지
- **중단 응답성 개선**: 멀티스레드 배치 중 취소 요청 시 pending 작업 취소를 더 빠르게 반영
- **GPU 설정 연결 보강**: `PerformanceSettings.use_gpu`가 고급 처리기 초기화에 반영

### 🔥 v8.5 핵심 기능
- **다중 사진 자동 감지**: 한 스캔에서 여러 사진을 자동으로 분리
- **워터마크 추가**: 텍스트/이미지 워터마크 지원
- **이미지 리사이즈**: 다양한 모드 지원
- **폴더 모니터링**: 자동 처리 Watch Mode
- **CLI 모드**: 명령줄에서 배치 처리

---

## 주요 기능

### 핵심 기능
- **3단계+ 지능형 탐색 알고리즘**: 다양한 배경에서 높은 검출 성공률
- **배치 처리**: 대량의 이미지를 한 번에 처리 (예상 남은 시간 표시)
- **메인 화면 일괄 편집**: 폴더 이미지를 불러와 이전/다음 탐색으로 외곽선을 순차 편집 후 한 번에 저장
- **Watch Mode 파이프라인 통합**: 감시 모드와 배치 모드의 처리 결과 일관성 확보
- **이미 처리된 파일 건너뛰기**: 중복 처리 방지
- **다양한 출력 포맷**: JPG, PNG, WEBP 지원

### UI/UX
- **PyQt6 기반 현대적 UI**: 다크/라이트 테마, 그라디언트 효과
- **토스트 알림**: 작업 완료 시 슬라이드-인 애니메이션 알림
- **실시간 미리보기**: 마우스 휠 확대/축소, 줌 슬라이더 (10%~500%)
- **수동 경계 편집**: 원본 탭에서 외곽선 점 드래그, 자동 탐지 실패 시 4점 클릭으로 직접 경계 지정
- **실패 파일 전용 보정 모드**: 경계 탐지 실패 파일만 별도 로드해 재편집
- **드래그 앤 드롭**: 폴더나 이미지를 직접 끌어다 놓기

## 🛠️ 감지 알고리즘

| 단계 | 알고리즘 | 설명 |
|------|----------|------|
| 1단계 | Multi-Scale Canny Edge | 다중 스케일 에지 검출 |
| 2단계 | Adaptive Threshold | 적응형 이진화 |
| 3단계 | Gradient Analysis (Sobel) | 그래디언트 분석 |
| 4단계 | Harris Corner Detection | 코너 검출 (선택적) |

## 📦 설치

### 요구 사항
- Python 3.8 이상
- Windows / macOS / Linux

### 설치 방법

```bash
pip install -r requirements.txt
```

## 🚀 사용법

### GUI 애플리케이션 실행

```bash
python run.py
```

### CLI 사용법

```bash
# 기본 사용
python -m photo_cropper.cli --input ./scans --output ./cropped

# 정확도 우선 + 디버그 저장
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate --debug-detect

# 워터마크 추가
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# 리사이즈 적용
python -m photo_cropper.cli -i ./scans -o ./cropped --max-size 1920

# 리사이즈 적용 (비율/해상도/프리셋)
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "50%"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "1200x900"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize instagram_square

# 멀티포토 감지
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo

# 병렬 처리 (스레드 수 지정)
python -m photo_cropper.cli -i ./scans -o ./cropped --jobs 6

# 이미 처리된 파일 건너뛰기
python -m photo_cropper.cli -i ./scans -o ./cropped --skip-processed

# 옵션 확인
python -m photo_cropper.cli --help
```

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 입력 폴더 선택 |
| `Ctrl+I` | 이미지 열기 |
| `Ctrl+P` | 미리보기 |
| `Ctrl+R` | 이미지 회전 (90도 시계방향) |
| `Ctrl+Z` | 실행 취소 (v8.5) |
| `Ctrl+Y` | 다시 실행 (v8.5) |
| `F11` | 전체화면 프리뷰 (v8.5) |
| `F5` | 파일 목록 새로고침 |
| `Ctrl+E` | 출력 폴더 열기 |
| `Ctrl+Q` | 종료 |

## ⚙️ 설정 옵션

### 설정 파일 위치
- Windows: `%APPDATA%/PhotoCropper/settings.json`
- macOS/Linux: `~/.photo_cropper/photo_cropper_settings.json`

> Windows에서 구버전 설정 파일(`~/.photo_cropper/photo_cropper_settings.json`)이 있으면 자동으로 새 경로로 마이그레이션됩니다.

### v8.5 신규 설정

#### 워터마크 설정
- **텍스트 워터마크**: 텍스트, 폰트 크기, 색상, 그림자
- **이미지 워터마크**: PNG 이미지, 스케일, 투명도
- **위치**: 9방향 선택 (좌상단~우하단)
- **타일 모드**: 반복 패턴 워터마크

#### 리사이즈 설정
- **모드**: 맞춤(Fit), 채우기(Fill), 늘리기, 비율, 최대크기
- **크기**: 너비, 높이, 비율(%)
- **프리셋**: Instagram, Facebook, A4 등

#### 자동화 설정
- **폴더 감시**: 새 파일 자동 처리
- **스케줄러**: 예약 시간에 자동 배치 처리

### 알고리즘 설정
- **Canny 임계값**: 에지 감지 민감도 조절 (0-255)
- **CLAHE**: 저대비 이미지 향상
- **다중 스케일**: 다양한 크기의 사진 감지
- **코너 검출**: 추가적인 정확도 향상
- **검출 모드 (fast/balanced/accurate)**: 속도/정확도 트레이드오프 프리셋
- **검출 디버그 저장**: `_debug` 폴더에 엣지/마스크/후보 오버레이/`meta.json` 저장 (실패 원인 분석용)

### 출력 설정
- **출력 포맷**: JPG, PNG, WEBP
- **품질 조절**: JPG/WEBP 품질 (1-100), PNG 압축 (0-9)
- **그레이스케일/노이즈 제거/선명도 향상**
- **자동 분류 저장(선택)**: 분류 신뢰도 조건 충족 시 카테고리 하위 폴더에 저장

> 참고: 파일명 규칙/타임스탬프를 사용하는 경우 `skip processed` 판별은 출력 파일명 기준입니다.
> 파일명에 시간이 포함되면 이전 처리본을 완전히 탐지하지 못할 수 있습니다.
> 자동 분류 하위 폴더(`인물/풍경/문서/흑백/기타`)는 `skip processed` 탐지 대상에 포함됩니다.
> 다만 파일명 규칙/타임스탬프 조합에서는 중복 판별 한계가 남을 수 있으므로 대량 재처리 전 샘플 검증을 권장합니다.

## 🧪 안정성 체크 포인트

- **문법 검증**: `python -m compileall -q photo_cropper`
- **CLI 스모크 테스트**: `python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --max-size 1920 --skip-processed`
- **워치 모드 검증**: GUI에서 Watch Mode 시작 후 신규 파일 투입 시 배치와 동일한 출력(워터마크/리사이즈/분류 폴더) 확인
- **유니코드 경로 검증**: 한글 경로의 워터마크 이미지 파일을 지정해 저장 성공 여부 확인
- **취소 검증**: 멀티스레드 배치 실행 중 중단 요청 시 진행률 및 로그가 빠르게 취소 상태로 전환되는지 확인

## 📁 프로젝트 구조

```
photo_cropper/
├── main.py                  # 진입점
├── cli.py                   # CLI 인터페이스 (v8.5)
├── core/
│   ├── image/processor.py   # 핵심 이미지 처리
│   ├── batch/processor.py   # 배치 처리
│   ├── settings_model/app_settings.py          # 설정 관리
│   ├── multi_photo_detector.py  # 다중 사진 감지 (v8.5)
│   ├── watermark_processor.py   # 워터마크 (v8.5)
│   ├── resize_processor.py      # 리사이즈 (v8.5)
│   ├── folder_watcher.py        # 폴더 감시 (v8.5)
│   ├── scheduler.py             # 스케줄러 (v8.5)
│   └── history_manager.py       # 히스토리 관리 (v8.5)
├── ui/
│   ├── main/window.py
│   └── widgets/
│       ├── settings/panel.py
│       ├── preview_widget.py
│       ├── thumbnail_grid_widget.py  # 썸네일 그리드 (v8.5)
│       ├── fullscreen_viewer.py      # 전체화면 뷰어 (v8.5)
│       └── floating_action_button.py # FAB (v8.5)
├── i18n/                    # 다국어 지원 (v8.5)
│   └── catalog/manager.py
└── utils/
    └── file_helpers.py
```

## 🔧 빌드 (PyInstaller)

### 실행 파일 생성

```bash
# 의존성 설치
pip install pyinstaller

# 빌드 실행 (경량화 적용)
pyinstaller photo_cropper.spec --clean
```

빌드된 실행 파일: `dist/PhotoCropper_v9.exe`

### 추가 경량화 (UPX)

[UPX](https://github.com/upx/upx/releases)를 설치하면 실행 파일 크기가 약 30-50% 감소합니다:

1. UPX 다운로드 및 압축 해제
2. `upx.exe`를 시스템 PATH에 추가
3. 다시 빌드: `pyinstaller photo_cropper.spec --clean`

### 빌드 최적화 내용

| 항목 | 설명 |
|------|------|
| 단일 파일 | onefile 모드로 단일 .exe 생성 |
| 불필요 모듈 제외 | matplotlib, scipy, pandas, tkinter 등 |
| OpenCV 경량화 | 미사용 모듈 제거 (dnn, ml, video 등) |
| NumPy 경량화 | 테스트/문서 파일 제거 |
| UPX 압축 | 실행 파일 압축 (~40% 크기 감소) |

## 📋 변경 이력

### v9.0 수동 경계 보정 업데이트 (2026-03)
- ✨ 메인 화면에 폴더 일괄 편집/이전/다음/편집 저장 추출 흐름 추가
- ✨ 자동 경계 탐지 실패 파일을 감지해 사용자에게 안내하고, 실패 파일만 수동 보정 모드로 로드
- ✨ 원본 탭에서 외곽선 점 드래그 편집 강화 및 4점 클릭 수동 경계 지정 지원
- 🛡️ 일괄 처리 취소/종료 응답성 개선(수동 추출 스레드 중단 요청 처리 포함)

### v9.0 안정성 패치 (2026-02)
- 🛡️ Watch Mode가 `BatchProcessor.process_single()` 경로를 사용하도록 통합
- 🛡️ 얼굴 보정/스마트 보정/리사이즈/분류 폴더 라우팅/워터마크를 배치·감시 모드 공통 파이프라인으로 정렬
- 🛡️ 분류 라우팅을 워터마크 적용 전 이미지 기준으로 수행해 분류 왜곡을 완화
- 🛡️ 워터마크 이미지 경로를 유니코드 안전 로딩(`np.fromfile + cv2.imdecode`)으로 전환
- 🛡️ 그레이스케일 + 이미지 워터마크 조합에서 채널 불일치 예외를 제거
- 🛡️ DNN 얼굴 감지 모델 자동 다운로드/체크섬 검증 및 네트워크 실패 시 Haar 폴백 적용
- 🛡️ `max_image_size_mb` 제한을 배치/감시 처리 전 파일 크기 필터에 반영
- 🛡️ `skip processed`가 자동 분류 하위 폴더 경로까지 중복 탐지
- 🛡️ 멀티스레드 취소 시 pending 작업 취소를 우선 처리해 응답성 개선

### v9.0 (2026-01)
- 🎨 **UI/UX 리팩토링** - 인디고 퍼플 테마 (#818cf8)
- 🎨 **새 색상 팔레트** - 에메랄드/로즈/앰버
- 🎨 **그라데이션 토스트** - 더 세련된 알림 UI
- ⚡ **CLAHE 캐싱** - 이미지 처리 속도 향상
- ⚡ **커널 캐싱** - 모폴로지 연산 최적화
- ⚡ **Import 최적화** - 불필요한 inline import 제거

### v8.5 (2026-01)
- ✨ **다중 사진 자동 감지** - 한 스캔에서 여러 사진 분리
- ✨ **워터마크 시스템** - 텍스트/이미지 워터마크
- ✨ **이미지 리사이즈** - 다양한 모드 및 프리셋
- ✨ **폴더 모니터링** - 자동 처리 Watch Mode
- ✨ **스케줄러** - 예약 배치 처리
- ✨ **CLI 인터페이스** - 명령줄 배치 처리
- ✨ **썸네일 그리드 뷰** - 이미지 목록 그리드 표시
- ✨ **전체화면 프리뷰** - F11 전체화면 모드
- ✨ **FAB (플로팅 액션 버튼)** - 빠른 접근 메뉴
- ✨ **Undo/Redo 히스토리** - 실행 취소/다시 실행
- ✨ **다국어 지원** - 한국어, 영어, 일본어

### v7.2 (2025-12)
- 버튼, 프로그레스바에 그라디언트 효과
- 토스트 알림 시스템
- 줌 슬라이더 (10%~500%)
- 배치 완료 후 폴더 자동 열기

### v7.1 (2025-12)
- 이미지 회전 (Ctrl+R)
- 파일 목록 새로고침 (F5)
- 예상 남은 시간(ETA) 표시
- 윈도우 상태 저장/복원

## 📄 라이선스

MIT License

## 👨‍💻 기여

버그 리포트나 기능 제안은 Issues에 등록해 주세요.


## 2026-03-01 구현 정합성 업데이트

- CLI 설정 병합이 defaults -> preset -> config -> cli override로 재구성되었습니다.
- 우선순위는 CLI > config > preset으로 고정되었습니다.
- --preset이 실제 프로파일(BatchProfileManager)과 연결되었습니다.
- --config가 전체 AppSettings를 병합하며, 레거시 키 `advanced_processing` -> `advanced` 호환이 추가되었습니다.
- AI 핵심 CLI 옵션(분류/얼굴/스마트보정)이 추가되고 값 검증이 적용되었습니다.
- Watch 모드 관측성이 강화되었습니다.
  - 기존 processing_completed(filepath, success) 유지
  - 신규 processing_completed_detailed(filepath, success, status, message, wait_ms)
  - 신규 queue_metrics_updated(queue_size, avg_wait_ms)
- 재귀 감시에서 신규 하위 폴더 유입 시 초기 이미지 스캔을 즉시 수행합니다.
- Watch 최대 대기시간은 watch_mode.max_wait_seconds(기본 30.0)로 설정 가능합니다.
- 프로파일은 읽기 시 레거시 키를 허용하고, 저장/내보내기 시 표준 키 `advanced`로 정규화됩니다.
- 회귀 테스트가 보강되었습니다(수동 크롭 import, CLI 병합 우선순위, 재귀 감시 유입, max wait roundtrip).

> 참고: 전체 처리 selftest는 OpenCV(cv2) 설치가 필요합니다.


## 2026-03-02 Split Refactor Notes

- Split long modules into package paths:
  - `core/settings_model`, `core/advanced`, `core/face`, `core/image`, `core/batch`
  - `ui/main`, `ui/widgets/settings`, `i18n/catalog`
- Updated internal imports and packaging metadata (`photo_cropper.spec`) for the new package layout.
- Runtime behavior target remains unchanged: CLI options, settings schema, output rules, watch/batch contracts.
