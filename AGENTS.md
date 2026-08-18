# AGENTS — opencv-photoscan-crop

AI coding agents should read this file and Spec Kit artifacts before large changes.

<!-- SPECKIT-AGENT-GUIDE:START -->

## Spec Kit / Spec-Driven Development (AI 에이전트 필독)

> 이 블록은 GitHub Spec Kit 활성화 및 기능 명세 작업 결과를 AI 에이전트가 바로 쓰도록 정리한 안내입니다.
> 수정 시 마커 주석을 유지하세요. 스크립트/후속 세션이 이 구간을 갱신합니다.

### 이 저장소 상태

- **프로젝트**: `opencv-photoscan-crop`
- **Spec Kit 초기화**: `.specify/ 있음`
- **에이전트 스킬**: Grok=True, Claude=True, Codex/Agy(.agents)=True
- **활성 기능 디렉터리**: `specs/001-photoscan-verify-gate` (포인터: `.specify/feature.json`)
- **기능 제목**: 사진 스캔 크롭 · CI 검증 게이트
- **산출물**: spec=`yes`, plan=`True`, research/data-model/quickstart=`True`, tasks=`False`, converge=`False`

### 에이전트가 먼저 읽을 파일

1. `specs/001-photoscan-verify-gate/spec.md` — 무엇을/왜 (사용자 스토리, FR, 성공 기준)
2. `specs/001-photoscan-verify-gate/plan.md` — 기술 컨텍스트·구조 결정
3. `specs/001-photoscan-verify-gate/tasks.md` — 실행 가능 작업 목록 (`[x]`=이미 있음, `[ ]`=잔여)
4. `specs/001-photoscan-verify-gate/research.md`, `data-model.md`, `quickstart.md`, `contracts/` — 설계 보조
5. `.specify/feature.json` — 현재 활성 feature path
6. `.specify/memory/constitution.md` — 원칙(템플릿이면 advisory)

### 권장 워크플로 (스킬 / 슬래시 커맨드)

| 단계 | 커맨드 (Grok/Claude 등) | 산출 |
|------|-------------------------|------|
| 원칙 | `/speckit-constitution` | `.specify/memory/constitution.md` |
| 명세 | `/speckit-specify` | `specs/<id>/spec.md` |
| 계획 | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 작업 | `/speckit-tasks` | `tasks.md` |
| 구현 | `/speckit-implement` | 코드 (tasks 순서) |
| 갭점검 | `/speckit-converge` | `tasks.md` 에 Phase Convergence **append-only** |

- Codex skills 모드: `$speckit-specify` 형태일 수 있음
- 스킬 파일: `.grok/skills/speckit-*/SKILL.md`, `.claude/skills/speckit-*/SKILL.md`

### 작업 규칙 (에이전트)

1. **새 기능/큰 변경 전** 활성 `spec.md`·`tasks.md` 를 읽고, 없으면 specify→plan→tasks 순으로 만든다.
2. **구현은 tasks.md 체크리스트**를 따른다. 완료 시 `- [ ]` → `- [x]`.
3. **`/speckit-converge` 는 tasks.md 를 rewrite 하지 않는다** — 잔여 갭만 하단 Phase 로 append.
4. brownfield 프로젝트는 상당 기능이 이미 있을 수 있다. 중복 구현 전에 코드·`[x]` 태스크를 확인한다.
5. 웹/데스크톱 패리티 등 **out-of-scope Assumptions** 는 새 feature 로 분리하는 것을 선호한다.
6. 기본 integration 은 **grok** 이며, 동일 레포에 claude / codex / agy 스킬도 multi-install 되어 있을 수 있다.

### 빠른 경로 예시

```text
# 현재 기능 파악
read specs/001-photoscan-verify-gate/spec.md
read specs/001-photoscan-verify-gate/tasks.md
# 잔여 구현
/speckit-implement   # 또는 tasks.md 의 [ ] 항목만 수행
# 구현 후 갭 재점검
/speckit-converge
```

### 관련 링크

- Spec Kit: https://github.com/github/spec-kit
- 로컬 CLI: `specify` (uv tool, 버전은 `specify version`)

<!-- SPECKIT-AGENT-GUIDE:END -->
