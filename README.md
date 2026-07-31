# Environmental Science Semester Benchmark (Pre / Post)

A self-contained, offline-capable, standards-aligned **multiple-choice benchmark** for
**Environmental Science, Grade 10**, built on the **Georgia Standards of Excellence**
(course **26.06110**, standards **SEV1–SEV5**).

Everything lives in one file — **`index.html`** — with no external libraries or CDNs.
It works offline, supports light + dark themes, is keyboard-accessible, and is mobile-friendly.

**▶ Live student link (after Pages is enabled — see below):**
`https://arosenbaum993.github.io/prebenchmarkenvsci/`

---

## What students see

- A start screen: **name + class period**, then a choice of **Pre-Test (Form A)** or **Post-Test (Form B)**.
- **One question per screen** with a progress bar, **Flag-for-review**, a **question-navigator grid**,
  free back/forward movement, and answers that can be changed until submit.
- On submit: an **auto-scored** result with a **projected achievement level** and a **per-domain breakdown** (SEV1–SEV5).
  Students **do not** see which answers were correct.
- Attempts auto-save in the browser so a student can resume if a page is refreshed.

## What teachers see

Click **🔒 Teacher** (top right) and enter the passcode. The dashboard has six tabs:

| Tab | What it shows |
|---|---|
| **Class overview** | Attempt counts, pre/post averages, projected-level distribution |
| **Standard mastery** | Color-coded **% correct heatmap** per standard *and* per element (Pre vs Post) |
| **Students** | Per-student score, level, and per-domain breakdown |
| **Growth** | Pre → Post deltas (overall and per domain), matched by name + period |
| **Grouping & reteach** | Auto-generated lists of students **below 50%** on each domain |
| **Data** | CSV export/import, Google Sheet endpoint, and the copy-paste Apps Script code |

> The teacher passcode is **not** printed in this public README. It is delivered privately
> with the teacher materials. You can change it in `index.html` (`CONFIG.passcode`).

## Data & combining devices

- Every submission is stored locally in the browser (`localStorage`).
- The **Data** tab can **export a CSV** from any device and **import CSVs** on one “master”
  device to combine a whole class.
- **Optional Google Sheet logging:** paste a Google Apps Script Web App URL into the Data tab and
  each submission is also posted to your private Google Sheet. If the endpoint is unset or
  unreachable, local save + CSV still work — nothing breaks.

---

## One-time GitHub Pages setup

1. Merge the pull request (or push) so **`index.html`** is on the `main` branch.
2. In this repo, go to **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a branch**.
4. Set **Branch = `main`** and **Folder = `/ (root)`**, then **Save**.
5. Wait ~1 minute. Your test is live at:
   **`https://arosenbaum993.github.io/prebenchmarkenvsci/`**

A `.nojekyll` file is included so GitHub Pages serves the file as-is.

## Optional: Google Sheet logging setup

1. Create a Google Sheet (it stays **private to your account**).
2. **Extensions → Apps Script**, delete any code, and paste the code from **`apps_script/Code.gs`**
   (also shown, with a **Copy** button, in the benchmark’s **Data** tab).
3. **Deploy → New deployment → Web app**, with **Execute as: Me** and **Who has access: Anyone**.
4. Copy the resulting `/exec` URL into the **Data** tab’s *SHEET_ENDPOINT* box (or set `CONFIG.endpoint` in `index.html`).

> 🔐 **Privacy:** *“Who has access: Anyone”* only controls who may **submit** a row to the link.
> It does **not** expose or share your spreadsheet — the Sheet itself stays private to your Google
> account. A shared `SECRET` in the page must match the `SECRET` in the script, so only this test can add rows.

---

## Security notes (public repo)

- The correct-answer key is **obfuscated** and decoded at run time — **View Source does not reveal answers**.
- There is **no answer-key tab** in the student-facing file.
- The teacher guide and the raw item bank (which contain answers) are **kept out of this public repo**
  and delivered separately.

*Built as a classroom pre/post benchmark tool. It is aligned to the GSE and GaDOE Environmental Science
Curriculum Map but is **not** an official Georgia Milestones assessment (Environmental Science has no EOC).*
