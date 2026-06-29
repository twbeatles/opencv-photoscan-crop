# Project Audit

## Remediation Status (2026-06-29)

감사 권고사항 대부분이 적용되었습니다. 요약:

| 항목 | 상태 |
|------|------|
| `;opencv/` → `opencv/` 리네이밍 | **완료** |
| `scripts/verify.ps1` / `verify.sh` | **완료** |
| selftest 러너 개선 (이름 출력/필터/traceback) | **완료** |
| winotify pyright 호환 | **완료** (`importlib`) |
| Git + GitHub Actions `.github/workflows/verify.yml` | **완료** |
| 싱글톤 reset + `PHOTOCROPPER_LIBRARY_DB` / `PHOTOCROPPER_OFFLINE` | **완료** |
| pytest + `tests/` | **완료** (단위 + selftest registry) |
| `CONTRIBUTING.md` | **완료** |
| 문서 동기화 (README/GEMINI/CLAUDE/spec) | **완료** |
| 벤치마크 synthetic CI 게이트 | **미구현** (데이터셋 미포함) |
| `getsize` 실패 시 silent pass 보강 | **미구현** (추정 항목) |

검증: `powershell -NoProfile -File scripts/verify.ps1` → **VERIFY OK**

---

## 1. Executive Summary

Photo Cropper v9.0은 PyQt6 GUI·CLI·Watch Mode·SQLite 기반 관리 셸을 갖춘 성숙한 이미지 처리 애플리케이션입니다. `selftests/`에 100개 이상의 통합 자가검증이 있고, 이번 감사 환경에서 `python -m photo_cropper.selftest`는 **SELFTEST OK**, `compileall`은 통과했습니다.

그러나 **Superpowers(엄격 TDD·계획 기반 개발·에이전트 자동화·환경 격리)** 관점에서는 다음이 전체 위험도를 **Medium–High**로 끌어올립니다.

| 영역 | 평가 |
|------|------|
| 기능 안정성 | **양호** — 배치/Watch/CLI 정합성, preflight, fatal_error, path guard 등이 코드·테스트·문서에 정렬됨 |
| TDD/테스트 자동화 | **취약** — pytest/unittest 미사용, 단일 직렬 selftest 러너, 실패 시 테스트명 미출력 |
| 환경 격리 | **취약** — Git 미초기화, `;opencv/` 비표준 경로, 전역 싱글톤 다수, 사용자 APPDATA/SQLite 쓰기 |
| CI/검증 파이프라인 | **없음** — `.github/workflows` 부재, 통합 verify 스크립트 부재 |
| 문서 정합성 | **부분 불일치** — pyright 0 errors 주장 vs 실제 winotify 미설치 시 1 error |

**핵심 결론:** 런타임 기능은 광범위한 selftest로 상당히 견고하지만, 에이전트가 Red-Green-Refactor 루프를 **독립·병렬·격리** 환경에서 반복하기에는 구조적 장벽이 큽니다. 즉시 수정이 필요한 것은 기능 결함보다 **자동화 인프라·테스트 하네스·경로/의존성 표준화**입니다.

---

## 2. Project Understanding

### 2.1 프로젝트 목적

스캔/배경 위 사진을 OpenCV 기반 다단계 알고리즘으로 감지·크롭하고, 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 라우팅 → 워터마크 후처리를 적용하는 데스크톱 앱입니다. v9.0부터 라이브러리·작업 이력·레시피·중복 검출 등 **관리 셸**이 확장되었습니다.

### 2.2 아키텍처 (README.md, `;opencv/CLAUDE.md`, CodeGraph 분석)

```text
저장소 루트/
└── ;opencv/                    ← 실제 앱 루트 (비표준 디렉터리명)
    ├── run.py                 → photo_cropper.main.main() (GUI)
    ├── photo_cropper/
    │   ├── cli.py             → cli_support.runtime (CLI 파사드)
    │   ├── cli_support/runtime.py
    │   ├── selftest.py        → selftests/runner.py
    │   ├── core/
    │   │   ├── batch/         BatchProcessor (facade + runner/single/post mixins)
    │   │   ├── image/         ImageProcessor (감지·크롭)
    │   │   ├── watch_mode/    WatchModeCoordinator → AutoProcessor
    │   │   ├── jobs/          JobOrchestrator
    │   │   ├── library/       LibraryRepository + SQLite
    │   │   ├── recipes/       RecipeManager
    │   │   └── settings_model/
    │   └── ui/main/           MainWindow composition root (actions/builders/services)
```

**CodeGraph 호출 관계 요약:**

- **GUI:** `run.py` → `main.py` → `MainWindow` → `ui/main/actions/*` → `BatchProcessor` / `WatchModeCoordinator`
- **CLI:** `cli_support/runtime.py::process_batch` → `build_settings_from_args` → `validate_settings` → `BatchProcessor.start_async` → (선택) `JobOrchestrator`
- **Watch:** `WatchModeCoordinator.start` → `AutoProcessor` background worker → `BatchProcessor.process_single(clear_stop_event=False)`
- **관리:** `JobOrchestrator.finalize_job` → `LibraryRepository` (asset/variant/review/job 기록)

### 2.3 주요 데이터 흐름

1. **설정:** `AppSettings` dataclass → `SettingsManager` persistence (`%APPDATA%/PhotoCropper/settings.json` 또는 `~/.photo_cropper/`)
2. **배치:** 입력 스캔 → preflight(`BatchRuntimeFlow`) → `start_async` → `_process_single_file` → 후처리 파이프라인 → 출력 + `.photocropper/processed_index.json`
3. **skip_processed:** 인덱스 v2 (`status=success|partial`) 우선, signature에 분류 폴더·백업 옵션 포함
4. **작업 이력:** CLI/GUI 배치 완료 시 `JobOrchestrator.finalize_job`이 SQLite 카탈로그·리뷰 큐 갱신
5. **라이브러리 DB:** 기본 경로 `get_library_db_path()` → `%LOCALAPPDATA%/PhotoCropper/library/library.db`

### 2.4 검증 현황 (이번 감사 실행)

| 명령 | 결과 |
|------|------|
| `cd ";opencv" && python -m photo_cropper.selftest` | **SELFTEST OK** |
| `cd ";opencv" && python -m compileall -q photo_cropper` | **COMPILEALL OK** |
| `cd ";opencv" && pyright --project pyrightconfig.json` | **1 error** (`winotify` import) |

---

## 3. High-Risk Issues

### 3.1 비표준 앱 디렉터리명 `;opencv/`가 셸·에이전트 자동화를 방해

* **위치:** 저장소 루트 구조, `README.md` L7·L151–157, 모든 `cd ";opencv"` 예시
* **문제:** 디렉터리명 선두 `;`가 PowerShell에서 문 구분자로 해석될 수 있어 경로 인용·`&&` 체이닝이 실패합니다. 이번 감사에서 `cd "...;opencv" && python ...`는 PowerShell 파서 오류로 실패했고, `Set-Location` + `;` 구분만 동작했습니다.
* **영향:** 에이전트/CI가 README 명령을 그대로 실행하면 빌드·테스트가 즉시 실패합니다. Git worktree·상대경로 스크립트도 오류 가능성이 높습니다.
* **근거:** README가 `;opencv/`를 전제로 한 명령 제공. 실제 감사 셸에서 `&&` 실패 확인.
* **권장 수정 방향:** 앱 루트를 `opencv/` 또는 `app/` 등 표준 이름으로 변경하고, README/CLAUDE/pyright `include` 경로 동기화. 단기적으로는 루트에 `verify.ps1`/`verify.sh`로 OS별 진입점 고정.
* **우선순위:** **Critical** (자동화 차단)

---

### 3.2 Git 미초기화로 Superpowers 환경 격리(worktree) 불가

* **위치:** 저장소 루트 (워크스페이스 메타데이터: git repo 아님)
* **문제:** `obra/superpowers`의 git worktree 기반 병렬 에이전트 실행·브랜치 격리가 불가능합니다.
* **영향:** 다중 에이전트가 동일 워킹 디렉터리를 공유하며 설정 DB·SQLite·processed index·singleton 상태가 오염될 수 있습니다.
* **근거:** 사용자 환경 정보 및 `.git` 부재.
* **권장 수정 방향:** `git init` + `.gitignore` 정리 후 원격 연결. 에이전트 작업은 worktree별 독립 `TEMP`/DB 경로 사용.
* **우선순위:** **High**

---

### 3.3 CI/CD 및 표준 테스트 러너 부재

* **위치:** `.github/workflows` 없음, `photo_cropper/selftests/runner.py` L238–247
* **문제:** pytest/unittest 기반 표준 테스트가 없고, 100+ 검증이 단일 `TESTS` 리스트 직렬 실행에 의존합니다. 실패 시 `SELFTEST FAILED: {e}`만 출력하고 **실패한 테스트 함수명을 기록하지 않습니다.**
* **영향:** 에이전트가 Red-Green-Refactor에서 (1) 단일 테스트 격리 실행, (2) 실패 지점 빠른 특정, (3) CI 게이트 자동화를 할 수 없습니다.
* **근거:**

```238:247:;opencv/photo_cropper/selftests/runner.py
def main() -> int:
    try:
        for test in TESTS:
            test()
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0
```

* **권장 수정 방향:** `pytest` 래퍼 도입(`_test_*` → `test_*` 또는 parametrized), GitHub Actions에서 `selftest`+`pyright`+`compileall` 실행. 러너에 `print(test.__name__)` 및 per-test try/except 추가(최소 개선).
* **우선순위:** **High**

---

### 3.4 pyright 검증 기준과 문서 불일치 (winotify)

* **위치:** `;opencv/photo_cropper/utils/system_notification.py` L28–29, `pyrightconfig.json`, `README.md` L518·L559
* **문제:** 런타임은 `try/except ImportError`로 winotify 없이 동작하지만, pyright는 top-level `from winotify import ...`를 **missing import**로 보고합니다. README/CLAUDE는 "0 errors / 0 warnings"를 주장합니다.
* **영향:** 클린룸/리눅스 CI에서 `pyright`가 실패해 문서화된 검증 기준을 통과할 수 없습니다. 에이전트가 "검증 완료"를 잘못 판단할 위험.
* **근거:** 이번 실행 `pyright --project pyrightconfig.json` → `reportMissingImports` 1건. `requirements.txt`는 winotify를 Windows 전용 optional로 선언.
* **권장 수정 방향:** `TYPE_CHECKING` 분기, `pyrightconfig.json`의 `reportMissingImports: none` 또는 stub 패키지, CI에서 Windows 전용 extra 설치 명시.
* **우선순위:** **High** (자동화 게이트)

---

### 3.5 전역 싱글톤이 테스트·에이전트 격리를 약화

* **위치:**
  - `core/library/repository.py` L114–121 (`get_library_repository`)
  - `core/image_classifier.py` (`get_classifier`)
  - `core/face/detector.py` (`get_face_detector`)
  - `core/smart_enhancer.py`, `utils/processing_log.py`, `i18n/catalog/manager.py`
* **문제:** 프로세스 수명 동안 단일 인스턴스를 공유하며 reset API가 없습니다. selftest 대부분은 temp `LibrarySqliteStore`를 주입하지만, CLI/GUI 런타임 경로는 `get_library_repository()`로 **사용자 APPDATA 하위 SQLite**에 씁니다.
* **영향:** 테스트 순서 의존, 병렬 실행 불가, 에이전트 로컬 DB 오염. CodeGraph도 `JobOrchestrator`/`process_single`에 대해 "no covering tests found"를 표시(커스텀 네이밍·인덱스 한계).
* **근거:**

```114:121:;opencv/photo_cropper/core/library/repository.py
_repository_instance: Optional[LibraryRepository] = None

def get_library_repository() -> LibraryRepository:
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = LibraryRepository()
    return _repository_instance
```

* **권장 수정 방향:** `reset_*_for_tests()` 또는 DI 컨테이너, CLI에 `--library-db` 오버라이드, 테스트 fixture에서 env+singleton 초기화.
* **우선순위:** **Medium**

---

### 3.6 selftest의 모듈 패치가 실패 시 프로세스 상태 오염 가능

* **위치:** `selftests/batch_cli.py` L965–982, L1019–1041, L1097–1113
* **문제:** `batch_mod.BatchProcessor = FakeProcessor`로 모듈 전역을 교체합니다. `finally`로 복원하지만, **assert 실패·프로세스 kill 시 복원 누락** 가능.
* **영향:** 후속 테스트 또는 동일 프로세스 재실행에서 실제 `BatchProcessor` 대신 Fake가 남아 오작동(추정: 낮은 확률이나 디버깅 어려움).
* **근거:** monkeypatch 패턴 3곳, try/finally는 assert 전 중간 예외에만 안전.
* **권장 수정 방향:** `unittest.mock.patch` 컨텍스트 매니저 또는 pytest fixture autouse teardown.
* **우선순위:** **Medium**

---

### 3.7 CLI 종료코드 우선순위: 취소(130)가 실패(1)보다 우선

* **위치:** `cli_support/runtime.py` L540–551
* **문제:** `fatal_error` → `cancelled(130)` → `failed>0(1)` 순입니다. 사용자가 Ctrl+C로 취소했지만 이미 일부 파일이 실패한 경우 **exit 130**이 반환되고 `failed>0`은 무시됩니다.
* **영향:** CI/스크립트가 "취소"와 "부분 실패"를 구분하지 못할 수 있습니다. 문서는 취소 130을 명시하므로 의도일 수 있으나 자동화 소비자에게 함정.
* **근거:**

```540:551:;opencv/photo_cropper/cli_support/runtime.py
    if bool(getattr(progress, "fatal_error", False)):
        ...
        return 1
    if cancelled:
        return 130
    if progress.failed > 0:
        return 1
```

* **권장 수정 방향:** 문서에 "cancelled 시 failed 무시" 명시, 또는 `130` + stderr에 failed 카운트 항상 출력(이미 summary 있음). 엄격 모드 `--strict-cancel` 검토.
* **우선순위:** **Medium**

---

### 3.8 DNN 얼굴 모델 최초 사용 시 네트워크 의존

* **위치:** `core/face/detector.py` L209–268 (`urllib.request.urlopen`, 20s timeout)
* **문제:** DNN 모델이 로컬 캐시에 없으면 GitHub raw URL에서 다운로드 시도. 샌드박스/오프라인 환경에서는 Haar 폴백으로 전환(selftest `_test_face_dnn_fallback_when_download_fails` 존재).
* **영향:** 첫 실행 지연·네트워크 실패 로그·에이전트 환경에서 예측 불가 지연. 기능상 치명적이지는 않음.
* **근거:** `_download_file_atomic`, `_ensure_dnn_models` 구현 및 selftest 폴백 검증.
* **권장 수정 방향:** 모델 번들링(선택), `PHOTOCROPPER_OFFLINE=1` env, CI에서 사전 캐시 시드.
* **우선순위:** **Low–Medium**

---

## 4. Potential Functional Gaps

### 4.1 확실한 갭

| 항목 | 설명 |
|------|------|
| 통합 verify 스크립트 부재 | README에 검증 명령이 분산되어 있으나 단일 `make verify`/`scripts/verify` 없음 |
| CodeGraph 인덱스 미커밋 | `.codegraph/`가 gitignore — 에이전트가 구조 분석 MCP 없이는 grep/Read에 의존 |
| 벤치마크 데이터셋 미포함 | `photo_cropper.benchmark`는 라벨 포맷만 제공, 실사진 데이터 없음 — 정밀도 회귀 자동화 제한 |
| PyInstaller `unittest` 제외 | spec에서 unittest/pytest 제외 — frozen 빌드에서 테스트 실행 불가(의도적일 수 있음) |

### 4.2 추정(추가 검증 필요)

| 항목 | 설명 |
|------|------|
| **추정:** Linux headless CI에서 일부 Qt selftest 스킵/불안정 | `_ensure_qt_app`은 `QT_QPA_PLATFORM=offscreen` 설정하나, 환경에 따라 PyQt6/display 의존 테스트가 flaky할 수 있음 |
| **추정:** `getsize` 실패 시 max_image_size_mb 우회 | `_single_file.py` L126–127 `except Exception: pass` — 권한/경합 오류 시 대용량 파일이 제한 없이 처리될 수 있음 |
| **추정:** CLI job tracking 실패 시 조용한 degradation | `process_batch` L470–473에서 library 초기화 실패 시 warning만 남기고 job 기록 없이 진행 — 운영 추적 공백 |
| **추정:** `backups/` 로컬 폴더 잔존 | gitignore 대상이나 워크스페이스에 구버전 스냅샷 존재 시 에이전트가 잘못된 파일을 참조할 수 있음 |
| **추정:** 취소+실패 혼합 시 exit code 의미 모호 | `_test_cli_cancel_exit_code_130`은 failed=0 케이스만 검증 |

### 4.3 Superpowers TDD 적합성 평가

| 기준 | 상태 |
|------|------|
| Red-Green-Refactor 단위 격리 | **미흡** — 통합 selftest 중심, 단일 함수 단위 테스트 거의 없음 |
| Mock/의존성 주입 | **부분** — BatchProcessor 내부 `_get_classifier` 등 hook은 있으나 공개 DI 아님 |
| 결정론적 테스트 | **양호** — tempfile·synthetic image·Fake processor 다수 |
| 빠른 피드백 | **보통** — 전체 selftest ~10s+(환경 의존), 단일 테스트 선택 실행 불가 |
| 에이전트 친화 문서 | **양호** — CLAUDE.md 상세, 그러나 검증 결과와 실측 불일치 존재 |

---

## 5. Recommended Fix Plan

### 1단계 (즉시 수정): 자동화 차단·치명적 환경 문제

1. **`verify` 스크립트 추가** — OS별 `;opencv` 진입 + `compileall` + `selftest` + `pyright` 일괄 실행, 실패 시 exit code 표준화
2. **pyright winotify 오류 해결** — import 가드 또는 config 조정으로 문서 주장(0 errors)과 일치
3. **Git 저장소 초기화** — worktree/브랜치 격리 가능하게 함
4. **selftest 러너 개선** — 각 테스트명 출력, 실패 시 `test.__name__` + traceback 보존

### 2단계 (안정성 개선): 크로스 플랫폼·격리

1. **싱글톤 reset / 테스트 DB 경로 오버라이드** — `PHOTOCROPPER_LIBRARY_DB`, `reset_library_repository_for_tests()`
2. **경로 리네이밍 검토** — `;opencv` → `opencv` (breaking이지만 장기 자동화 ROI 큼)
3. **GitHub Actions** — Windows + Linux matrix, OpenCV·PyQt6 설치, selftest headless
4. **CLI exit code 문서화 보강** — cancelled vs failed vs fatal 우선순위 표 추가
5. **모듈 패치 → mock.patch 전환**

### 3단계 (구조 및 TDD 개선): 장기 Superpowers 정합성

1. **pytest 점진 도입** — `selftests/`를 `tests/`로 migration, `-k` 선택 실행
2. **핵심 순수 함수 단위 테스트 분리** — `path_validation`, `processed_index`, `naming_rules`, `BatchRuntimeFlow`
3. **CodeGraph 인덱스 생성 문서화** — `codegraph build` 또는 MCP setup을 CONTRIBUTING에 명시
4. **벤치마크 CI (선택)** — synthetic labels + 소형 fixture로 IoU 회귀 게이트
5. **README/CLAUDE 검증 결과 자동 갱신** — verify 스크립트 출력을 릴리스 체크리스트에 연동

---

## 6. Test Recommendations

에이전트가 안전하게 Red-Green-Refactor를 돌리려면 아래 시나리오를 **pytest parametrized** 또는 selftest 신규 항목으로 추가하는 것을 권장합니다.

### 6.1 배치·CLI 계약

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | recursive batch, output이 input 내부 | 시작 차단, GUI/CLI/Watch 동일 error_code |
| 2 | explicit file list에 missing 1건 포함 | 전체 preflight 차단, queued job 없음 |
| 3 | output path가 파일(디렉터리 아님) | `fatal_error=True`, CLI exit 1 |
| 4 | partial_success만 존재 | 기본 exit 0, `--strict-partial` exit 1 |
| 5 | **취소 + failed>0 혼합** | exit code 정책 문서화 및 assertion 추가 |
| 6 | invalid `failed_folder_name` (`..`, `CON`) | settings/CLI exit 2, classify 진입 차단 |

### 6.2 Watch·동시성

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 7 | stop 후 queued callback 진입 | `CANCELLED`, 출력 파일 미생성 |
| 8 | overwrite 동일 경로, mtime/size 불변 | 재큐잉 없음 |
| 9 | overwrite, signature 변경 | `fileChanged` 재처리 |
| 10 | Watch 중 `move_failed_files` | snapshot에서 False 강제 |

### 6.3 상태·데이터 흐름

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 11 | `skip_processed` + `partial` 인덱스 | skip 아님, warning 후 재처리 |
| 12 | 분류 폴더 locale 변경 시 signature | skip 판정 달라짐 |
| 13 | 멀티포토 partial 저장 | `PARTIAL_SUCCESS`, index `status=partial` |
| 14 | `get_library_repository()` 두 번 호출 | 동일 인스턴스 (현행) + reset 후 새 인스턴스 (개선 후) |

### 6.4 격리·자동화 인프라 (메타 테스트)

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 15 | `verify.ps1` / `verify.sh` 클린룸 | compileall + selftest + pyright 전부 pass |
| 16 | winotify 미설치 Linux | pyright pass (import guard 후) |
| 17 | `QT_QPA_PLATFORM=offscreen` only | Qt selftest 전부 pass |
| 18 | 단일 테스트 `-k test_cli_cancel` | 1건만 실행, <2s (pytest 도입 후) |

### 6.5 회귀 방지 (이미지 처리)

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 19 | synthetic no-photo accurate 모드 | false positive 회귀 없음 (기존 `_test_no_photo_false_positive_regression` 유지) |
| 20 | unicode 경로 워터마크 이미지 | `load_image_unicode` 성공 |
| 21 | grayscale + image watermark | 채널 오류 없음 |
| 22 | `perspective_correct=false` manual preview vs save | 동일 shape |

---

## 부록: CodeGraph 분석 메모

- `.codegraph/`는 워크스페이스에 없으나 MCP `codegraph_explore`는 `;opencv` 경로에 대해 정상 동작(로컬 인덱스가 MCP 서버 측에 존재하는 것으로 추정).
- Blast radius 경고(`process_single`, `validate_settings` 등 "no covering tests found")는 **pytest 네이밍 미인식**에 가깝고, 실제로는 homonym selftest가 존재함. 에이전트는 CodeGraph 경고만으로 테스트 부재를 단정하지 말 것.

---

*감사 수행일: 2026-06-29 | 감사자 역할: Superpowers Reviewer | 코드 수정 없음 (리포트만 작성)*