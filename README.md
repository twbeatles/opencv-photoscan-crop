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
- **유니코드 이미지 로딩 안정화**: core/UI 이미지 로딩을 `utils.image_io.load_image_unicode()`로 통일하고 워터마크 경로도 같은 안전 로딩 패턴을 사용
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

### 🛡️ 구현 정합성 업데이트 (2026-04)
- **재귀 Batch/CLI/Watch 안전 가드**: recursive 처리에서는 output이 input root 내부면 시작을 차단
- **재귀 스캔 내부 산출물 제외**: `output_root`, `_failed`, `backup`, `.photocropper`를 자동 제외
- **상대경로 보존 저장 규칙**: recursive 입력은 output, `_failed`, `*_photos`에서 입력 기준 상대 경로를 유지
- **partial_success 집계 정렬**: GUI/CLI summary가 `success`, `partial_success`, `failed`, `skipped`를 동일 규칙으로 집계
- **CLI `--strict-partial` 추가**: 기본은 partial을 success 계열로 처리하고, strict일 때만 종료코드 1 반환
- **분류 모델 정규화**: legacy `custom`은 `advanced` alias로 유지되며 UI는 `basic/advanced`만 노출
- **Scheduler `once` 의미 명확화**: 날짜 없는 "다음 도래 HH:MM 1회 실행" 의미로 고정
- **Python locale 카탈로그 전환**: 번역 원본을 `photo_cropper/i18n/catalog/locales/*.py`로 단일화하고 런타임 언어 전환 경로를 통일
- **메인 UI 런타임 재번역**: 저장된 언어를 초기 UI 생성 전에 적용하고, 장수명 위젯/메뉴/툴바는 언어 변경 즉시 재번역
- **안전한 경로 조각 검증**: 자동 분류 폴더명과 naming prefix/suffix는 단일 path segment 규칙으로 즉시 검증
- **분류 폴더 locale 기본값**: 분류 폴더 입력을 비워두면 현재 UI 언어 기본 폴더명을 사용하고, 구 기본 한글값은 자동 마이그레이션
- **Unicode-safe 이미지 로더 통일**: core/UI 이미지 로딩은 `utils.image_io.load_image_unicode()`를 사용하며 `cv2.imread` 직접 호출을 제거
- **CLI 설정 검증 강화**: config/preset에서 잘못된 naming prefix/suffix 또는 분류 폴더명이 들어오면 처리 시작 전 exit code `2`로 중단
- **processed index signature 보강**: 언어별로 해석된 분류 폴더명과 백업 옵션이 `skip_processed` 판정 signature에 포함
- **출력명 예약 통합**: 일반/분류/멀티포토 저장 경로가 batch 단위 thread-safe reservation을 공유해 동시 저장 충돌을 방지
- **Scheduler once 보존**: busy/no files/invalid config skip은 `once` 예약을 소비하지 않고, 실제 배치 시작 시에만 비활성화
- **Library/SQLite 안정화**: 라이브러리 폴더 가져오기는 background thread에서 진행되고 SQLite는 WAL, foreign key, busy timeout을 설정
- **Undo/Redo 연결**: 세션 내 설정 변경, 수동 crop, 라이브러리/컬렉션/레시피 수동 변경을 `Ctrl+Z`/`Ctrl+Y`로 되돌릴 수 있음

### 🗂️ 관리 셸 및 리팩터링 업데이트 (2026-04-19)
- **관리 셸 중심 UX**: 메인 화면이 `라이브러리`, `워크벤치`, `검토`, `중복`, `작업`, `컬렉션`, `레시피`, `설정` 섹션 중심으로 확장
- **카탈로그/작업 이력 계층 도입**: 관리앱 관련 핵심 로직이 `photo_cropper/core/library/`, `core/jobs/`, `core/recipes/`로 정리
- **SOLID 기반 분할 리팩터링**: 기존 대형 파일을 얇은 파사드 + 책임별 내부 모듈 구조로 재편
- **패키징 안정화**: PyInstaller spec이 분할된 하위 모듈들을 자동 수집하도록 보강
- **검증 기준 갱신**: `compileall`, `selftest`와 함께 `pyright`를 기본 정합성 점검 항목으로 포함

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
- **런타임 다국어 전환**: 한국어/영어/일본어/중국어/스페인어를 앱 재시작 없이 주요 UI에 즉시 반영
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

# recursive 입력 + partial 엄격 종료 정책
python -m photo_cropper.cli -i ./scans -o ../cropped --recursive --strict-partial

# legacy custom 값도 허용되지만 내부적으로 advanced로 처리
python -m photo_cropper.cli -i ./scans -o ./cropped --classify --classify-model custom

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
| `Ctrl+Z` | 실행 취소 (세션 내 수동 작업) |
| `Ctrl+Y` | 다시 실행 (세션 내 수동 작업) |
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

#### 언어/파일명 안전성
- **실시간 언어 전환**: 설정 패널 언어 변경 시 메인 메뉴, 툴바, 상태바, 진행창 등 장수명 UI가 즉시 갱신됩니다.
- **번역 카탈로그 검증**: locale key coverage와 placeholder 일치성은 selftest에서 검사됩니다.
- **안전한 분류 폴더명**: 자동 분류 폴더명은 폴더 구분자, `..`, 드라이브/UNC 경로, Windows 예약어, 제어문자를 허용하지 않습니다.
- **안전한 naming 규칙**: prefix/suffix도 동일한 규칙으로 검증되며 invalid 상태에서는 설정 emit/자동 미리보기가 차단됩니다.
- **locale 기본값 sentinel**: 분류 폴더 입력을 비워두면 현재 UI 언어 기본값을 사용합니다.

#### 자동화 설정
- **폴더 감시**: 새 파일 자동 처리
- **스케줄러**: 예약 시간에 자동 배치 처리

> 참고: 재귀 Watch Mode에서는 출력 폴더를 입력 폴더 내부에 둘 수 없습니다. 기본 출력값(`<input>/output_cropped`)을 그대로 쓰려면 재귀 감시를 끄거나, 출력 폴더를 입력 루트 밖으로 지정하세요.
> 참고: 재귀 Batch/Watch/CLI에서는 내부 생성 폴더(`output_root`, `_failed`, `backup`, `.photocropper`)를 입력 스캔에서 자동 제외합니다.
> 참고: 스케줄 유형 `once`는 날짜 지정이 아니라 "다음 도래 HH:MM에 1회 실행" 의미입니다. busy/no files/invalid config로 시작하지 못한 경우 예약은 보존됩니다.

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
> 참고: 재귀 입력에서는 출력 결과, `_failed`, 멀티포토 `*_photos` 폴더가 입력 기준 상대 경로를 보존합니다.
> 참고: 분류 모델 `custom`은 더 이상 별도 모델이 아니며 `advanced`의 호환 alias로 처리됩니다.

> 참고: `skip processed`는 출력 폴더 로컬 인덱스(`.photocropper/processed_index.json`)를 우선 사용합니다.
> 인덱스 키는 `source_path + size + mtime_ns + pipeline_signature`이며, signature에는 언어별 분류 폴더 해석값과 백업 옵션이 포함됩니다. 멀티포토는 `outputs[]`로 다중 결과를 기록합니다.
> `partial_success`는 인덱스에 `status=partial`로 남기되, 다음 실행에서 full skip하지 않고 경고 후 재처리합니다.
> 인덱스가 비활성/오류일 때만 파일명 기반 fallback 탐지와 제한 경고가 적용됩니다.
> 자동 분류 하위 폴더(기본 `인물/풍경/문서/흑백/기타`, 사용자 지정 가능)와 멀티포토 하위 폴더(`*_photos`)도 탐지 대상에 포함됩니다.
> 참고: CLI summary는 항상 `processed/success/partial_success/failed/skipped`를 출력하며, `--strict-partial` 사용 시 partial만 있어도 종료코드 `1`입니다.

## 🧪 안정성 체크 포인트

- **문법 검증**: `cd ";opencv" && python -m compileall -q photo_cropper`
- **타입 검사**: `pyright --project .\\pyrightconfig.json`
- **전체 selftest**: `cd ";opencv" && python -m photo_cropper.selftest`
- **CLI 스모크 테스트**: `cd ";opencv" && python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-separate-folders --preserve-metadata --no-perspective-correct --skip-processed`
- **워치 모드 검증**: GUI에서 Watch Mode 시작 후 신규 파일 투입 시 배치와 동일한 출력(워터마크/리사이즈/분류 폴더) 확인
- **재귀 Batch 안전성 검증**: recursive batch/CLI + output inside input 조합에서 시작이 차단되는지 확인
- **재귀 Watch 안전성 검증**: recursive watch + output inside input 조합에서 시작이 차단되는지 확인
- **Watch overwrite 검증**: 같은 경로 이미지를 덮어쓴 뒤 size/mtime이 바뀌면 재큐잉되고, 변동이 없으면 중복 처리되지 않는지 확인
- **수동 preview/save parity 검증**: `advanced.perspective_correct=false`에서 수동 편집 직후 preview와 실제 저장 결과 shape이 일치하는지 확인
- **스케줄러 검증**: `watch_mode.scheduler_enabled=true` 상태에서 예약 시각 도달 시 자동 배치 시작/중복 실행 skip 확인
- **CLI partial 정책 검증**: partial만 발생한 run은 기본 종료코드 `0`, `--strict-partial`에서는 `1`인지 확인
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
├── photo_cropper_onefile.spec
└── photo_cropper/
    ├── main.py
    ├── cli.py
    ├── cli_support/
    ├── selftest.py
    ├── selftests/
    ├── benchmark.py
    ├── core/
    │   ├── advanced/
    │   ├── app_paths.py
    │   ├── batch/
    │   ├── file_watch/
    │   ├── image/
    │   ├── jobs/
    │   ├── library/
    │   ├── recipes/
    │   ├── settings_model/
    │   ├── manual_extract/
    │   ├── watch_mode/
    │   ├── multi_photo_detector.py
    │   ├── processed_index.py
    │   ├── resize_processor.py
    │   ├── scheduler.py
    │   └── watermark_processor.py
    ├── ui/
    │   ├── main/
    │   │   └── composition/
    │   └── widgets/
    │       ├── management/
    │       │   └── library/
    │       └── settings/
    ├── i18n/catalog/
    └── utils/
        └── path_validation.py
```

## 🔧 빌드 (PyInstaller)

### 실행 파일 생성

```bash
# 의존성 설치
pip install pyinstaller

# 저장소 루트에서 안정 빌드
pyinstaller ".\\;opencv\\photo_cropper.spec" --clean

# 저장소 루트에서 단일 파일 실험 빌드
pyinstaller ".\\;opencv\\photo_cropper_onefile.spec" --clean
```

생성 결과:
- 안정 onedir 빌드: `;opencv/dist/PhotoCropper_v9/PhotoCropper_v9.exe`
- 실험 onefile 빌드: `;opencv/dist/PhotoCropper_v9_single.exe`

### 패키징 참고

- `photo_cropper.spec`는 Windows 앱 제어 정책 환경에서 더 안정적인 기본 빌드 대상입니다.
- `photo_cropper_onefile.spec`는 편의용/실험용이며, 런타임 압축 해제 경로에 여전히 의존합니다.
- 두 spec 모두 Qt/PyQt 안정성을 위해 UPX 압축을 비활성화했습니다.

### 빌드 최적화 내용

| 항목 | 설명 |
|------|------|
| 기본 빌드 | `photo_cropper.spec`는 onedir 앱 폴더를 생성 |
| 실험 빌드 | `photo_cropper_onefile.spec`는 단일 `.exe`를 생성 |
| 불필요 모듈 제외 | matplotlib, scipy, pandas, tkinter 등 |
| 분할 모듈 자동 수집 | 리팩터링된 `cli_support`, `core/*`, `ui/*` 하위 모듈을 자동 수집 |
| OpenCV/Qt 경량화 | `cv2.gapi` 제외 및 불필요한 Qt/OpenCV 런타임 바이너리 선별 제외 |
| 압축 정책 | App Control / PyQt 안정성을 위해 UPX 비활성화 |

## 📋 변경 이력

### v9.0 전역 코드 분할 리팩터링 (2026-05-11)
- `selftest.py`를 실행 호환 래퍼로 유지하고 실제 테스트를 `selftests/` 책임별 모듈로 분리했습니다.
- CLI, Watch runtime, Advanced image operations, MainWindow composition, SettingsPanel helper, LibraryPage layout을 얇은 public facade와 내부 패키지로 나눴습니다.
- `photo_cropper.spec`와 `photo_cropper_onefile.spec`의 hidden import 수집 범위를 새 내부 패키지까지 확장했습니다.

### v9.0 구현 정합성 업데이트 (2026-04-06)
- 🛡️ recursive batch/watch/CLI에서 output-inside-input 조합을 공통 규칙으로 차단하고, recursive scan exclusion(`output_root`, `_failed`, `backup`, `.photocropper`)을 일원화
- 🛡️ recursive 출력/실패 보관/멀티포토 저장이 입력 기준 상대 경로를 보존하도록 정렬
- 🛡️ `BatchProgress.partial_success`를 분리하고 GUI/CLI summary 정합성 및 CLI `--strict-partial` 종료 정책을 추가
- 🛡️ legacy 분류 모델 `custom`을 `advanced` alias로 정규화하고 UI 선택지를 `basic/advanced`로 정리
- 🛡️ Scheduler `once`를 날짜 없는 "다음 도래 HH:MM 1회 실행" 의미로 명확히 문서화

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

## 2026-04-19 관리앱/리팩터링 메모

- 라이브러리 ingest, review queue, duplicates, collections, recipes, jobs를 `core/library`, `core/jobs`, `core/recipes` 패키지로 분리해 관리앱 아키텍처를 고정했습니다.
- 다음 파일들은 외부 API 호환을 위한 파사드로 유지되고, 실제 구현은 내부 모듈로 이동했습니다:
  - `core/batch/processor.py`
  - `core/image/processor.py`
  - `core/library/repository.py`
  - `ui/widgets/management_pages.py`
- `core/batch/single.py`, `core/image/detect.py`, `core/library/_repository_assets.py`도 추가 분할돼 책임 경계를 더 명확히 했습니다.
- 현재 기본 검증 기준:
  - `cd ";opencv" && python -m compileall -q photo_cropper`
  - `cd ";opencv" && python -m photo_cropper.selftest`
  - `pyright --project .\\pyrightconfig.json`

## 2026-04-27 Management/Library 안정화 완료 메모

- Management 재실행/재처리, Watch, Batch가 파일 목록 기반 공통 preflight를 공유하도록 정리했습니다. recursive 처리에서 output이 input 내부에 들어가는 경로, 빈 output 기본값, 누락 파일 검증을 같은 규칙으로 차단합니다.
- Library import, exact duplicate rebuild, near duplicate rebuild, search-index rebuild를 maintenance job 흐름으로 통합해 UI 스레드 블로킹을 줄이고 완료 toast/refresh 경로를 일관화했습니다.
- SQLite 연결마다 `foreign_keys=ON`, `busy_timeout=5000`을 적용하고 초기화 시 WAL을 best-effort로 켭니다. 쓰기 경합은 store-level `RLock`과 write connection helper로 완화했습니다.
- `LibraryRepository.upsert_source()`는 빈 경로, 누락 파일, 디렉터리, 비이미지 파일을 asset으로 저장하지 않고 `ingest_state="invalid_source"`로 반환합니다.
- FTS 갱신 실패는 `app_state.search_index_dirty=1`로 기록되며, `maintenance_search_index`로 전체 색인을 재빌드할 수 있습니다.
- asset timeline 조회는 전체 review 5000건 스캔 대신 asset 전용 SQL 경로를 사용하고, near duplicate rebuild summary는 `scanned_assets`, `limited`, `limit`를 기록합니다.
- thumbnail/AI/OCR/person provider 실패는 job summary의 `metadata_warnings`, `ai_errors`, `thumbnail_failed_count`에 남깁니다.
- `core/library/_repository_protocol.py`로 repository mixin 타입 계약을 명시하고, 수정 범위의 파일 단위 pyright suppress를 제거했습니다.
- 문서 정합성상 기존 `REFACTOR_STATUS_2026-04-14.md`, `REFACTOR_STATUS_2026-04-19.md` 삭제는 이 통합 메모와 README/CLAUDE 업데이트로 대체합니다.
- 검증 기준:
  - `cd ";opencv" && python -m compileall -q photo_cropper`
  - `cd ";opencv" && pyright --project pyrightconfig.json`
  - `cd ";opencv" && python -m photo_cropper.selftest`

## 2026-04-30 안정화 완료 메모

- PyInstaller spec hidden import에 `photo_cropper.utils.image_io`와 `photo_cropper.ui.widgets.settings.i18n_bindings`를 명시해 frozen build 정합성을 보강했습니다.
- `.gitignore`는 build/dist/runtime cache 외에 로컬 `out/` 폴더도 저장소 밖으로 유지하도록 보강했습니다.
- 표준 검증 기준은 `compileall`, `selftest`, 루트/앱 pyright, CLI help, invalid-config CLI exit code `2` 스모크를 포함합니다.
- 2026-04-14/2026-04-19 리팩터링 상태 스냅샷 문서는 추적 대상에서 제거하고, 현재 README/GEMINI/CLAUDE 문서를 최신 기준으로 사용합니다.
