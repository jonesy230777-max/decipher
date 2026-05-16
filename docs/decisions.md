# Decipher — Decisions Log

Every non-trivial choice lands here with date, decision, alternative, reason.

---

## 2026-05-16

### D-001 — BMAD version pinned at 6.6.0 (GA), not @alpha
**Decision:** Installed `bmad-method@latest` resolving to **6.6.0** (released as GA).
**Alternative considered:** `bmad-method@alpha` per spec §0.
**Reason:** The `@alpha` dist-tag is no longer published; BMAD shipped past alpha
to stable 6.6.0 (with `@next` at 6.6.1-next.8). Spec §0 anticipates this:
"If `@alpha` resolves to a build older than the current v6 alpha at install time,
fall back to `npx bmad-method@next install`." 6.6.0 stable is preferred over `@next`
prerelease for a prototype baseline.

### D-002 — Tools: claude-code only; Modules: bmm only
**Decision:** Installed BMAD with `--tools claude-code --modules bmm`.
**Reason:** Steve's sole interface is Claude Code (per spec §15 "Steve is sole
operator"). `bmm` (BMad Method) is the planning + dev module; no second IDE
needed.

### D-003 — Project canonical home: `~/Documents/Decipher`
**Decision:** Working directory exactly as spec §2.
**Note:** Earlier in the session, macOS TCC blocked shell access to ~/Documents.
That has since cleared (folder is now read+write from shell). If TCC reasserts,
the workaround is to grant Terminal Full Disk Access in System Settings; do
not relocate the project.

### D-004 — Output folder `_bmad-output/` (BMAD default)
**Decision:** Kept BMAD default `_bmad-output/{planning-artifacts, implementation-artifacts}`.
**Rationale:** Spec §0 lists target artefact paths in `docs/` (analysis.md,
prd.md, architecture.md, ux_design.md, stories/, decisions.md, runbook.md).
We will write those into `docs/` directly while also keeping BMAD's
`_bmad-output/` for its own intermediate workspace, then either:
- (a) symlink `docs/prd.md` → `_bmad-output/planning-artifacts/prd.md`, or
- (b) treat `docs/` as canonical and mirror into `_bmad-output/` on demand.
Leaning (b). Confirm with Steve once he reviews M0.

### D-005 — Configured `bmm.user_skill_level=expert`
**Decision:** Skill level set to expert so BMAD agents skip beginner explanations
and produce condensed output.

### D-006 — Default archetype taxonomy: 4 (Source A), pending Steve
**Decision (placeholder):** Default `archetype_taxonomies.taxonomy_id=1` (the
four EQ Identities: Regulator, Edge-Builder, Observer, Labeler).
**Reason:** Schema must support both per §4 + §15 BLOCKING. Defaulting to
the four lets us scaffold seed data and the classifier without blocking M2-M3;
Steve flips via settings flag once he picks. Will re-raise as a Party Mode
decision before M3 closes.

### D-007 — Spec is the only input
**Decision:** Per Steve's instruction "Decipher_ClaudeCode_SuperPrompt.md only,
no other file", `docs/super_prompt.md` (verbatim copy) is the single input of
record. No other prior project notes inform Decipher. Trendfriend spec
(`~/decipher_platform_design_spec.md`) is unrelated and excluded.
