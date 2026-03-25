# 📸 사진 자동 자르기 (Photo Cropper) v9.0

🌐 [English](README_EN.md) | 한국어

스캔된 사진이나 배경 위에 놓인 사진을 자동으로 감지하여 정확하게 자르는 Python 애플리케이션입니다.

> 저장소 루트에서 실행/빌드할 때는 실제 앱 디렉터리인 `;opencv/` 기준 경로를 사용하세요.

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

### 🛡️ 처리 정합성 업데이트 (2026-03)
- **원근 보정 기본값 ON**: `advanced.perspective_correct=True`가 기본 동작이며, OFF 시 4점의 축정렬 bounding box 크롭으로 동작
- **수동 추출/배치 파이프라인 일치**: 수동 “편집 저장 추출”도 배치와 동일한 후처리/분류 라우팅/네이밍 규칙을 재사용
- **저장 경로 강건성 강화**: 확장자 누락/오염 경로에서도 `output_format` 기반 인코더로 저장 fallback
- **메타데이터 보존(best-effort)**: EXIF/ICC 복사 실패 시 경고만 남기고 저장 자체는 성공 처리
- **멀티포토 하위 폴더 저장**: `separate_output_folders=true` 시 `<원본파일명>_photos/` 구조로 저장
- **멀티포토 dedup 민감도 연동**: `merge_distance`가 중복 억제 단계에 반영
- **로컬 처리 이력 인덱스 도입**: 출력 폴더의 `.photocropper/processed_index.json`로 `skip_processed` 판정 재현성 강화
- **분류 폴더명 사용자 설정**: 기본 한글 폴더(`인물/풍경/문서/흑백/기타`) 유지 + 설정 패널에서 카테고리별 커스터마이즈 지원
- **Watch 준비/재시도 공정성 개선**: not-ready 파일 재큐잉을 공정 큐 정책으로 조정하고 timeout/read 실패 상태코드 정합성 강화
- **스케줄러 런타임 연결**: UI의 scheduler 설정이 앱 실행 중 실제 자동 배치 트리거로 동작
- **Watch background worker 전환**: Watch Mode 처리 콜백이 `AutoProcessor`의 단일 background worker에서 순차 실행되고, readiness timeout/retry도 `AutoProcessor`가 전담
- **EXIF Orientation 재기록**: `preserve_metadata` 저장 시 EXIF/ICC는 유지하되 Orientation은 항상 `1`로 다시 써서 이중 회전을 방지
- **멀티포토 partial_success 도입**: 일부 출력만 저장된 경우 `partial_success`로 구분되고, 배치 완료/Watch 토스트/processing log summary에 별도 집계
- **멀티포토 공통 로더 통일**: 멀티포토 입력도 `ImageProcessor.load_image()`를 사용해 EXIF orientation 정규화 동작을 단일 사진/수동 저장 경로와 일치
- **배치 재진입 차단**: 실행 중인 batch session은 새 session으로 덮어쓰지 않으며 `start_processing()`/`retry_failed_files()`가 중복 시작을 막음
- **수동 편집 preview/save crop 일치**: 수동 contour 편집 직후 미리보기와 실제 저장이 동일한 crop 규칙을 공유
- **재귀 Watch 출력 경로 가드**: 재귀 감시에서는 output 폴더가 input root 내부에 있으면 시작을 차단
- **Watch 실패 분류 비활성화**: Watch 처리 시 `move_failed_files`는 런타임 snapshot에서 강제로 꺼져 `_failed` 재처리 루프를 방지
- **Watch overwrite 재처리**: 같은 경로를 덮어쓴 경우에도 size/mtime signature가 바뀌면 `fileChanged` 경로로 다시 처리
- **processed index v2 partial 정책**: 인덱스 레코드에 `status=success|partial`를 저장하고, `partial`은 경고만 남긴 뒤 재처리
- **Retry Failed 경로 정규화**: 일반 배치와 동일하게 빈 output path를 `<input>/output_cropped`로 보정 후 검증

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
| 2단계 | Background Mask | 배경-전경 분리 기반 후보 생성 |
| 3단계 | Adaptive Threshold | 적응형 이진화 |
| 4단계 | Gradient Analysis (Sobel) | 그래디언트 분석 |
| 5단계 | Harris Corner Detection | 코너 검출 (선택적) |
| 6단계 | Hough Rectangle Fallback | 직선 클러스터 기반 사각형 추정 |

- `fast`/`balanced` 모드는 기존 조기 종료 동작을 유지합니다.
- `accurate` 모드는 1~6단계 후보를 모두 수집한 뒤 전역 재랭킹으로 최종 후보를 선택합니다.

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
# 저장소 루트에서 실행
python ".\\;opencv\\run.py"

# 또는 앱 폴더로 이동 후 실행
cd ";opencv"
python run.py
```

### CLI 사용법

```bash
# 저장소 루트에서 CLI 실행
cd ";opencv"

# 기본 사용
python -m photo_cropper.cli --input ./scans --output ./cropped

# 정확도 우선 + 디버그 저장
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate --debug-detect

# 정밀 튜닝 파라미터 지정 (CLI override)
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate \
  --min-area-ratio 0.08 --max-area-ratio 0.97 \
  --bg-mask-delta 34 --adaptive-block-size 19 --adaptive-c 3.0

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

# 멀티포토 세부 옵션
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-merge-distance 80 --multi-photo-separate-folders

# 메타데이터 보존 + 원근 보정 OFF
python -m photo_cropper.cli -i ./scans -o ./cropped --preserve-metadata --no-perspective-correct

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

> 참고: 재귀 Watch Mode에서는 출력 폴더를 입력 폴더 내부에 둘 수 없습니다. 기본 출력값(`<input>/output_cropped`)을 그대로 쓰려면 재귀 감시를 끄거나, 출력 폴더를 입력 루트 밖으로 지정하세요.

### 알고리즘 설정
- **Canny 임계값**: 에지 감지 민감도 조절 (0-255)
- **CLAHE**: 저대비 이미지 향상
- **다중 스케일**: 다양한 크기의 사진 감지
- **코너 검출**: 추가적인 정확도 향상
- **검출 모드 (fast/balanced/accurate)**: 속도/정확도 트레이드오프 프리셋
- **정밀 튜닝 (UI + CLI)**:
  - `min_area_ratio`, `max_area_ratio`
  - `bg_mask_delta`
  - `adaptive_block_size`, `adaptive_c`
- **검출 디버그 저장**: `_debug` 폴더에 엣지/마스크/후보 오버레이/`meta.json` 저장 (실패 원인 분석용)
- **원근 보정 기본값**: 기본 ON, OFF 시 원근 warp 대신 축정렬 bbox 크롭

### 출력 설정
- **출력 포맷**: JPG, PNG, WEBP
- **품질 조절**: JPG/WEBP 품질 (1-100), PNG 압축 (0-9)
- **메타데이터 보존**: EXIF/ICC best-effort 복사 (실패 시 저장은 계속 진행)
- **그레이스케일/노이즈 제거/선명도 향상**
- **자동 분류 저장(선택)**: 분류 신뢰도 조건 충족 시 카테고리 하위 폴더에 저장

> 참고: `skip processed`는 출력 폴더 로컬 인덱스(`.photocropper/processed_index.json`)를 우선 사용합니다.
> 인덱스 키는 `source_path + size + mtime_ns + pipeline_signature`이며, 멀티포토는 `outputs[]`로 다중 결과를 기록합니다.
> `partial_success`는 인덱스에 `status=partial`로 남기되, 다음 실행에서 full skip하지 않고 경고 후 재처리합니다.
> 인덱스가 비활성/오류일 때만 파일명 기반 fallback 탐지와 제한 경고가 적용됩니다.
> 자동 분류 하위 폴더(기본 `인물/풍경/문서/흑백/기타`, 사용자 지정 가능)와 멀티포토 하위 폴더(`*_photos`)도 탐지 대상에 포함됩니다.

## 🧪 안정성 체크 포인트

- **문법 검증**: `cd ";opencv" && python -m compileall -q photo_cropper`
- **타입 검사**: `pyright --project .\\pyrightconfig.json`
- **전체 selftest**: `cd ";opencv" && python -m photo_cropper.selftest`
- **CLI 스모크 테스트**: `cd ";opencv" && python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-separate-folders --preserve-metadata --no-perspective-correct --skip-processed`
- **워치 모드 검증**: GUI에서 Watch Mode 시작 후 신규 파일 투입 시 배치와 동일한 출력(워터마크/리사이즈/분류 폴더) 확인
- **재귀 Watch 안전성 검증**: recursive watch + output inside input 조합에서 시작이 차단되는지 확인
- **Watch overwrite 검증**: 같은 경로 이미지를 덮어쓴 뒤 size/mtime이 바뀌면 재큐잉되고, 변동이 없으면 중복 처리되지 않는지 확인
- **수동 preview/save parity 검증**: `advanced.perspective_correct=false`에서 수동 편집 직후 preview와 실제 저장 결과 shape이 일치하는지 확인
- **스케줄러 검증**: `watch_mode.scheduler_enabled=true` 상태에서 예약 시각 도달 시 자동 배치 시작/중복 실행 skip 확인
- **유니코드 경로 검증**: 한글 경로의 워터마크 이미지 파일을 지정해 저장 성공 여부 확인
- **취소 검증**: 멀티스레드 배치 실행 중 중단 요청 시 통계/상태 정합성 확인 및 CLI 종료코드 `130` 확인
- **벤치마크 하네스 검증**:
  - `cd ";opencv" && python -m photo_cropper.benchmark --images ./benchmark/images --labels ./benchmark/labels.json --report ./benchmark/report.json --detect-mode accurate`
  - 라벨 포맷: `;opencv/BENCHMARK_LABEL_FORMAT.md` 참조 (실사진 데이터셋은 저장소 미포함)

## 📁 프로젝트 구조

```text
;opencv/
├── run.py
├── photo_cropper.spec
└── photo_cropper/
    ├── main.py
    ├── cli.py
    ├── benchmark.py
    ├── core/
    │   ├── image/processor.py
    │   ├── batch/processor.py
    │   ├── settings_model/app_settings.py
    │   ├── multi_photo_detector.py
    │   ├── watermark_processor.py
    │   ├── resize_processor.py
    │   ├── folder_watcher.py
    │   ├── scheduler.py
    │   └── history_manager.py
    ├── ui/
    │   ├── main/window.py
    │   ├── main/models.py
    │   ├── main/actions/
    │   ├── main/builders/
    │   └── widgets/settings/panel.py
    ├── i18n/catalog/manager.py
    └── utils/file_helpers.py
```

## 🔧 빌드 (PyInstaller)

### 실행 파일 생성

```bash
# 의존성 설치
pip install pyinstaller

# 저장소 루트에서 빌드
pyinstaller ".\\;opencv\\photo_cropper.spec" --clean
```

빌드된 실행 파일: `dist/PhotoCropper_v9.exe`

### 추가 경량화 (UPX)

[UPX](https://github.com/upx/upx/releases)를 설치하면 실행 파일 크기가 약 30-50% 감소합니다:

1. UPX 다운로드 및 압축 해제
2. `upx.exe`를 시스템 PATH에 추가
3. 다시 빌드: `pyinstaller ".\\;opencv\\photo_cropper.spec" --clean`

### 빌드 최적화 내용

| 항목 | 설명 |
|------|------|
| 단일 파일 | onefile 모드로 단일 .exe 생성 |
| 불필요 모듈 제외 | matplotlib, scipy, pandas, tkinter 등 |
| OpenCV/Qt 경량화 | `cv2.gapi` 제외 및 불필요한 Qt/OpenCV 런타임 바이너리 선별 제외 |
| NumPy 경량화 | 테스트/문서 파일 제거 |
| UPX 압축 | 실행 파일 압축 (~40% 크기 감소) |

## 📋 변경 이력

### v9.0 통합 개선 업데이트 (2026-03-05)
- ✨ `skip_processed` 로컬 인덱스(`.photocropper/processed_index.json`) 추가 및 Batch/Watch/수동 추출 공통 적용
- ✨ 분류 폴더명 사용자 설정(`ClassificationSettings.category_folders`) 추가, 기본 한글 폴더 호환 유지
- ✨ 스케줄러 UI 설정과 런타임 자동 배치 트리거 연결(앱 실행 중)
- 🛡️ Watch 준비/재시도 정책 개선(stat/read 실패 만료 처리, 공정 큐 재시도, retry_count 로그)
- 🛡️ 멀티스레드 취소 시 완료 future drain + 미실행 작업 `CANCELLED` 반영으로 통계 정합성 강화
- 🛡️ Watch 완료 토스트 중복 제거(`processing_completed_detailed` 중심)
- 🛡️ CLI 취소 종료코드 `130`, 실패 `1`, 정상 `0`으로 정렬
- 🛡️ 프로파일 적용 경로를 `to_dict + deep-merge + AppSettings.from_dict`로 일원화

### v9.0 정밀도 개선 패치 (2026-03-08)
- 🎯 `accurate` 모드 전용 전역 재랭킹(1~6단계 후보 수집 후 점수 기반 선택) 추가
- 🎯 edge-support 점수 입력을 스테이지 마스크와 분리해 별도 기준 edge map으로 고정
- 🎯 면적 점수(plateau), 종횡비 점수(quad 변 길이 기반), Hough 각도 bin 클러스터링 개선
- 🎯 멀티포토 `DetectedPhoto.quad` 추가 및 perspective crop 우선 처리(유효하지 않으면 bbox fallback)
- 🎯 `merge_distance` 실반영 + `IoU + center distance + edge gap` 복합 dedup
- 🎯 EXIF orientation 정규화(Pillow 우선, OpenCV fallback) 및 얼굴 회전각 `primary_face` 기준화
- 🎯 정밀 튜닝 파라미터 5종 UI/CLI 노출
- 🎯 실사진 벤치마크 하네스(`photo_cropper.benchmark`) 및 라벨 템플릿/문서 추가

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

## 2026-03-16 정합성 점검 메모

- 저장소 루트 `pyrightconfig.json`과 `.editorconfig`를 추가해 루트/앱 폴더 어디서 실행해도 동일한 타입 검사와 UTF-8 규칙을 사용하도록 정렬했습니다.
- `pyright --project .\pyrightconfig.json` 및 `cd ";opencv" && pyright --project pyrightconfig.json` 모두 0 errors / 0 warnings를 확인했습니다.
- `cd ";opencv" && python -m photo_cropper.selftest` 기준 `SELFTEST OK`를 확인했습니다.
- `accurate` 모드의 no-photo false positive 회귀를 줄이기 위해 stage-specific candidate filter를 추가했고, 멀티포토 perspective crop 크기 계산은 quad point order를 정규화하도록 수정했습니다.
- `photo_cropper.spec` hidden import에 `ui.main.preview_worker`를 추가했고, 이번 정합성 수정으로 추가된 런타임 외부 의존성은 없습니다.

## 2026-03-25 안정화 구현 메모

- 수동 contour 편집 preview는 `core.manual_extract.crop_manual_contour()`를 공유하도록 정리되어, `perspective_correct=false`일 때도 실제 저장과 동일한 axis-aligned crop을 보여줍니다.
- `ui/widgets/preview_widget.py`의 contour redraw는 seed(1~3점)와 정상 contour(4점)를 분리해 `UnboundLocalError`와 seed 가이드 일부 미표시 문제를 제거했습니다.
- 재귀 Watch Mode는 output path가 input root 내부면 시작을 차단하고, 직접 실행 경로에서도 watch/batch/manual 상호 배제를 강제합니다.
- Watch 처리 시 settings snapshot에서 `move_failed_files=False`를 강제해 `_failed` 재처리 루프를 막고, `FolderWatcher.fileChanged`는 size/mtime signature가 바뀐 경우에만 overwrite 재처리를 큐잉합니다.
- processed index는 v2로 올라가며 `status=success|partial`를 저장합니다. legacy 레코드는 기본 `success`로 읽고, `partial` 레코드는 skip 대신 경고 후 재처리합니다.
- `retry_failed_files()`는 일반 배치 시작과 동일하게 빈 output path를 `<input>/output_cropped`로 보정하고 출력 디렉터리 검증 후 진행합니다.
- 검증: `cd ";opencv" && python -m compileall -q photo_cropper`, `cd ";opencv" && python -m photo_cropper.selftest`

## 2026-03-04 정합성 점검 메모

- `pyright --project pyrightconfig.json` 기준 0 errors / 0 warnings를 확인했습니다.
- `QWidget` 오버라이드 이벤트 시그니처는 PyQt6 스텁 기준으로 이벤트 타입과 파라미터명(`a0`)을 정렬했고, window timer service는 non-optional로 승격해 Pylance 경고를 제거했습니다.
- PyInstaller spec hidden import에 `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`를 명시해 패키징 안정성을 보강했습니다.

## 2026-03-09 UI/MainWindow 정합성 메모

- `ui/main/window.py`는 composition root로 축소되었고, 실제 동작은 `ui/main/actions/` 계층이 담당합니다.
- 위젯 생성은 `ui/main/builders/`로 분리되었고, shared context는 `ui/main/models.py`에 정리되었습니다.
- `photo_cropper.spec` hidden import는 새 canonical 경로(`ui.main.actions.*`, `ui.main.builders.*`, `ui.main.models`)와 호환용 shim 경로를 함께 포함하도록 갱신했습니다.
- `ui.main.batch_actions` 등 기존 평면 import 경로는 호환용 re-export shim으로 유지됩니다.
