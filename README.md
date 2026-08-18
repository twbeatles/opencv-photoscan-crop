# 📸 Photo Cropper (사진 스캔 & 자동 크롭 도구)

🌐 [English](README_EN.md) | **한국어**

스캔된 앨범 사진, 문서, 복합 배경 위에 놓인 여러 장의 사진을 지능형 컴퓨터 비전 알고리즘으로 자동 감지하여 왜곡 없이 완벽하게 잘라내는(Crop & Deskew) 고성능 Python/PyQt6 애플리케이션입니다.

---

## 🌟 핵심 특징

- 🎯 **8단계 하이브리드 감지 엔진**: Canny, Background Mask, Adaptive Threshold, Sobel, Corner, Morph Gradient, Hough, LSD 사각형 검출을 결합하여 복잡한 배경에서도 정확한 사진 검출
- 🖼️ **다중 사진(Multi-Photo) 자동 분할**: 한 번에 스캔한 앨범 페이지에서 여러 장의 사진을 한 번에 감지하고, 개별 ROI 단일 재정제(Refine)를 거쳐 각각 분리 저장
- 📐 **지능형 원근 왜곡 보정 (Perspective Deskew)**: 기울어지거나 비스듬히 스캔된 사진을 4점 원근 변환으로 반듯하게 정렬
- 🤖 **AI 기반 자동 분류 & 얼굴 보정**: 인물/풍경/문서/흑백 자동 폴더 분류, DNN 얼굴 검출 기반 중심 크롭 및 눈 높이 수평 정렬, 스마트 노출/색감 자동 향상
- 🛠️ **전문가급 작업대 (GUI Workbench)**: 실시간 10%~500% 줌 미리보기, 외곽선 및 4점 직접 드래그 수동 보정, Undo/Redo (`Ctrl+Z`/`Ctrl+Y`), 히스토그램
- ⚡ **고속 배치 처리 & 자동화**: 멀티스레드 병렬 처리 (`--jobs`), 실시간 폴더 감시(Watch Mode), 예약 스케줄러, 처리 완료 파일 건너뛰기
- 📚 **통합 라이브러리 관리**: SQLite 기반 카탈로그, 썸네일 브라우징, 유사/중복 사진 검출, 처리 실패 사진 검토(Review) 및 원클릭 재작업

---

## 🚀 빠른 시작 (Quick Start)

### 1. 요구 사항 & 설치

- **Python**: 3.8 이상 권장
- **운영체제**: Windows 10/11, macOS, Linux

```bash
# 저장소 클론 후 opencv 디렉터리로 이동
cd opencv

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. GUI 실행

```bash
# 방법 A: 저장소 루트에서 실행
python ".\opencv\run.py"

# 방법 B: opencv 폴더 안에서 실행
cd opencv
python run.py
```

### 3. CLI 1줄 실행 (빠른 예시)

```bash
# 스캔 폴더의 사진들을 자동 감지하여 cropped 폴더로 일괄 크롭
python -m photo_cropper.cli -i ./scans -o ./cropped
```

---

## 🖥️ GUI 실전 사용 가이드

Photo Cropper의 GUI는 **좌측 사이드바 8대 메인 화면**과 **중앙 작업대**로 구성되어 있습니다.

```text
┌─────────────────┬────────────────────────────────────────────────────────┐
│  사이드바 메뉴  │  작업대 (Workbench)                                    │
│                 │  ┌──────────────────────────────────────────────────┐  │
│  📚 라이브러리  │  │ 입력/출력 경로 지정 | 장면 프리셋 | 멀티포토 토글 │  │
│  🛠️ 작업대 (기본)│  ├────────────────────────┬─────────────────────────┤  │
│  🔍 검토        │  │                        │ [📷 기본] [🔬 알고리즘] │  │
│  👥 중복 관리   │  │  실시간 미리보기 뷰    │ [🔧 처리] [📂 관리]     │  │
│  📋 작업 이력   │  │  (마우스 휠 줌/패닝,   │ [🤖 AI]                 │  │
│  📁 컬렉션      │  │   외곽선 드래그 보정)  │                         │  │
│  🍳 레시피      │  │                        │ 세부 파라미터 조절 패널 │  │
│  ⚙️ 설정 정보   │  │  📊 RGB 히스토그램     │                         │  │
│                 │  └────────────────────────┴─────────────────────────┘  │
└─────────────────┴────────────────────────────────────────────────────────┘
```

### 1. 기본 작업 흐름 (스캔 사진 크롭하기)

1. **이미지/폴더 불러오기**:
   - 상단 `입력 폴더`에서 `찾아보기`를 누르거나 탐색기에서 이미지/폴더를 프로그램 창으로 **드래그 앤 드롭**합니다.
2. **장면 프리셋(Scene Preset) 선택**:
   - 상단 퀵 셀렉터에서 스캔 환경에 맞는 프리셋을 선택합니다 (예: `Scanner (white bed)`, `Desk / table`, `Album page (multi)`).
3. **다중 사진 분할 모드 활성화 (필요 시)**:
   - 한 스캔에 여러 사진이 들어있는 경우 상단의 **`멀티포토` 스위치를 켭니다**.
4. **미리보기 & 수동 미세 조정**:
   - 자동 감지된 초록색 경계 상자를 확인합니다.
   - 경계가 어긋난 경우, 꼭짓점을 **마우스로 직접 드래그**하거나 클릭하여 4개 점을 수동 지정할 수 있습니다.
   - `Ctrl+Z` (실행 취소) / `Ctrl+Y` (다시 실행)를 지원합니다.
5. **일괄 크롭 실행**:
   - 하단 툴바의 `일괄 처리 시작`을 누르면 지정된 출력 폴더로 모든 사진이 고속 변환됩니다.

### 2. 메인 화면 구성 및 주요 기능

| 화면 | 주요 역할 및 활용 방법 |
|------|------------------------|
| **🛠️ 작업대 (Workbench)** | 사진을 불러와 경계를 확인하고, 실시간으로 파라미터를 변경하며 수동 보정 및 일괄 처리를 수행하는 핵심 작업 공간 |
| **📚 라이브러리 (Library)** | 처리 완료된 모든 사진을 SQLite DB 카탈로그로 보관. 날짜/태그별 썸네일 검색 및 필터링 지원 |
| **🔍 검토 (Review)** | 감지 신뢰도가 낮거나 경계 검출에 실패한 항목만 따로 모아 확인하고, 즉시 작업대로 불러와 재처리(Reprocess) |
| **👥 중복 관리 (Duplicates)** | 시각적 해시(pHash)를 통해 스캔 과정에서 중복 생성된 유사/동일 사진을 감지하여 안전하게 정리 |
| **📋 작업 이력 (Jobs)** | 과거에 실행된 배치 작업의 성공/실패/건너뜀 통계를 조회하고, **실패한 사진만 원클릭 재실행(Rerun Failed)** |
| **📁 컬렉션 (Collections)** | 사용자가 원하는 테마나 프로젝트별로 사진을 그룹화하고 가상 앨범으로 관리 |
| **🍳 레시피 (Recipes)** | 자주 사용하는 크롭 알고리즘, 리사이즈, 워터마크, 색감 설정을 템플릿으로 저장하고 원클릭 적용 |
| **⚙️ 설정 정보 (Settings)** | DB 용량 최적화(VACUUM), 썸네일 캐시 정리, 시스템 로그 확인 |

### 3. 작업대 5대 설정 패널 (Settings Panel)

- **📷 기본**: 후처리 기본값, UI 테마(다크/라이트), 언어(한국어/영어/일본어/중국어/스페인어), 출력 포맷(JPG/PNG/WEBP) 및 압축 품질, 기존 처리 파일 건너뛰기
- **🔬 알고리즘**: 감지 모드(`fast`, `balanced`, `accurate`), Canny 임계값, CLAHE 대비 개선, 배경 마스크 델타, 최소/최대 면적 비율, 원근 보정(Warp) 토글
- **🔧 처리**: 텍스트/이미지/타일 워터마크, 리사이즈(Fit, Fill, %, SNS 프리셋), 언샤프 마스크(선명도), 노이즈 제거, 흑백 변환, 자동 수평 보정(Deskew)
- **📂 관리**: 실시간 폴더 감시(Watch Mode), 지정 시각 자동 실행 스케줄러, 멀티스레드 작업자 수(1~64), 디버그 이미지(`_debug`) 저장 옵션
- **🤖 AI**: 카테고리 자동 분류(인물/풍경/문서/흑백), DNN 기반 얼굴 검출, 얼굴 중심 크롭 및 수평 정렬, 스마트 색감/노출 자동 보정

### 4. 주요 단축키

| 단축키 | 동작 |
|--------|------|
| `Ctrl + O` | 입력 폴더 열기 |
| `Ctrl + I` | 개별 이미지 열기 |
| `Ctrl + P` | 현재 이미지 미리보기 갱신 |
| `Ctrl + R` | 이미지 90도 시계방향 회전 |
| `Ctrl + Z` / `Ctrl + Y` | 설정 변경 및 경계 편집 실행 취소 / 다시 실행 |
| `F11` | 전체화면 미리보기 뷰어 전환 |
| `F5` | 파일 목록 새로고침 |
| `Ctrl + E` | 출력 폴더 탐색기로 열기 |
| `마우스 휠` | 미리보기 10% ~ 500% 확대 / 축소 |
| `마우스 우클릭 드래그` | 확대 상태에서 이미지 이동 (Panning) |

---

## ⌨️ CLI 실전 활용 가이드 (명령줄 사용법)

대량의 사진을 스크립트로 자동화하거나 서버/CI 환경에서 연동할 때 CLI를 사용할 수 있습니다.

```bash
# 기본 실행 형태 (opencv 디렉터리 내에서)
python -m photo_cropper.cli -i <입력경로> -o <출력경로> [옵션...]
```

### 1. 다중 사진(멀티포토) 분할 및 개별 폴더 저장

하나의 스캔 파일 안에 여러 장의 사진이 있는 경우, 이를 개별 사진으로 분리하고 각각 하위 폴더에 저장합니다.

```bash
# 한 스캔에서 여러 사진 분리 + ROI 단일 재정제 적용
python -m photo_cropper.cli -i ./album_scans -o ./out_photos --multi-photo --multi-photo-refine

# 분리된 사진을 원본 파일명 기반의 개별 하위 폴더(<파일명>_photos/)에 분리 저장
python -m photo_cropper.cli -i ./album_scans -o ./out_photos --multi-photo --multi-photo-separate-folders
```

### 2. 스캔 환경별 장면 프리셋 (Scene Preset) 활용

복잡한 수치를 조정하지 않고 스캔 대상 환경에 맞춰 최적의 파라미터를 자동 적용합니다.

```bash
# 흰색 배경 평판 스캐너에서 스캔한 사진
python -m photo_cropper.cli -i ./scans -o ./out --scene-preset scanner_white

# 나무 책상이나 복합 질감 바닥에 놓인 사진
python -m photo_cropper.cli -i ./desk_shots -o ./out --scene-preset desk_photo

# 검은색 천이나 어두운 배경에 놓인 사진
python -m photo_cropper.cli -i ./dark_bed -o ./out --scene-preset dark_background

# 앨범 페이지에 붙어있는 다중 사진 일괄 추출
python -m photo_cropper.cli -i ./album -o ./out --scene-preset album_multi

# A4/영수증 등 문서 스캔본 크롭
python -m photo_cropper.cli -i ./docs -o ./out --scene-preset document
```

### 3. AI 자동 카테고리 분류 & 폴더 라우팅

크롭된 사진을 AI가 분석하여 `인물`, `풍경`, `문서`, `흑백`, `기타` 폴더로 자동 분류하여 저장합니다.

```bash
# AI 분류 활성화 + 신뢰도 70% 이상 시 카테고리별 하위 폴더에 자동 분류
python -m photo_cropper.cli -i ./scans -o ./out --classify --classify-auto-folder --classify-min-confidence 0.7
```

### 4. AI 얼굴 감지 & 인물 중심 크롭 / 수평 정렬

인물 사진의 얼굴을 감지하여 사진의 중심에 배치하고 눈 높이를 기준으로 수평을 맞춥니다.

```bash
# DNN 모델 기반 얼굴 검출 + 얼굴 중심 크롭 + 눈 높이 기반 자동 회전
python -m photo_cropper.cli -i ./portraits -o ./out --face-detect --face-dnn --face-auto-center-crop --face-auto-rotate
```

### 5. 스마트 자동 화질 개선 (Smart Enhancement)

오래되어 색이 바래거나 노출이 부족한 스캔 사진의 밝기, 대비, 화이트 밸런스를 자동으로 복원합니다.

```bash
# 스마트 자동 화질 개선 (강도 80%)
python -m photo_cropper.cli -i ./old_scans -o ./out --smart-enhance --smart-strength 80
```

### 6. 고속 대량 배치 처리 & 중복 건너뛰기

```bash
# 8개 스레드 병렬 처리 + 하위 폴더 재귀 탐색 + 이미 처리된 파일 건너뛰기
python -m photo_cropper.cli -i ./all_scans -o ./out --jobs 8 --recursive --skip-processed
```

### 7. 포맷 변환, 리사이즈, 워터마크 및 메타데이터 보존

```bash
# WEBP 포맷 (품질 90) + 인스타그램 정방형 리사이즈 + 워터마크 + EXIF 보존
python -m photo_cropper.cli -i ./scans -o ./out \
  --format WEBP \
  --quality 90 \
  --resize instagram_square \
  --watermark "© 2026 Studio" \
  --preserve-metadata
```

> **리사이즈 지정 형식 지원:**
> - 비율: `--resize "50%"`
> - 해상도(가로x세로): `--resize "1200x900"`
> - 최대 변 길이: `--resize 1920` (또는 `--max-size 1920`)
> - SNS 프리셋: `--resize instagram_square`, `--resize facebook_cover`, `--resize a4`

### 8. 사전 정의된 프리셋(Preset) 또는 JSON 설정 파일 사용

```bash
# 등록된 프리셋 목록 확인
python -m photo_cropper.cli --list-presets

# 특정 프리셋 적용
python -m photo_cropper.cli -i ./scans -o ./out --preset "고화질 인물 스캔"

# JSON 설정 파일 적용 + 특정 옵션만 CLI에서 재정의
python -m photo_cropper.cli -i ./scans -o ./out --config ./my_settings.json --jobs 4
```

---

## 🔬 감지 엔진 알고리즘 & 튜닝 팁

### 8단계 하이브리드 파이프라인

| 단계 | 알고리즘 | 특징 및 역할 |
|:---:|:---|:---|
| **1** | Multi-Scale Canny Edge | 여러 해상도 스케일에서 에지를 추출하여 굵은 윤곽과 세밀한 경계선 동시 감지 |
| **2** | Background Mask | 이미지 모서리 색상 기반 배경-전경 분리 및 마스크 추출 |
| **3** | Adaptive Threshold | 조명이 불균일한 스캔본에서 국소 대비 기반 이진화 |
| **4** | Gradient Analysis (Sobel) | 밝기 그래디언트 강도를 분석하여 부드러운 경계 탐지 |
| **5** | Harris Corner Detection | 사진의 모서리(코너점)를 직접 검출하여 사각형 후보 구성 |
| **6** | Morphology Gradient | 텍스처가 있는 바닥(원목 책상, 패브릭)에서 외곽선 추출 |
| **7** | Hough Rectangle Fallback | 직선 성분 클러스터링을 통해 잘린 사각형 윤곽 추정 |
| **8** | LSD Rectangle Detector | Line Segment Detector 기반 정밀 사각형 검출 (`accurate` 모드) |

### 감지 모드 (`--detect-mode`) 선택 가이드

- `fast`: 조기 종료(Early Exit) 기법을 사용하여 최소한의 연산으로 고속 처리 (단순 단색 배경에 적합)
- `balanced` (기본값): Background Mask + Canny + 사각형 적합도 채점을 결합한 표준 안정 모드
- `accurate`: 모든 후보군을 추출한 후 형상비, 직교성, 면적비, 콘텐츠 대비(Contrast) 전역 재랭킹 수행 (복잡한 앨범/책상에 권장)

---

## ⚙️ 설정 파일 및 스토리지 구조

### 설정 파일 위치

- **Windows**: `%APPDATA%\PhotoCropper\settings.json`
- **macOS / Linux**: `~/.photo_cropper/photo_cropper_settings.json`

### SQLite 라이브러리 및 데이터베이스

- 라이브러리 카탈로그 DB: `%APPDATA%\PhotoCropper\library.db` (처리 이력, 메타데이터, pHash 해시, 컬렉션, 레시피 보관)
- 썸네일 캐시: `%APPDATA%\PhotoCropper\thumbnails\`

---

## 🛠️ 개발, 검증 및 빌드

### 1. 원클릭 통합 검증 (Verification Gate)

CI 및 PR 전 모든 린트, 타입, 유닛 테스트, 자가진단(selftest)을 일괄 실행합니다.

```powershell
# Windows PowerShell
powershell -NoProfile -File scripts/verify.ps1
```

```bash
# macOS / Linux
bash scripts/verify.sh
```

### 2. 개별 테스트 및 진단 실행

```bash
cd opencv

# Pytest 단위 테스트
python -m pytest tests/ -q

# 자가 진단 러너 (Selftest)
python -m photo_cropper.selftest

# 벤치마크 (성능 및 정확도 측정)
python -m photo_cropper.benchmark
```

### 3. 독립 실행 파일 빌드 (PyInstaller)

```bash
cd opencv
pip install pyinstaller

# 폴더형 안정 빌드 (권장)
pyinstaller photo_cropper.spec --clean

# 단일 파일 실행 빌드 (실험적)
pyinstaller photo_cropper_onefile.spec --clean
```

- 생성된 실행 파일: `opencv/dist/PhotoCropper_v9/PhotoCropper_v9.exe`

---

## 📄 라이선스 & 기여

- **License**: [MIT License](LICENSE)
- **Contribution**: 버그 제보 및 기능 제안은 GitHub Issues에 남겨주세요. 개발 참여 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md) 및 [AGENTS.md](AGENTS.md)를 참고하시기 바랍니다.
