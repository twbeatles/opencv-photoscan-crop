# Implementation Plan: 사진 스캔 크롭 · CI 검증 게이트

**Branch**: `001-photoscan-verify-gate` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-photoscan-verify-gate/spec.md`

**Note**: Brownfield plan — align codebase with already-shipped intent; use for converge/tasks and future parity.

## Summary

Brownfield plan for `001-photoscan-verify-gate` aligned to commit `a56fc45`. 최근 커밋(pyright CI 실패 해소·pre-push verify 게이트)을 기준으로, 스캔 이미지 자동 크롭이 타입/검증 게이트와 함께 안정 동작하는 기능을 명세한다.

## Technical Context

**Language/Version**: Python

**Primary Dependencies**: opencv-python stack

**Storage**: local files

**Testing**: pyright + scripts verify + tests

**Target Platform**: CLI/local

**Project Type**: cli-tool

**Performance Goals**: Interactive or batch as appropriate for domain

**Constraints**: Reliability and user-visible failure modes prioritized

**Scale/Scope**: Single-user / team tool scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Constitution file is still a Spec Kit template placeholder in this repo — treat as **advisory defaults**:
  - Prefer small, testable modules over monolith growth
  - Keep user-facing paths documented and verifiable
  - No unjustified new top-level packages
- **Gate result (pre)**: PASS with advisory constitution (no hard project-specific rules yet)
- **Gate result (post Phase 1)**: PASS — design stays within existing tree (`opencv package + scripts gates.`)

## Project Structure

### Documentation (this feature)

```text
specs/001-photoscan-verify-gate/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md             # NOT created by /speckit-plan
```

### Source Code (repository root)

```text
opencv/
scripts/
tests/ (if any)
```

**Structure Decision**: opencv package + scripts gates.

## Complexity Tracking

> No constitution violations requiring justification for this brownfield plan.
