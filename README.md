# 📸 사진 자동 자르기 (Photo Cropper) v9.0

스캔된 사진이나 배경 위에 놓인 사진을 자동으로 감지하여 정확하게 자르는 Python 애플리케이션입니다.

## ✨ v9.0 새 기능

### 🎨 UI/UX 개선
- **인디고 퍼플 액센트**: 새로운 색상 테마 (#818cf8)
- **에메랄드/로즈/앰버 팔레트**: 성공/오류/경고 색상 개선
- **그라데이션 토스트 알림**: 더 세련된 알림 UI
- **창 상태 저장**: 윈도우 크기/위치 자동 저장 및 복원

### ⚡ 성능 및 안정성
- **CLAHE 객체 캐싱**: 이미지 처리 속도 향상
- **커널 캐싱**: 모폴로지 연산 최적화
- **설정값 검증**: 저장 시 자동 범위 검증 (jpg_quality, canny 등)
- **리소스 정리 강화**: 종료 시 모든 ThreadPoolExecutor 안전 종료

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

### CLI 사용법 (v8.5+)

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
| `Ctrl+Z` | 실행 취소 |
| `Ctrl+Y` | 다시 실행 |
| `F11` | 전체화면 프리뷰 |
| `F5` | 파일 목록 새로고침 |
| `Ctrl+E` | 출력 폴더 열기 |
| `Ctrl+Q` | 종료 |

## ⚙️ 설정 옵션

### 출력 설정
| 항목 | 유효 범위 | 기본값 |
|------|----------|--------|
| JPG 품질 | 1-100 | 95 |
| PNG 압축 | 0-9 | 6 |
| WebP 품질 | 1-100 | 90 |

### 알고리즘 설정
| 항목 | 유효 범위 | 기본값 |
|------|----------|--------|
| Canny 최소 | 0-255 | 50 |
| Canny 최대 | 0-255 | 150 |
| CLAHE Clip Limit | 0.1-10.0 | 2.0 |
| 최소 면적 비율 | 0.01-0.99 | 0.1 |

### 워터마크 설정 (v8.5+)
- **텍스트 워터마크**: 텍스트, 폰트 크기, 색상, 그림자
- **이미지 워터마크**: PNG 이미지, 스케일, 투명도
- **위치**: 9방향 선택 (좌상단~우하단)
- **타일 모드**: 반복 패턴 워터마크

### 자동화 설정 (v8.5+)
- **폴더 감시**: 새 파일 자동 처리
- **스케줄러**: 예약 시간에 자동 배치 처리

## 📁 프로젝트 구조

```
photo_cropper/
├── main.py                  # 진입점
├── cli.py                   # CLI 인터페이스
├── core/
│   ├── image_processor.py   # 핵심 이미지 처리
│   ├── batch_processor.py   # 배치 처리 (ThreadPoolExecutor)
│   ├── settings.py          # 설정 관리 + 검증
│   ├── multi_photo_detector.py  # 다중 사진 감지
│   ├── watermark_processor.py   # 워터마크
│   ├── resize_processor.py      # 리사이즈
│   ├── folder_watcher.py        # 폴더 감시
│   ├── scheduler.py             # 스케줄러
│   └── history_manager.py       # Undo/Redo 히스토리
├── ui/
│   ├── main_window.py       # 메인 윈도우 (창 상태 저장/복원)
│   └── widgets/
│       ├── settings_panel.py
│       ├── preview_widget.py
│       └── ...
└── utils/
    └── file_helpers.py
```

## 🔧 빌드 (PyInstaller)

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
```

빌드된 실행 파일: `dist/SmartPhotoCropper_v9.exe`

## 📋 변경 이력

### v9.0 (2026-01)
- 🎨 **UI/UX 리팩토링** - 인디고 퍼플 테마 (#818cf8)
- 🎨 **새 색상 팔레트** - 에메랄드/로즈/앰버
- 🎨 **창 상태 저장/복원** - 윈도우 크기/위치 기억
- ⚡ **CLAHE/커널 캐싱** - 이미지 처리 속도 향상
- 🔒 **설정 검증** - 저장 시 자동 범위 클램핑
- 🔧 **리소스 정리 강화** - 안전한 종료 처리

### v8.5 (2026-01)
- ✨ 다중 사진 자동 감지
- ✨ 워터마크 시스템
- ✨ 이미지 리사이즈
- ✨ 폴더 모니터링 / 스케줄러
- ✨ CLI 인터페이스
- ✨ Undo/Redo 히스토리

### v7.2 (2025-12)
- 그라디언트 효과, 토스트 알림, 줌 슬라이더

## 📄 라이선스

MIT License

## 👨‍💻 기여

버그 리포트나 기능 제안은 Issues에 등록해 주세요.
