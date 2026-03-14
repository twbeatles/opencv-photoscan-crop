# 기능 구현 점검 메모 (2026-03-14)

> 이 문서는 2026-03-14 시점의 구현 점검 기록입니다. 아래 항목들은 이후 같은 날짜의 구현 작업으로 반영되었으며, 현재 동작 설명은 `README.md`와 `;opencv/CLAUDE.md`의 2026-03-14 업데이트를 우선 기준으로 봐주세요.

`README.md`와 `;opencv/CLAUDE.md`를 기준으로, 실제 구현이 문서상 기대 동작과 얼마나 정합적인지 기능 중심으로 점검했습니다. 검토 범위는 `;opencv/photo_cropper`의 배치 처리, Watch Mode, 멀티포토, 수동 추출, 메타데이터 저장 흐름입니다.

## 우선순위 높은 이슈

### 1. Watch Mode 처리가 UI 스레드에서 동기 실행됩니다

- 근거
  - `WatchModeCoordinator.start()`는 `AutoProcessor`를 현재 QObject 트리 안에서 바로 생성합니다: `;opencv/photo_cropper/core/watch_mode/coordinator.py:90-97`
  - `AutoProcessor._process_next()`는 별도 worker/thread 없이 `self._process_callback(...)`를 직접 호출합니다: `;opencv/photo_cropper/core/folder_watcher.py:562-576`
  - 이 callback은 결국 `BatchProcessor.process_single()`을 동기 호출합니다: `;opencv/photo_cropper/core/watch_mode/coordinator.py:134-154`, `;opencv/photo_cropper/core/batch/processor.py:1208-1259`
- 영향
  - Watch Mode에서 큰 파일이 들어오면 UI가 멈춘 것처럼 보일 가능성이 큽니다.
  - 취소/정지 반응도 현재 파일 처리가 끝날 때까지 늦어집니다.
  - 스케줄러와 Watch Mode를 같이 쓸 때 체감상 "감시 중인데 앱이 굳는" 문제가 생길 수 있습니다.
- 권장
  - Watch Mode의 파일 처리만 별도 worker thread 또는 전용 executor로 분리하고, 결과만 signal로 UI에 전달하는 구조가 필요합니다.

### 2. Watch Mode의 `max_wait_seconds`가 실제로는 제대로 살아있지 않습니다

- 문서 기대값
  - `README.md:392`
  - `;opencv/CLAUDE.md:162`
  - 두 문서 모두 Watch 파일 준비 대기시간을 `watch_mode.max_wait_seconds`로 제어한다고 설명합니다.
- 실제 구현
  - `FolderWatcher._process_pending_files()`는 파일을 한 번 열어보고 실패하면 1초 뒤 딱 한 번만 `_retry_file()`을 호출합니다: `;opencv/photo_cropper/core/folder_watcher.py:249-279`
  - `_retry_file()`도 다시 실패하면 warning만 남기고 그 파일을 버립니다: `;opencv/photo_cropper/core/folder_watcher.py:267-279`
  - 반면 진짜 정교한 readiness 로직은 `AutoProcessor._check_file_ready()`에 구현되어 있지만, `new_file_detected`가 먼저 올라와야만 실행됩니다: `;opencv/photo_cropper/core/folder_watcher.py:518-605`
- 영향
  - 스캐너가 천천히 쓰는 파일, 네트워크 드라이브, 대용량 복사 파일은 `AutoProcessor`까지 도달하지 못하고 유실될 수 있습니다.
  - 문서에서 강조한 "최대 대기시간 제어"와 실제 동작이 어긋납니다.
- 권장
  - 파일 준비 여부 판정은 `FolderWatcher`가 아니라 `AutoProcessor` 한 군데에서만 맡게 하는 편이 안전합니다.

### 3. `preserve_metadata` 사용 시 EXIF orientation이 다시 붙어서 출력이 재회전될 수 있습니다

- 문서 기대값
  - `README.md:317`
  - `;opencv/CLAUDE.md:208-209`
  - 둘 다 EXIF orientation 정규화가 들어갔다고 설명합니다.
- 실제 구현
  - `ImageProcessor.load_image()`는 `ImageOps.exif_transpose()`로 픽셀을 먼저 바로잡습니다: `;opencv/photo_cropper/core/image/processor.py:207-218`
  - 그런데 `copy_metadata_best_effort()`는 원본의 `src.info["exif"]`를 그대로 다시 저장합니다: `;opencv/photo_cropper/core/image/save_io.py:55-67`, `;opencv/photo_cropper/core/image/save_io.py:82-88`
- 영향
  - 원본이 `Orientation=6/8` 같은 값을 갖고 있으면, 픽셀은 이미 정상 방향인데 메타데이터가 다시 회전 정보를 들고 가게 됩니다.
  - 결과적으로 일부 뷰어/OS에서 저장 결과가 다시 돌아가 보일 수 있습니다.
  - 특히 `--preserve-metadata`를 문서 예시처럼 쓰는 CLI/배치 흐름에서 바로 체감될 수 있습니다.
- 권장
  - 메타데이터 복사 전 Orientation 태그를 제거하거나 `1`로 재기록해야 합니다.
  - 가능하면 "안전한 EXIF subset만 복사"하는 전략이 더 낫습니다.

### 4. 멀티포토 경로는 EXIF orientation 정규화 로딩을 우회합니다

- 근거
  - 멀티포토는 `np.fromfile + cv2.imdecode`로 직접 이미지를 읽습니다: `;opencv/photo_cropper/core/batch/processor.py:1827-1830`
  - 일반 단일 사진 경로는 `ImageProcessor.load_image()`를 통해 EXIF 정규화를 적용합니다: `;opencv/photo_cropper/core/image/processor.py:197-225`
- 영향
  - 같은 원본이라도 단일 사진 모드와 멀티포토 모드의 회전/검출 결과가 달라질 수 있습니다.
  - 휴대폰 촬영본이나 EXIF orientation이 남아 있는 스캔 이미지는 멀티포토에서만 잘못 검출될 가능성이 있습니다.
- 권장
  - 멀티포토도 공통 로더(`ImageProcessor.load_image()` 또는 별도 shared loader)로 통일하는 것이 좋습니다.

### 5. 배치를 다시 시작하면 이전 배치가 완전히 종료되기 전에 새 세션이 열릴 수 있습니다

- 근거
  - `BatchActions.start_processing()`에는 이미 실행 중인 batch를 막는 guard가 없습니다: `;opencv/photo_cropper/ui/main/actions/batch.py:124-171`
  - 이 함수는 항상 `BatchSessionService.create_processor()`를 호출합니다: `;opencv/photo_cropper/ui/main/actions/batch.py:161-170`
  - `create_processor()`는 기존 세션에 대해 `cleanup()`만 호출하고 새 `BatchProcessor`를 생성합니다: `;opencv/photo_cropper/core/batch/session_service.py:30-45`
  - 그런데 `BatchProcessor.cleanup()`은 stop 요청만 하고 worker thread를 join하지 않습니다: `;opencv/photo_cropper/core/batch/processor.py:1085-1092`
- 영향
  - 사용자가 버튼/메뉴를 연속 클릭하거나 UI 경로에서 중복 진입하면, 이전 배치의 잔여 작업과 새 배치가 겹칠 수 있습니다.
  - 출력 파일 중복, 로그 혼선, progress 상태 꼬임 가능성이 있습니다.
- 권장
  - UI 진입점에서 `is_running` hard guard를 넣고, 세션 교체는 이전 worker가 실제 종료된 뒤에만 허용하는 편이 안전합니다.

### 6. 멀티포토는 부분 저장이나 중간 취소를 `SUCCESS`로 덮어버립니다

- 근거
  - 멀티포토 loop는 stop 요청이 들어오면 그냥 `break`합니다: `;opencv/photo_cropper/core/batch/processor.py:1881-1883`
  - 이후 저장된 결과가 1개라도 있으면 `ProcessStatus.SUCCESS`를 반환합니다: `;opencv/photo_cropper/core/batch/processor.py:1916-1930`
  - 개별 sub-photo 저장 실패도 카운트/경고 없이 지나갑니다: `;opencv/photo_cropper/core/batch/processor.py:1895-1912`
- 영향
  - 실제로는 `3/5`만 저장됐는데도 전체 스캔이 성공처럼 보일 수 있습니다.
  - 사용자는 일부 사진이 빠졌다는 사실을 UI/로그만 보고 놓치기 쉽습니다.
- 권장
  - `PARTIAL_SUCCESS` 같은 상태를 별도로 두거나, 최소한 `saved_count`, `failed_count`, `cancelled_midway`를 UI에 노출하는 게 필요합니다.

## 추가하면 좋은 보완 작업

- EXIF orientation + `preserve_metadata` 조합 회귀 테스트 추가
- 멀티포토 회전 원본(orientation 6/8) 회귀 테스트 추가
- Watch Mode 대용량 복사/지연 파일 회귀 테스트 추가
- batch 재진입 방지 테스트 추가
- 멀티포토 `partial success` UX 정의 및 로그 포맷 보강

## 이번 점검에서 수행한 확인

- `python -m compileall -q photo_cropper`: 통과
- `python -m photo_cropper.cli --help`: 통과
- `python -m photo_cropper.selftest`: 실패
  - 현재 셸 환경에 `cv2`가 없어 import 단계에서 중단됐습니다.
- `pyright --project pyrightconfig.json`: 실패
  - 현 환경의 missing import(`cv2`, `winotify`) 영향이 크지만, 일부 Optional/type 경고도 남아 있어 정적검사 정리 여지는 있습니다.

## 요약

가장 먼저 손봐야 할 축은 `Watch Mode 비동기화`, `파일 준비 판정 단일화`, `EXIF orientation + metadata 보존 정합성`입니다. 이 세 가지는 문서상으로는 이미 해결된 것처럼 보이지만, 실제 구현에서는 여전히 사용자 체감 이슈나 결과물 정합성 문제로 이어질 가능성이 큽니다.
