# API Quality Checklist: Product Catalog

**Purpose**: Validate the *quality of the written requirements* covering validation rules, error
contracts, and the security gate — before implementation begins. These items test whether the spec
and its design documents are complete, unambiguous, and internally consistent. They do **not** test
whether code works; that is what `quickstart.md` and the test suite are for.
**Created**: 2026-08-12
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate — this is the list a reviewer works through before approving the feature
**Audience**: Reviewer, at PR time

---

## Requirement Completeness — Validation Rules

- [ ] CHK001 Are validation rules documented for every writable field, with no field left implicitly unconstrained? [Completeness, Spec §FR-001–FR-008]
- [ ] CHK002 Is the lower bound on price stated as strictly-greater-than-zero rather than merely non-negative, so a free product is unambiguously refused? [Clarity, Spec §FR-005]
- [ ] CHK003 Is the upper bound on price given as a concrete figure rather than a field-width description? [Measurability, Spec §FR-004]
- [ ] CHK004 Is the required behaviour for an over-precise price stated as refusal rather than leaving rounding as an implementer's choice? [Ambiguity, Spec §Edge Cases]
- [ ] CHK005 Are the rules for name length and emptiness both specified, including whether surrounding whitespace counts toward the limit? [Completeness, Spec §FR-002]
- [ ] CHK006 Is the default value documented for every optional field, and is "empty" distinguished from "absent" for each? [Clarity, Spec §FR-003, §FR-007]
- [ ] CHK007 Is the stock constraint specified as a storage-layer guarantee rather than an application-level check, so the requirement cannot be satisfied by edge validation alone? [Clarity, Spec §FR-006]
- [ ] CHK008 Are requirements defined for a partial update that supplies only some fields, including whether omitted fields are cleared or preserved? [Coverage, Data Model §Input DTO]
- [ ] CHK009 Are validation requirements stated for the administrative maintenance path, or is the spec explicit that they do not apply there? [Gap, Research §D8]

## Requirement Completeness — Error Contracts

- [ ] CHK010 Is a status code specified for every documented failure mode, with none left to implementer discretion? [Completeness, Research §D6]
- [ ] CHK011 Is the response *body shape* specified for each error class, and are the differing shapes of the two classes made explicit? [Completeness, Contract §components/responses]
- [ ] CHK012 Is the rule distinguishing a shape failure from a broken business rule stated as a general principle, rather than only illustrated by examples? [Clarity, Research §D6]
- [ ] CHK013 Are requirements defined for what a caller receives when a request breaks a shape rule *and* a business rule simultaneously? [Gap, Edge Case]
- [ ] CHK014 Is the requirement that a refused submission stores nothing stated explicitly, rather than implied? [Completeness, Spec §SC-002]
- [ ] CHK015 Are error message requirements specified — must a message name the offending field, and is the message language fixed? [Ambiguity, Spec §FR-020]
- [ ] CHK016 Is the requirement that an inactive product and a nonexistent one are indistinguishable stated for the response *body* as well as the status code? [Clarity, Spec §Edge Cases]
- [ ] CHK017 Are requirements defined for malformed request bodies that are not valid JSON at all? [Gap, Coverage]

## Requirement Consistency

- [ ] CHK018 Does the status-code table in research reconcile with the responses declared in the contract, with no operation carrying a code in one and not the other? [Consistency, Research §D6 vs Contract]
- [ ] CHK019 Do the field lists in the spec, the data model, and the contract's `Product` schema agree on exactly which fields are exposed? [Consistency, Spec §FR-018]
- [ ] CHK020 Is the decision to expose price as a string rather than a number stated consistently across the contract, the research decision, and the quickstart? [Consistency, Research §D2]
- [ ] CHK021 Do the spec's stated validation rules and the plan's placement of those rules agree on which layer owns each rule? [Consistency, Plan §Constitution Check]
- [ ] CHK022 Is the divergence from the source tutorial's 400-for-price documented in every place a reader could form the opposite expectation? [Consistency, Plan §Deliberate divergence]
- [ ] CHK023 Do the active-state requirements read consistently between the read path and the write path, given they intentionally differ? [Consistency, Research §D5]
- [ ] CHK024 Does the spec's withdrawn first draft leave no orphaned requirements — for example a published/active distinction that survived in one section but not others? [Conflict, Spec §Resolved Clarifications]

## Acceptance Criteria Quality

- [ ] CHK025 Can every success criterion be evaluated without reading the implementation? [Measurability, Spec §Success Criteria]
- [ ] CHK026 Is the money-precision criterion stated with the class of values that would expose a failure, rather than as a general claim of exactness? [Measurability, Spec §SC-004]
- [ ] CHK027 Are the performance criteria bounded by a stated catalog size, so they are falsifiable? [Measurability, Spec §SC-005]
- [ ] CHK028 Is the "zero image data" criterion expressed so it can be checked against the design rather than only observed at runtime? [Measurability, Spec §SC-008]
- [ ] CHK029 Are acceptance criteria present for each of the three user stories, sufficient to judge that story independently shippable? [Coverage, Spec §User Scenarios]

## Scenario Coverage

- [ ] CHK030 Are requirements defined for the primary read flow, including ordering and the empty-catalog case? [Coverage, Spec §FR-016, §FR-017]
- [ ] CHK031 Are requirements defined for every write verb the contract exposes, including the one that permanently destroys data? [Coverage, Spec §FR-019]
- [ ] CHK032 Are requirements defined for reaching a deactivated product on the write path, and is the reason for that asymmetry recorded? [Coverage, Research §D5]
- [ ] CHK033 Are requirements defined for concurrent edits to the same product, or is their absence recorded as an accepted risk? [Gap, Spec §Edge Cases]
- [ ] CHK034 Are recovery requirements defined for a stored row that violates a later-added invariant — including the blast radius on the listing? [Coverage, Recovery, Data Model §Mapping]
- [ ] CHK035 Are requirements defined for the response when the catalog grows past the assumed scale, given no pagination is specified? [Gap, Research §D7]

## Edge Case Coverage

- [ ] CHK036 Are boundary values specified at each numeric limit — exactly zero price, exactly 99999999.99, exactly 200 characters, exactly zero stock? [Coverage, Edge Case]
- [ ] CHK037 Are requirements defined for an image address that is well-formed but unreachable, and is the system's non-responsibility for resolution stated? [Coverage, Spec §FR-013]
- [ ] CHK038 Are requirements defined for an image address that is well-formed but points outside the intended store? [Gap, Spec §Assumptions]
- [ ] CHK039 Is the absence of an image-host allowlist recorded as a deliberate decision with its risk named, rather than simply omitted? [Assumption, Spec §Assumptions]

## Non-Functional Requirements — Security

- [ ] CHK040 Is the unprotected write path stated as a requirement with a release-blocking condition attached, rather than only as a note? [Completeness, Spec §FR-025]
- [ ] CHK041 Is the specific exposure spelled out — what an unauthenticated caller can do — rather than described generically as "missing auth"? [Clarity, Spec §Security Note]
- [ ] CHK042 Is the environment boundary explicit about where this feature may and may not run? [Clarity, Spec §Security Note]
- [ ] CHK043 Is the security gate carried into the implementation tasks, so it cannot be lost between specification and code? [Traceability, Tasks §T048]
- [ ] CHK044 Are the read and write paths distinguished in the security requirement, given the read-only increment carries a different risk profile? [Clarity, Tasks §Implementation Strategy]
- [ ] CHK045 Are requirements defined for who counts as an administrator once access control lands, or is that explicitly deferred to a named future feature? [Gap, Spec §FR-025]
- [ ] CHK046 Are requirements defined to keep internal error detail out of responses on the unauthenticated surface, consistent with the treatment the health endpoint already received? [Gap, Coverage]

## Non-Functional Requirements — Accessibility & Data Handling

- [ ] CHK047 Is the absence of image alternative text recorded as a known accessibility gap with its consequence stated, rather than silently dropped from the earlier draft? [Assumption, Spec §Assumptions]
- [ ] CHK048 Are requirements defined for how monetary values must be represented across the boundary, including the obligation the representation places on a consumer? [Completeness, Contract §info]
- [ ] CHK049 Are data-retention requirements defined for a hard delete, given it destroys history irreversibly? [Gap, Spec §Edge Cases]

## Dependencies & Assumptions

- [ ] CHK050 Is the external image store documented as a dependency, with provisioning explicitly outside this feature's scope? [Dependency, Spec §Assumptions]
- [ ] CHK051 Are the assumptions about image address durability and public readability stated and marked as unvalidated? [Assumption, Spec §Assumptions]
- [ ] CHK052 Is the assumed catalog scale documented, and are the requirements that depend on it identified? [Assumption, Spec §Assumptions]
- [ ] CHK053 Is the dependency on registering the persistence layer as an application module documented, given nothing in the repository required it before? [Dependency, Research §D1]
- [ ] CHK054 Is the single-currency assumption stated, along with what would have to change if a second currency appeared? [Assumption, Research §D2]

## Ambiguities & Conflicts

- [ ] CHK055 Is a requirement identifier scheme in place, with each functional requirement individually referenceable from tasks and tests? [Traceability]
- [ ] CHK056 Are all clarifications from the first draft marked resolved, with the superseded content removed rather than left to contradict the current model? [Conflict, Spec §Resolved Clarifications]
- [ ] CHK057 Is the unpaginated listing recorded as a decision with its future breaking-change consequence named, rather than as an omission? [Ambiguity, Research §D7]
- [ ] CHK058 Are the two documented gaps that the architecture itself creates — the admin bypass and the listing blast radius — stated in every document a reader might consult in isolation? [Traceability, Research §D8]

---

## Notes

- Check items off as `[x]` as each is confirmed. Add findings inline.
- An unchecked item is a **requirements** defect — something to fix in the spec or design documents
  before writing code, not a bug to file later.
- Items marked `[Gap]` are checking for something that may be legitimately absent. A gap that is
  documented as a deliberate decision passes; a gap that is simply missing does not.
- Three items encode risks the feature carries knowingly: **CHK040–CHK044** (the unprotected write
  path, FR-025), **CHK009 with CHK034** (the admin bypass and its effect on the whole listing), and
  **CHK047** (no image alt text). These are the items most worth a reviewer's attention, because
  each is a decision to accept a cost rather than an oversight.
