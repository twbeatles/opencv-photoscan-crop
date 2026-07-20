# 📸 Photo Cropper

🌐 [English](README_EN.md) | 한국어

스캔된 사진이나 배경 위에 놓인 사진을 자동으로 감지하여 정확하게 자르는 Python 애플리케이션입니다.

---

## 주요 기능

### 자동 사진 감지 & 크롭
- **8단계 지능형 감지 알고리즘**: Canny~LSD + NMS/GrabCut 정제로 높은 검출 성공률
- **장면 프리셋 / 간단 모드**: 스캐너·책상·앨범 등 원클릭 튜닝, 고급 탭 숨김
- **다중 사진 자동 감지**: 한 스캔에서 여러 사진 분리 + ROI 단일 탐지 재정제(기본 ON)
- **원근 보정**: 비틀린 사진을 자동으로 정렬 (기본값 ON)
- **수동 경계 편집**: 자동 감지 실패·저신뢰 시 외곽선 점 드래그 또는 4점 직접 지정

### 배치 처리
- **폴더 단위 일괄 처리**: 대량 이미지를 한 번에 처리 (예상 남은 시간 표시)
- **이미 처리된 파일 건너뛰기**: 중복 처리 방지
- **재귀 처리**: 하위 폴더까지 포함한 일괄 처리 지원
- **실패 파일 별도 보정**: 경계 탐지 실패 파일만 수동 보정 모드로 재편집

### 후처리 옵션
- **워터마크**: 텍스트/이미지 워터마크, 9방향 위치, 타일 모드
- **리사이즈**: Fit/Fill/비율/최대크기 모드, Instagram·Facebook·A4 등 프리셋
- **이미지 보정**: 그레이스케일, 노이즈 제거, 선명도 향상, 얼굴 자동 보정
- **자동 분류 저장**: AI 분류로 인물/풍경/문서/흑백/기타 하위 폴더에 자동 저장
- **메타데이터 보존**: EXIF/ICC 정보 복사

### 관리 기능
- **라이브러리**: 처리된 사진을 SQLite 카탈로그로 관리
- **중복 감지**: 동일/유사 사진 탐지 및 정리
- **컬렉션 / 레시피**: 처리 프리셋 저장 및 재사용
- **작업 이력**: 배치 처리 결과 추적

### 자동화
- **Watch Mode**: 폴더를 감시해 새 파일을 자동으로 처리
- **스케줄러**: 지정 시각에 자동 배치 실행
- **CLI 지원**: 명령줄에서 스크립트/파이프라인 연동

### UI/UX
- **PyQt6 기반 현대적 UI**: 다크/라이트 테마
- **실시간 미리보기**: 마우스 휠 확대/축소, 줌 슬라이더 (10%~500%)
- **런타임 다국어 전환**: 한국어·영어·일본어·중국어·스페인어 (앱 재시작 불필요)
- **드래그 앤 드롭**: 폴더나 이미지를 직접 끌어다 놓기
- **Undo/Redo**: `Ctrl+Z`/`Ctrl+Y`로 설정 변경·수동 편집 되돌리기

---

## 감지 알고리즘

| 단계 | 알고리즘 | 설명 |
|------|----------|------|
| 1단계 | Multi-Scale Canny Edge | 다중 스케일 에지 검출 |
| 2단계 | Background Mask | 배경-전경 분리 기반 후보 생성 |
| 3단계 | Adaptive Threshold | 적응형 이진화 |
| 4단계 | Gradient Analysis (Sobel) | 그래디언트 분석 |
| 5단계 | Harris Corner Detection | 코너 검출 (선택적) |
| 6단계 | Morphology Gradient | 형태학 경계 + Otsu (텍스처 배경) |
| 7단계 | Hough Rectangle Fallback | 직선 클러스터 기반 사각형 추정 |
| 8단계 | LSD Rectangle | Line Segment Detector 기반 사각형 (accurate) |

- **fast / balanced**: 조기 종료로 처리 속도 우선
- **accurate**: 전 단계 후보 수집 → NMS → 전역 재랭킹 → 콘텐츠 대비 → GrabCut 정제
- **장면 프리셋**: 워크벤치·알고리즘 탭·CLI `--scene-preset`
- **멀티포토 ROI 재정제**: 각 사진에 단일 탐지 재실행 (기본 ON)
- 상세 파이프라인: [`docs/detection-pipeline.md`](docs/detection-pipeline.md)

---

## 설치

**요구 사항**
- Python 3.8 이상
- Windows / macOS / Linux

```bash
pip install -r requirements.txt
```

---

## 사용법

### GUI 실행

```bash
python run.py
```

### CLI 사용법

```bash
# 기본 사용
python -m photo_cropper.cli --input ./scans --output ./cropped

# 정확도 우선 모드
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate

# 워터마크 추가
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# 리사이즈 (비율 / 해상도 / 프리셋)
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "50%"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "1200x900"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize instagram_square

# 한 스캔에서 여러 사진 분리
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo

# 장면 프리셋 (스캐너/책상/앨범 등 자동 튜닝)
python -m photo_cropper.cli -i ./scans -o ./cropped --scene-preset scanner_white

# 앨범 페이지 다중 사진 + ROI 재정제
python -m photo_cropper.cli -i ./scans -o ./cropped --scene-preset album_multi --multi-photo-refine

# 여러 사진 분리 + 각각 하위 폴더에 저장
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-separate-folders

# 메타데이터 보존
python -m photo_cropper.cli -i ./scans -o ./cropped --preserve-metadata

# 하위 폴더 재귀 처리 (output은 input 외부 경로로 지정)
python -m photo_cropper.cli -i ./scans -o ../cropped --recursive

# 이미 처리된 파일 건너뛰기
python -m photo_cropper.cli -i ./scans -o ./cropped --skip-processed

# 병렬 처리 (스레드 수 지정)
python -m photo_cropper.cli -i ./scans -o ./cropped --jobs 6

# 옵션 전체 보기
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

---

## 설정

### 설정 파일 위치

- **Windows**: `%APPDATA%/PhotoCropper/settings.json`
- **macOS / Linux**: `~/.photo_cropper/photo_cropper_settings.json`

### 알고리즘 설정

| 설정 | 설명 |
|------|------|
| 감지 모드 | `fast` / `balanced` / `accurate` — 속도/정확도 트레이드오프 |
| Canny 임계값 | 에지 감지 민감도 (0–255) |
| CLAHE | 저대비 이미지 향상 |
| 정밀 튜닝 | 최소/최대 면적 비율, 배경 마스크 델타, 적응형 블록 크기 등 |
| 원근 보정 | ON(기본): 4점 원근 변환 / OFF: 축정렬 Bounding Box 크롭 |
| 감지 디버그 저장 | `_debug` 폴더에 에지/마스크/후보 오버레이 저장 (실패 원인 분석용) |

### 출력 설정

| 설정 | 설명 |
|------|------|
| 출력 포맷 | JPG / PNG / WEBP |
| 품질 | JPG/WEBP: 1–100 / PNG: 압축 0–9 |
| 메타데이터 | EXIF/ICC 복사 (실패 시 저장은 계속 진행) |
| 이미지 보정 | 그레이스케일, 노이즈 제거, 선명도 향상 |
| 자동 분류 | AI 신뢰도 조건 충족 시 카테고리 하위 폴더에 저장 |

### 워터마크 설정

- **텍스트 워터마크**: 텍스트, 폰트 크기, 색상, 그림자
- **이미지 워터마크**: PNG 이미지, 스케일, 투명도
- **위치**: 좌상단~우하단 9방향
- **타일 모드**: 반복 패턴 워터마크

### 리사이즈 설정

- **모드**: 맞춤(Fit), 채우기(Fill), 비율(%), 최대 크기
- **프리셋**: Instagram, Facebook, A4 등

### 자동화 설정

- **Watch Mode**: 폴더를 감시해 새 파일 자동 처리
  - 재귀 Watch Mode에서는 출력 폴더를 입력 폴더 외부로 지정해야 합니다
- **스케줄러**: 지정 시각(`HH:MM`)에 자동 배치 실행
  - `once` 타입: 다음 도래 HH:MM에 1회 실행 (날짜 지정 없음)

---

## 프로젝트 구조

```text
photo_cropper/
├── main.py
├── cli.py
├── selftest.py
├── core/
│   ├── image/          # 크롭 알고리즘
│   ├── batch/          # 배치 처리
│   ├── library/        # 라이브러리 카탈로그 (SQLite)
│   ├── jobs/           # 작업 이력
│   ├── recipes/        # 레시피/프리셋
│   ├── settings_model/ # 설정 dataclass
│   ├── advanced/       # 고급 이미지 처리
│   ├── watch_mode/     # Watch Mode
│   ├── multi_photo_detector.py
│   ├── watermark_processor.py
│   ├── resize_processor.py
│   └── scheduler.py
├── ui/
│   ├── main/           # 메인 윈도우
│   └── widgets/        # UI 컴포넌트
├── i18n/catalog/       # 다국어 번역
└── utils/
```

---

## 빌드 (PyInstaller)

```bash
pip install pyinstaller

# 안정 빌드 (권장)
pyinstaller photo_cropper.spec --clean

# 단일 파일 실험 빌드
pyinstaller photo_cropper_onefile.spec --clean
```

**출력 경로**
- 안정 빌드: `dist/PhotoCropper_v9/PhotoCropper_v9.exe`
- 단일 파일: `dist/PhotoCropper_v9_single.exe`

> Windows 앱 제어 정책 환경에서는 onedir 빌드(`photo_cropper.spec`)가 더 안정적입니다.

---

## 라이선스

MIT License

## 기여

버그 리포트나 기능 제안은 Issues에 등록해 주세요.
