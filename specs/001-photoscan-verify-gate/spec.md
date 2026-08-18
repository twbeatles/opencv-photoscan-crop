# Feature Specification: 사진 스캔 크롭 · CI 검증 게이트

**Feature Branch**: `001-photoscan-verify-gate`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "최근 커밋(pyright CI 실패 해소·pre-push verify 게이트)을 기준으로, 스캔 이미지 자동 크롭이 타입/검증 게이트와 함께 안정 동작하는 기능을 명세한다."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 스캔 이미지 크롭 (Priority: P1)

입력 이미지에서 문서/사진 영역을 감지해 크롭 저장한다.

**Why this priority**: 핵심 기능.

**Independent Test**: 표본 이미지 처리.

**Acceptance Scenarios**:

1. **Given** 유효 이미지이면, **When** 처리하면, **Then** 크롭 결과가 저장된다.

---

### User Story 2 - 품질 게이트 (Priority: P1)

pyright/verify가 push 전 회귀를 막는다.

**Why this priority**: CI 실패 재발 방지.

**Independent Test**: verify 스크립트 실행.

**Acceptance Scenarios**:

1. **Given** 타입 오류가 있으면, **When** 게이트를 실행하면, **Then** 실패한다.
2. **Given** 클린 코드이면, **When** 게이트를 실행하면, **Then** 통과한다.

---

### User Story 3 - 배치 처리 (Priority: P2)

폴더 단위 처리와 실패 파일 보고.

**Why this priority**: 실사용 대량 스캔.

**Independent Test**: 혼합 성공/실패 폴더.

**Acceptance Scenarios**:

1. **Given** 일부 실패 파일이 있으면, **When** 배치가 끝나면, **Then** 실패 목록이 남는다.

### Edge Cases

- 입력이 비어 있거나 부분만 채워진 경우 안전한 안내와 함께 진행/중단을 명확히 한다.
- 장시간 작업·네트워크 실패 시 전체가 조용히 실패하지 않고 상태를 남긴다.
- 동시 실행/중복 클릭 시 중복 부작용을 최소화한다.
- 권한·준비 상태 미충족 시 파괴적 쓰기 없이 차단한다.


## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 이미지 영역 감지·크롭 저장을 제공해야 한다.
- **FR-002**: 배치 처리와 실패 보고를 제공해야 한다.
- **FR-003**: pre-push/CI 검증 게이트를 유지해야 한다.

### Key Entities

- **ScanImage**, **CropResult**, **BatchReport**

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 표본 이미지 크롭 성공
- **SC-002**: 게이트가 타입 오류 차단
- **SC-003**: 배치 실패 목록 누락 0건

## Assumptions

- OpenCV 런타임 사용 가능.
- Brownfield 기준 커밋: `a56fc45`.
