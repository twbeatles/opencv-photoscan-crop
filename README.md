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
- **이미 처리된 파일 건너뛰기**: 중복 처리 방지
- **다양한 출력 포맷**: JPG, PNG, WEBP 지원

### UI/UX
- **PyQt6 기반 현대적 UI**: 다크/라이트 테마, 그라디언트 효과
- **토스트 알림**: 작업 완료 시 슬라이드-인 애니메이션 알림
- **실시간 미리보기**: 마우스 휠 확대/축소, 줌 슬라이더 (10%~500%)
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
cd photo_cropper
pip install -r requirements.txt
```

## 🚀 사용법

### GUI 애플리케이션 실행

```bash
python run.py
```

### CLI 사용법 (v8.5 신규)

```bash
# 기본 사용
python -m photo_cropper.cli --input ./scans --output ./cropped

# 워터마크 추가
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# 리사이즈 적용
python -m photo_cropper.cli -i ./scans -o ./cropped --max-size 1920

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

### 출력 설정
- **출력 포맷**: JPG, PNG, WEBP
- **품질 조절**: JPG/WEBP 품질 (1-100), PNG 압축 (0-9)
- **그레이스케일/노이즈 제거/선명도 향상**

## 📁 프로젝트 구조

```
photo_cropper/
├── main.py                  # 진입점
├── cli.py                   # CLI 인터페이스 (v8.5)
├── core/
│   ├── image_processor.py   # 핵심 이미지 처리
│   ├── batch_processor.py   # 배치 처리
│   ├── settings.py          # 설정 관리
│   ├── multi_photo_detector.py  # 다중 사진 감지 (v8.5)
│   ├── watermark_processor.py   # 워터마크 (v8.5)
│   ├── resize_processor.py      # 리사이즈 (v8.5)
│   ├── folder_watcher.py        # 폴더 감시 (v8.5)
│   ├── scheduler.py             # 스케줄러 (v8.5)
│   └── history_manager.py       # 히스토리 관리 (v8.5)
├── ui/
│   ├── main_window.py
│   └── widgets/
│       ├── settings_panel.py
│       ├── preview_widget.py
│       ├── thumbnail_grid_widget.py  # 썸네일 그리드 (v8.5)
│       ├── fullscreen_viewer.py      # 전체화면 뷰어 (v8.5)
│       └── floating_action_button.py # FAB (v8.5)
├── i18n/                    # 다국어 지원 (v8.5)
│   └── translations.py
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

빌드된 실행 파일: `dist/SmartPhotoCropper_v85.exe`

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

