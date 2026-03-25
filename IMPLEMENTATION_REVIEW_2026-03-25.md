# Photo Cropper 기능 구현 점검 리포트

작성일: 2026-03-25

참조 문서:
- `README.md`
- `;opencv/README.md`
- `;opencv/CLAUDE.md`
- `;opencv/photo_cropper/` 하위 주요 런타임 코드

검증 메모:
- `python -m compileall -q photo_cropper`: OK
- `python -m photo_cropper.selftest`: OK
- `pyright --project pyrightconfig.json`: 현재 환경에 `cv2`, `numpy`, `PyQt6`, `PIL` 등이 잡혀 있지 않아 대부분이 환경성 오류였고, 이번 리포트의 주된 근거로 쓰기에는 부적절했음

## 구현 반영 상태 업데이트

이 리포트에서 우선순위 높게 제안했던 1차 안정화 항목은 2026-03-25 기준 코드에 반영되었습니다.

- contour redraw 분기 정리로 preview widget 예외 경로 제거
- 수동 contour preview/save crop parity 정렬
- 재귀 Watch Mode의 output-inside-input 시작 차단
- Watch 처리 시 failed-file routing 강제 비활성화
- Watch/Batch/Manual 직접 실행 상호 배제
- `fileChanged` 기반 overwrite 재처리 + signature 중복 억제
- processed index v2(`status=success|partial`) 및 partial 재처리 정책 반영
- `Retry Failed`의 output path 보정/검증 경로 통일
- 관련 selftest 추가 및 전체 selftest 재통과

이 문서 본문은 "당시 발견된 이슈와 왜 문제였는지"를 남겨두기 위해 유지합니다.

## 전체 판단

문서상 소개된 핵심 기능은 대부분 연결되어 있지만, 실제 사용자 흐름 기준으로는 UI 수동 편집, Watch Mode, 파일 시스템 부작용이 만나는 지점에 잠재 리스크가 집중되어 있습니다.

특히 우선 대응이 필요한 것은 아래 6가지입니다.

1. 미리보기/수동 편집 UI가 실제로 크래시할 수 있음
2. 재귀 Watch Mode가 자기 출력물을 다시 입력으로 먹을 수 있음
3. 실패 파일 분류가 Watch Mode 재처리 루프를 만들 수 있음
4. 사용자가 직접 Watch와 Batch를 동시에 돌릴 수 있음
5. `perspective_correct=False`일 때 수동 편집 미리보기와 실제 저장 결과가 다름
6. `Retry Failed` 경로가 최초 배치 시작 경로보다 약함

## 주요 이슈

### 1. 높음: contour overlay redraw가 크래시하고, 수동 4점 입력 가이드도 일부만 그려짐

근거:
- `;opencv/photo_cropper/ui/widgets/preview_widget.py:490`
- `;opencv/photo_cropper/ui/widgets/preview_widget.py:499`
- `;opencv/photo_cropper/ui/widgets/preview_widget.py:526`

문제 내용:
- `seed_points`는 `self._contour_points`가 없을 때만 할당됩니다.
- 그런데 499라인의 루프는 분기 밖에 있어서, 정상적인 4점 contour가 있을 때도 `len(seed_points)`를 호출합니다.
- 실제로 오프스크린 `ImagePreviewWidget`에 `set_original_image(...)`를 호출해 재현했을 때 `UnboundLocalError`가 발생했습니다.
- 같은 블록 안의 `return` 위치도 잘못되어 있어서, 수동으로 1~3개 점을 찍는 동안 가이드 선이 첫 세그먼트만 그려집니다.

영향:
- 자동 검출된 contour가 있는 일반 미리보기 경로에서도 UI 예외가 날 수 있음
- 수동 보정 UX가 불완전함
- README에서 강조하는 핵심 편집 흐름 신뢰도가 떨어짐

권장 조치:
- 수동 seed 렌더링과 4점 contour 렌더링 분기를 완전히 분리
- `seed_points` 루프를 수동 seed 분기 안으로 이동
- `return`을 루프 밖으로 이동
- `set_original_image(...)` 호출 기준 UI 회귀 테스트 추가

### 2. 높음: 재귀 Watch Mode가 자기 출력 폴더를 다시 처리할 수 있음

근거:
- `;opencv/photo_cropper/core/watch_mode/coordinator.py:67`
- `;opencv/photo_cropper/ui/main/actions/watch.py:128`
- `;opencv/photo_cropper/core/folder_watcher.py:190`
- `;opencv/photo_cropper/core/folder_watcher.py:196`
- `;opencv/photo_cropper/core/folder_watcher.py:221`
- `;opencv/photo_cropper/core/folder_watcher.py:255`
- `;opencv/photo_cropper/core/watch_mode/coordinator.py:148`

문제 내용:
- Watch Mode 기본 출력 경로가 `<input>/output_cropped`입니다.
- 재귀 감시가 켜져 있으면 새 하위 디렉터리를 watcher에 추가하고, 그 안 이미지도 즉시 스캔합니다.
- 그런데 output subtree를 제외하는 로직이 없습니다.
- 따라서 저장된 결과 이미지가 다시 새 입력으로 큐잉될 수 있습니다.

영향:
- 중복 처리
- 대기열 증가
- 분류 폴더, 멀티포토 하위 폴더, 후처리 결과가 다시 재처리되는 자기증식형 동작 가능

권장 조치:
- 재귀 Watch Mode에서는 output path가 watch root 내부일 때 시작 자체를 막거나 강한 경고를 표시
- 또는 `FolderWatcher`/`AutoProcessor`에 ignore path 개념 추가
- 최소한 `output root`, 분류 폴더, `*_photos`, `backup`, `.photocropper`는 제외
- "watch root 안에 output root가 있는 경우"에 대한 selftest 추가

### 3. 높음: 실패 파일 분류 기능이 Watch Mode 재처리 루프를 만들 수 있음

근거:
- `;opencv/photo_cropper/core/settings_model/app_settings.py:242`
- `;opencv/photo_cropper/core/settings_model/app_settings.py:243`
- `;opencv/photo_cropper/core/settings_model/app_settings.py:244`
- `;opencv/photo_cropper/utils/file_helpers.py:426`
- `;opencv/photo_cropper/utils/file_helpers.py:448`
- `;opencv/photo_cropper/core/batch/processor.py:1257`
- `;opencv/photo_cropper/core/batch/processor.py:1562`

문제 내용:
- 실패 파일은 기본적으로 `<source_dir>/_failed` 아래로 복사/이동됩니다.
- Watch Mode는 내부적으로 `BatchProcessor.process_single(...)`를 사용합니다.
- 재귀 감시가 켜져 있으면 `_failed`도 감시 트리 안에 남습니다.
- 특히 기본값이 `copy_failed_instead_of_move=True`라서 원본이 남고 실패본이 하나 더 생기므로 루프가 더 심해집니다.

영향:
- 같은 실패 파일이 반복 큐잉될 수 있음
- `_failed`, `_failed_1` 식으로 결과가 계속 불어날 수 있음
- 사용자는 "왜 같은 파일이 계속 실패하느냐"를 체감하게 됨

권장 조치:
- Watch Mode에서는 실패 파일 분류를 강제로 끄거나
- `_failed` subtree를 감시 대상에서 제외
- `move_failed_files + recursive watch` 조합에 대해 UI 경고 추가
- 관련 회귀 테스트 추가

### 4. 중간: 사용자가 직접 Watch와 Batch를 동시에 실행할 수 있음

근거:
- `;opencv/photo_cropper/ui/main/actions/watch.py:96`
- `;opencv/photo_cropper/ui/main/actions/watch.py:186`
- `;opencv/photo_cropper/ui/main/actions/batch.py:143`

문제 내용:
- 스케줄러 경로는 `busy_reason_for_scheduled_batch()`로 중복 실행을 막습니다.
- 하지만 직접 `start_watch_mode()`를 누를 때는 active batch를 막지 않습니다.
- 반대로 직접 `start_processing()`를 누를 때도 active watch를 막지 않습니다.
- 두 경로는 서로 다른 processor lifecycle을 쓰므로 실제 동시 실행이 가능합니다.

영향:
- 같은 출력 경로에 동시 쓰기 가능
- 진행률/상태 메시지 해석이 어려워짐
- 중복 파일명, skip_processed 타이밍, UI 상태 꼬임 같은 재현 어려운 문제로 이어질 수 있음

권장 조치:
- Batch, Watch, Manual Extract를 묶는 공통 busy guard 추가
- Batch 실행 중 Watch 시작 차단
- Watch 활성 중 Batch 시작 차단
- 현재 scheduler 경로에서 쓰는 경고 패턴을 재사용

### 5. 중간: `perspective_correct=False`일 때 수동 편집 미리보기와 실제 저장 결과가 다름

근거:
- `;opencv/photo_cropper/ui/main/actions/preview.py:88`
- `;opencv/photo_cropper/ui/main/actions/preview.py:117`
- `;opencv/photo_cropper/core/image/processor.py:1445`
- `;opencv/photo_cropper/core/manual_extract/service.py:178`

문제 내용:
- 수동 contour 편집 직후 미리보기는 항상 `correct_perspective(...)`를 호출합니다.
- 반면 실제 저장 경로는 `settings.advanced.perspective_correct`를 존중합니다.
- 문서상 OFF 동작은 axis-aligned bounding box crop인데, 현재 미리보기는 그 규칙을 따르지 않습니다.

영향:
- 사용자는 한 화면을 보고 저장했는데 실제 저장 결과가 다르게 나옴
- 수동 편집은 신뢰가 핵심인 흐름이라 체감 문제가 큼

권장 조치:
- 수동 편집 미리보기 경로도 저장 경로와 같은 분기를 사용
- `perspective_correct=False`이면 preview도 axis-aligned crop을 보여주도록 수정
- preview/save parity 테스트 추가

### 6. 중간: `Retry Failed` 경로는 빈 output path를 정상화하지 않음

근거:
- `;opencv/photo_cropper/ui/main/actions/batch.py:323`
- `;opencv/photo_cropper/ui/main/actions/batch.py:343`
- 비교 기준: `;opencv/photo_cropper/ui/main/actions/batch.py:167`

문제 내용:
- 최초 `start_processing()`는 output path가 비어 있으면 `<input>/output_cropped`로 채웁니다.
- `retry_failed_files()`는 그 처리를 하지 않습니다.
- 그 상태로 progress dialog를 먼저 띄우고, worker thread 안에서 `output_path=""` 상태 배치를 시작할 수 있습니다.

영향:
- 최초 배치보다 재시도 경로가 더 약함
- UI에서 미리 막아야 할 오류가 뒤늦게 worker thread에서 터짐

권장 조치:
- `start_processing()`와 동일한 output path 보정/검증 로직 재사용
- 정상화가 끝난 뒤에만 progress dialog 생성

## 추가하면 좋은 부분

### 1. Partial success의 processed index 정책 재검토

현재 상태:
- `;opencv/photo_cropper/core/batch/processor.py:1746`에서 full `SUCCESS`만 processed index에 기록
- partial multi-photo 출력은 의도적으로 기록하지 않음

보완 이유:
- `skip_processed` 상태에서 재실행하면 이미 저장된 일부 출력이 다시 만들어질 수 있음
- 사용자 입장에서는 "처음부터 다시"보다 "빠진 것만 보완"이 더 자연스러울 수 있음

권장 방향:
- partial outputs도 status 메타데이터와 함께 기록
- skip / resume / warn 정책을 분리해서 결정

### 2. Watch Mode는 현재 "새 경로"만 처리하고, 같은 파일명 overwrite는 사실상 무시함

근거:
- `;opencv/photo_cropper/core/folder_watcher.py:193`

보완 이유:
- `_on_file_changed()`가 실질적으로 no-op
- 스캐너나 동기화 도구가 같은 파일명을 덮어쓰는 패턴이면 재처리가 안 됨

권장 방향:
- overwrite-in-place를 지원할지 명확히 결정
- 지원할 경우 `fileChanged`에서 mtime/size 기준 중복 억제를 넣어 재큐잉

### 3. 테스트 보강이 필요한 지점

추가 권장 테스트:
- preview contour redraw 회귀 테스트
- recursive watch가 output subtree를 무시하는지 검증
- recursive watch가 `_failed` subtree를 무시하는지 검증
- Batch/Watch 상호 배제 검증
- `perspective_correct=False`에서 preview/save parity 검증
- 빈 output path 상태의 `Retry Failed` 검증

## 결론

현재 프로젝트는 핵심 알고리즘 자체보다, UI 상태와 Watch 자동화, 파일 저장 부작용이 만나는 경계면에서 더 큰 리스크를 가지고 있습니다. 다음 안정화 우선순위는 detection core보다는 이 경계 조건들을 막는 쪽이 맞습니다.
