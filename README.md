# Environmental Science — Semester Pre/Post Diagnostic

A standards-aligned, online, auto-scoring diagnostic for **9th-grade Environmental
Science** (Georgia course **26.06110**, standards **SEV1–SEV5**). Built to guide
instruction across an 18-week semester and to measure learning at the end.

- **40 multiple-choice items per form**, two **parallel forms**:
  - **Form A = Pre-Test** (Week 1 diagnostic — plan the semester)
  - **Form B = Post-Test** (semester end — measure growth on identical targets)
- **Every item is tagged** to a standard *and* element, so subscores are meaningful.
- **Diagnostic distractors:** most wrong answers are keyed to a *documented* student
  misconception from the GaDOE Environmental Science Teacher Notes ("potential initial
  student ideas"), so the report tells you **what to reteach and to whom** — not just a score.

## What's here

| File | What it is |
|---|---|
| **`assessment.html`** | The complete, self-contained online test. Open in any browser or upload to Google Sites / an LMS. Auto-scores, shows a per-standard diagnostic report, exports results, and includes teacher tools (answer key + **class data analyzer**). No internet, accounts, or plugins required. |
| **`TEACHER_GUIDE.md`** | Answer key, standards/element alignment, mastery bands, the full **misconception map**, and how to turn pre-test data into a semester plan and reteaching groups. |
| **`ITEM_BANK.md`** | Clean printable copy of both forms (for paper use or importing into Google Forms). |
| **`data/items.json`** | Machine-readable item bank. |
| **`build/items.py`** | **Single source of truth** — all 80 items with alignment + misconception keys. |
| **`build/build.py`** | Regenerates every deliverable from `items.py`. |

## Using it with a class

1. Assign **Form A** (pre-test) in Week 1. Students enter their name/class and answer online.
2. Each student gets a short **result code** (`ENV-…`). Collect the codes (LMS, a form, or a shared doc).
3. Open **Teacher tools → Class data analyzer**, paste the codes, and get a class heatmap,
   ready-made reteaching groups, item analysis, and misconception frequencies.
4. At semester end, assign **Form B** and compare the same element subscores to show growth.

**Mastery bands:** Secure ≥ 80% · Developing 50–79% · Beginning < 50%.

## Rebuilding

Editing questions? Change `build/items.py`, then:

```bash
cd build && python3 build.py
```

This re-validates the bank (balanced parallel forms, valid keys) and regenerates
`assessment.html`, `TEACHER_GUIDE.md`, `ITEM_BANK.md`, and `data/items.json`.

---

*Aligned to the Science Georgia Standards of Excellence for Environmental Science
(26.06110), the GaDOE Environmental Science Teacher Notes, and the GaDOE High School
Environmental Science Curriculum Map.*
