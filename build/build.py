# -*- coding: utf-8 -*-
"""
Build the deliverables from the single-source-of-truth item bank (items.py):

  assessment.html        Standalone, self-contained online test (open in any browser,
                         upload to Google Sites / an LMS, or share the file). Auto-scores,
                         produces a per-standard diagnostic report, exports results, and
                         includes teacher tools (answer key + class data analyzer).
  build/artifact_body.html   Body-only version used for the shareable Artifact preview.
  TEACHER_GUIDE.md       Answer key, standards alignment, misconception map, mastery
                         bands, and how to individualize instruction from the data.
  ITEM_BANK.md           Clean printable copy of both forms (paper or import).
  data/items.json        Machine-readable item bank.
"""

import json
import os
import hashlib
import random
import statistics
from collections import defaultdict, OrderedDict

from items import ITEMS, STANDARDS, ELEMENTS, SEGMENTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LETTERS = ["A", "B", "C", "D"]


# ------------------------------------------------------------------ shuffle
def _seed(s):
    """Stable (PYTHONHASHSEED-independent) integer seed from a string."""
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def shuffle_options(items):
    """Deterministically reorder each item's options so the correct answer is
    spread evenly across A/B/C/D (kills the 'always B' positional tell), and the
    distractor order is scrambled too. answer + diagnoses indices are remapped."""
    # Balanced, deterministically-shuffled target positions for the key, per form.
    targets = {}
    for form in ("A", "B"):
        fids = [it["id"] for it in items if it["form"] == form]
        n = len(fids)
        cycle = ([0, 1, 2, 3] * ((n + 3) // 4))[:n]
        random.Random(_seed("pos-" + form)).shuffle(cycle)
        for k, fid in enumerate(fids):
            targets[fid] = cycle[k]
    out = []
    for it in items:
        tgt = targets[it["id"]]
        correct = it["options"][it["answer"]]
        distractors = [(oi, it["options"][oi]) for oi in range(4) if oi != it["answer"]]
        random.Random(_seed("opt-" + it["id"])).shuffle(distractors)
        newopts = [None] * 4
        remap = {it["answer"]: tgt}
        newopts[tgt] = correct
        for slot, (oi, txt) in zip([p for p in range(4) if p != tgt], distractors):
            newopts[slot] = txt
            remap[oi] = slot
        nit = dict(it)
        nit["options"] = newopts
        nit["answer"] = tgt
        nit["diagnoses"] = {remap[int(k)]: v for k, v in it["diagnoses"].items()}
        out.append(nit)
    return out


ITEMS = shuffle_options(ITEMS)

# ------------------------------------------------------------------ validate
def validate():
    seen = set()
    counts = defaultdict(lambda: {"A": 0, "B": 0})
    for it in ITEMS:
        assert it["id"] not in seen, "duplicate id %s" % it["id"]
        seen.add(it["id"])
        assert it["form"] in ("A", "B"), it["id"]
        assert len(it["options"]) == 4, "%s must have 4 options" % it["id"]
        assert 0 <= it["answer"] <= 3, "%s bad answer index" % it["id"]
        assert it["std"] in STANDARDS, it["id"]
        key = it["std"] + it["el"]
        assert key in ELEMENTS, "unknown element %s" % key
        counts[key][it["form"]] += 1
        for d in it["diagnoses"]:
            assert d != it["answer"], "%s diagnosis on correct answer" % it["id"]
            assert 0 <= d <= 3, it["id"]
    # every element must have equal, non-zero coverage on both parallel forms
    for key, c in counts.items():
        assert c["A"] == c["B"] and c["A"] >= 1, "unbalanced coverage for %s: %s" % (key, c)
    na = sum(1 for i in ITEMS if i["form"] == "A")
    nb = sum(1 for i in ITEMS if i["form"] == "B")
    assert na == nb, "form length mismatch %d/%d" % (na, nb)
    print("validated: %d items | Form A (pre)=%d | Form B (post)=%d | %d elements"
          % (len(ITEMS), na, nb, len(counts)))

    # --- answer-key quality checks (guard against positional & length tells) ---
    for form in ("A", "B"):
        fi = [i for i in ITEMS if i["form"] == form]
        pos = defaultdict(int)
        for i in fi:
            pos[i["answer"]] += 1
        spread = {LETTERS[k]: pos.get(k, 0) for k in range(4)}
        # each key position should appear a balanced number of times
        assert max(spread.values()) - min(spread.values()) <= 1, \
            "Form %s answer positions unbalanced: %s" % (form, spread)
        # correct answer should not systematically be the longest option
        longest = sum(1 for i in fi
                      if len(i["options"][i["answer"]]) == max(len(o) for o in i["options"])
                      and [len(o) for o in i["options"]].count(max(len(o) for o in i["options"])) == 1)
        rate = longest / len(fi)
        assert rate <= 0.40, "Form %s: correct answer is the unique longest in %.0f%% of items" % (form, rate * 100)
        print("  Form %s key positions %s | correct-is-longest %.0f%%" % (form, spread, rate * 100))
    return na

FORM_LEN = validate()

# ------------------------------------------------------------------ data json
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "items.json"), "w", encoding="utf-8") as f:
    json.dump({"standards": STANDARDS, "elements": ELEMENTS,
               "segments": SEGMENTS, "items": ITEMS}, f, indent=2, ensure_ascii=False)

# JS payload (compact)
JS_DATA = json.dumps({
    "standards": STANDARDS,
    "elements": ELEMENTS,
    "segments": SEGMENTS,
    "formLen": FORM_LEN,
    "items": [{
        "id": i["id"], "form": i["form"], "std": i["std"], "el": i["el"],
        "target": i["target"], "stem": i["stem"], "options": i["options"],
        "answer": i["answer"], "diagnoses": {str(k): v for k, v in i["diagnoses"].items()},
    } for i in ITEMS],
}, ensure_ascii=False)

# ------------------------------------------------------------------ HTML inner
STYLE = r"""
<style>
:root{
  --bg:#eef2ee; --surface:#ffffff; --surface-2:#e8ede8;
  --ink:#17231e; --ink-soft:#516059; --ink-faint:#7d8a83;
  --line:#d6ddd6; --line-strong:#c2cbc2;
  --primary:#1f4a3f; --primary-ink:#f3f7f4;
  --accent:#0e7c86; --accent-soft:#e2f0f1;
  --good:#2e7d5b; --good-bg:#e4f2ea;
  --warn:#a5711a; --warn-bg:#f6ecd8;
  --crit:#b1442c; --crit-bg:#f6e2db;
  --shadow:0 1px 2px rgba(20,40,32,.06),0 6px 20px rgba(20,40,32,.06);
  --radius:14px; --radius-sm:9px;
  --serif:Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0f1613; --surface:#16211c; --surface-2:#1c2a23;
    --ink:#e8eee9; --ink-soft:#a6b3ab; --ink-faint:#7c8a82;
    --line:#2a3a31; --line-strong:#38493f;
    --primary:#8fc3b0; --primary-ink:#0f1613;
    --accent:#3fb6c0; --accent-soft:#123338;
    --good:#66c295; --good-bg:#12291f;
    --warn:#d8a44e; --warn-bg:#2c2413;
    --crit:#e08065; --crit-bg:#2e1a14;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35);
  }
}
:root[data-theme="light"]{
  --bg:#eef2ee; --surface:#ffffff; --surface-2:#e8ede8;
  --ink:#17231e; --ink-soft:#516059; --ink-faint:#7d8a83;
  --line:#d6ddd6; --line-strong:#c2cbc2;
  --primary:#1f4a3f; --primary-ink:#f3f7f4; --accent:#0e7c86; --accent-soft:#e2f0f1;
  --good:#2e7d5b; --good-bg:#e4f2ea; --warn:#a5711a; --warn-bg:#f6ecd8;
  --crit:#b1442c; --crit-bg:#f6e2db;
  --shadow:0 1px 2px rgba(20,40,32,.06),0 6px 20px rgba(20,40,32,.06);
}
:root[data-theme="dark"]{
  --bg:#0f1613; --surface:#16211c; --surface-2:#1c2a23;
  --ink:#e8eee9; --ink-soft:#a6b3ab; --ink-faint:#7c8a82;
  --line:#2a3a31; --line-strong:#38493f;
  --primary:#8fc3b0; --primary-ink:#0f1613; --accent:#3fb6c0; --accent-soft:#123338;
  --good:#66c295; --good-bg:#12291f; --warn:#d8a44e; --warn-bg:#2c2413;
  --crit:#e08065; --crit-bg:#2e1a14;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  line-height:1.55;-webkit-font-smoothing:antialiased;font-size:16px}
.wrap{max-width:860px;margin:0 auto;padding:0 20px 96px}
h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.2;text-wrap:balance;margin:0}
a{color:var(--accent)}
.eyebrow{font-family:var(--sans);text-transform:uppercase;letter-spacing:.12em;
  font-size:.7rem;font-weight:700;color:var(--accent)}
.muted{color:var(--ink-soft)}
.tnum{font-variant-numeric:tabular-nums}

/* header */
header.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.top-inner{max-width:860px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:14px}
.mark{width:34px;height:34px;border-radius:9px;flex:0 0 auto;background:
  radial-gradient(circle at 30% 28%,var(--accent),var(--primary));position:relative}
.mark::after{content:"";position:absolute;inset:0;border-radius:9px;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.18)}
.top h1{font-size:1.02rem}
.top .sub{font-size:.72rem;color:var(--ink-soft);font-family:var(--sans)}
.spacer{flex:1}
.theme-btn{border:1px solid var(--line-strong);background:var(--surface);color:var(--ink-soft);
  border-radius:20px;padding:6px 12px;font-size:.76rem;cursor:pointer;font-family:var(--sans)}
.theme-btn:hover{color:var(--ink);border-color:var(--accent)}
.progress-rail{height:4px;background:var(--surface-2);width:100%}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--primary));width:0;
  transition:width .35s ease}

/* hero / cards */
.hero{padding:44px 0 8px}
.hero h2{font-size:2rem;margin-bottom:10px;letter-spacing:-.01em}
.hero p{max-width:60ch;color:var(--ink-soft);margin:0}
.badgerow{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 6px}
.badge{font-size:.72rem;font-weight:600;color:var(--ink-soft);background:var(--surface);
  border:1px solid var(--line);border-radius:20px;padding:5px 11px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px}
@media(max-width:680px){.grid2{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;box-shadow:var(--shadow)}
.card h3{font-size:1.12rem;margin-bottom:6px}
.card p{margin:0 0 14px;color:var(--ink-soft);font-size:.92rem}
.field{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}
.field label{font-size:.78rem;font-weight:600;color:var(--ink-soft)}
.field input,.field select{font:inherit;padding:9px 11px;border:1px solid var(--line-strong);
  border-radius:var(--radius-sm);background:var(--bg);color:var(--ink)}
.field input:focus,.field select:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
.form-toggle{display:flex;gap:8px}
.form-toggle label{flex:1;border:1px solid var(--line-strong);border-radius:var(--radius-sm);
  padding:10px 12px;cursor:pointer;font-size:.86rem;text-align:center;background:var(--bg)}
.form-toggle input{position:absolute;opacity:0;width:0;height:0}
.form-toggle input:checked + span{color:var(--primary);font-weight:700}
.form-toggle label:has(input:checked){border-color:var(--accent);background:var(--accent-soft);
  box-shadow:inset 0 0 0 1px var(--accent)}

.btn{font:inherit;font-weight:600;cursor:pointer;border-radius:var(--radius-sm);padding:11px 18px;
  border:1px solid transparent;background:var(--primary);color:var(--primary-ink)}
.btn:hover{filter:brightness(1.06)}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn.ghost{background:var(--surface);color:var(--ink);border-color:var(--line-strong)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.sm{padding:8px 13px;font-size:.82rem}
.btnrow{display:flex;flex-wrap:wrap;gap:10px}

/* test */
.section-head{display:flex;align-items:baseline;gap:12px;margin:30px 0 4px}
.section-head .std{font-size:.8rem;font-weight:700;color:var(--accent);font-family:var(--sans)}
.section-head h2{font-size:1.3rem}
.section-desc{color:var(--ink-soft);font-size:.9rem;margin:2px 0 14px}
.q{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px 18px 8px;margin:14px 0;box-shadow:var(--shadow);border:0;min-width:0}
.q legend{padding:0;display:block;width:100%;float:left}
.q::after{content:"";display:table;clear:both}
.q .qmeta{font-size:.7rem;color:var(--ink-faint);font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;margin-bottom:6px}
.q .stem{font-size:1.02rem;font-weight:500;margin-bottom:12px}
.opt{display:flex;gap:11px;align-items:flex-start;padding:11px 13px;border:1px solid var(--line);
  border-radius:var(--radius-sm);margin-bottom:9px;cursor:pointer;background:var(--bg);transition:border-color .15s}
.opt:hover{border-color:var(--accent)}
.opt input{margin-top:3px;accent-color:var(--accent);width:17px;height:17px;flex:0 0 auto}
.opt .lett{font-weight:700;color:var(--ink-soft);font-family:var(--mono);font-size:.85rem;margin-top:1px}
.opt:has(input:checked){border-color:var(--accent);background:var(--accent-soft)}
.opt:has(input:focus-visible){outline:2px solid var(--accent);outline-offset:1px}
.navbar{display:flex;align-items:center;gap:12px;margin-top:22px;flex-wrap:wrap}
.count-pill{font-size:.8rem;color:var(--ink-soft);background:var(--surface);border:1px solid var(--line);
  border-radius:20px;padding:6px 12px;font-variant-numeric:tabular-nums}
.dots{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}
.dot{width:26px;height:26px;border-radius:7px;border:1px solid var(--line-strong);background:var(--surface);
  font-size:.72rem;cursor:pointer;color:var(--ink-soft);font-variant-numeric:tabular-nums}
.dot.done{background:var(--primary);color:var(--primary-ink);border-color:var(--primary)}
.dot.current{outline:2px solid var(--accent);outline-offset:1px}

/* report */
.report-head{padding:24px 0 6px}
.scorecard{display:flex;gap:18px;flex-wrap:wrap;align-items:center;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow);margin-top:8px}
.ring{--p:0;width:104px;height:104px;border-radius:50%;flex:0 0 auto;
  background:conic-gradient(var(--accent) calc(var(--p)*1%),var(--surface-2) 0);
  display:grid;place-items:center}
.ring .inner{width:78px;height:78px;border-radius:50%;background:var(--surface);display:grid;place-items:center;text-align:center}
.ring .pct{font-size:1.5rem;font-weight:700;font-family:var(--mono);line-height:1}
.ring .cap{font-size:.62rem;color:var(--ink-soft);text-transform:uppercase;letter-spacing:.08em}
.std-row{display:flex;align-items:center;gap:12px;padding:12px 0;border-top:1px solid var(--line)}
.std-row:first-of-type{border-top:0}
.std-row .lab{flex:1;min-width:0}
.std-row .lab .code{font-weight:700;font-size:.82rem}
.std-row .lab .name{font-size:.82rem;color:var(--ink-soft)}
.meter{width:120px;height:9px;border-radius:6px;background:var(--surface-2);overflow:hidden;flex:0 0 auto}
.meter span{display:block;height:100%}
.band{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:3px 9px;
  border-radius:20px;flex:0 0 auto;width:96px;text-align:center}
.band.secure{color:var(--good);background:var(--good-bg)}
.band.developing{color:var(--warn);background:var(--warn-bg)}
.band.beginning{color:var(--crit);background:var(--crit-bg)}
.fill.secure{background:var(--good)} .fill.developing{background:var(--warn)} .fill.beginning{background:var(--crit)}

.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px 20px;box-shadow:var(--shadow);margin-top:16px}
.panel h3{font-size:1.05rem;margin-bottom:4px}
details.teacher{margin-top:16px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}
details.teacher>summary{cursor:pointer;padding:15px 20px;font-weight:600;list-style:none;
  display:flex;align-items:center;gap:10px}
details.teacher>summary::-webkit-details-marker{display:none}
details.teacher>summary::before{content:"▸";color:var(--accent);transition:transform .2s}
details.teacher[open]>summary::before{transform:rotate(90deg)}
.tablewrap{overflow-x:auto;margin:4px 0}
table{border-collapse:collapse;width:100%;font-size:.84rem;min-width:520px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--ink-soft);font-weight:700}
td.tnum,th.tnum{text-align:right;font-variant-numeric:tabular-nums}
tr .ok{color:var(--good);font-weight:700} tr .no{color:var(--crit);font-weight:700}
.cellband{display:inline-block;padding:2px 7px;border-radius:6px;font-weight:700;font-size:.78rem;font-variant-numeric:tabular-nums}
.cellband.secure{color:var(--good);background:var(--good-bg)}
.cellband.developing{color:var(--warn);background:var(--warn-bg)}
.cellband.beginning{color:var(--crit);background:var(--crit-bg)}
.miscrow{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-top:1px dashed var(--line)}
.miscrow:first-child{border-top:0}
.freq{font-family:var(--mono);font-weight:700;color:var(--crit);flex:0 0 auto;font-variant-numeric:tabular-nums}
textarea{width:100%;min-height:120px;font-family:var(--mono);font-size:.8rem;padding:12px;
  border:1px solid var(--line-strong);border-radius:var(--radius-sm);background:var(--bg);color:var(--ink);resize:vertical}
textarea:focus{outline:2px solid var(--accent);outline-offset:1px}
.codebox{font-family:var(--mono);font-size:.74rem;word-break:break-all;background:var(--bg);
  border:1px dashed var(--line-strong);border-radius:var(--radius-sm);padding:11px;color:var(--ink-soft);margin-top:8px}
.note{font-size:.82rem;color:var(--ink-soft);background:var(--accent-soft);border-left:3px solid var(--accent);
  padding:10px 14px;border-radius:0 8px 8px 0;margin:12px 0}
.hidden{display:none!important}
.legend-key{display:flex;gap:14px;flex-wrap:wrap;font-size:.75rem;color:var(--ink-soft);margin-top:10px}
.legend-key b{font-weight:700}
footer.foot{max-width:860px;margin:40px auto 0;padding:20px;border-top:1px solid var(--line);
  color:var(--ink-faint);font-size:.76rem}
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
@media print{
  header.top,.navbar,.dots,.btnrow,.theme-btn,.export-row,details.teacher>summary::before{display:none!important}
  body{background:#fff;color:#000} .card,.panel,.scorecard{box-shadow:none;border-color:#bbb}
  details.teacher[open]{border-color:#bbb}
}
</style>
"""

BODY = r"""
<header class="top">
  <div class="top-inner">
    <div class="mark" aria-hidden="true"></div>
    <div>
      <h1>Environmental Science &mdash; Semester Diagnostic</h1>
      <div class="sub">Georgia SEV1&ndash;SEV5 &middot; course 26.06110 &middot; Grade 9</div>
    </div>
    <div class="spacer"></div>
    <button class="theme-btn" id="themeBtn" type="button" aria-label="Toggle light or dark theme">Theme</button>
  </div>
  <div class="progress-rail" id="rail" hidden><div class="progress-fill" id="fill"></div></div>
</header>

<main class="wrap">

  <!-- ============ HOME ============ -->
  <section id="home">
    <div class="hero">
      <div class="eyebrow">Pre &amp; Post Assessment</div>
      <h2>One test, two jobs: find the gaps in week&nbsp;1, measure the growth in week&nbsp;18.</h2>
      <p>Forty multiple-choice items built directly from the Georgia Standards of Excellence and GaDOE
      Teacher Notes. Every question is tagged to a standard and element, and most wrong answers are keyed
      to a specific, documented student misconception &mdash; so the results tell you <em>what</em> to reteach and
      <em>to&nbsp;whom</em>, not just a score.</p>
      <div class="badgerow" id="blueprintBadges"></div>
    </div>

    <div class="grid2">
      <div class="card">
        <h3>Take the assessment</h3>
        <p>Students enter their name and class, choose the form the teacher assigns, and answer online. Results are scored instantly.</p>
        <div class="field"><label for="stuName">Student name</label><input id="stuName" autocomplete="off" placeholder="First and last name"></div>
        <div class="grid2" style="margin-top:0;gap:12px">
          <div class="field"><label for="stuClass">Class / period</label><input id="stuClass" autocomplete="off" placeholder="e.g. Period 3"></div>
          <div class="field"><label for="stuId">Student ID (optional)</label><input id="stuId" autocomplete="off" placeholder="ID"></div>
        </div>
        <div class="field">
          <label>Which form?</label>
          <div class="form-toggle" role="radiogroup" aria-label="Choose test form">
            <label><input type="radio" name="form" value="A" checked><span>Pre-Test &middot; Form A</span></label>
            <label><input type="radio" name="form" value="B"><span>Post-Test &middot; Form B</span></label>
          </div>
        </div>
        <button class="btn" id="startBtn" type="button" style="width:100%">Start the assessment &rarr;</button>
      </div>

      <div class="card">
        <h3>Teacher tools</h3>
        <p>Review every answer and its standard alignment, or paste your students' result codes to build a class picture and instructional groups.</p>
        <div class="btnrow" style="flex-direction:column">
          <button class="btn ghost" id="keyBtn" type="button" style="width:100%">Answer key &amp; alignment</button>
          <button class="btn ghost" id="analyzeBtn" type="button" style="width:100%">Class data analyzer</button>
        </div>
        <div class="note" style="margin-top:16px">Robust data, no login: after each student finishes, they get a short
        <b>result code</b>. Collect the codes (LMS, form, or shared doc) and paste them into the analyzer for a
        class heatmap, item analysis, and ready-made reteaching groups.</div>
      </div>
    </div>
  </section>

  <!-- ============ TEST ============ -->
  <section id="test" class="hidden">
    <div class="report-head">
      <div class="eyebrow" id="testFormLabel">Pre-Test &middot; Form A</div>
      <h2 id="testTitle" style="font-size:1.5rem">Answer every question you can.</h2>
      <p class="muted" style="margin:6px 0 0">There's no time limit. If you're unsure, pick your best answer &mdash; a guess still tells your teacher what to review. Your honest answers help plan the semester.</p>
    </div>
    <div class="dots" id="dots" aria-hidden="true"></div>
    <form id="quizForm"><div id="sections"></div></form>
    <div class="navbar">
      <button class="btn ghost sm" id="prevBtn" type="button">&larr; Previous</button>
      <button class="btn ghost sm" id="nextBtn" type="button">Next section &rarr;</button>
      <span class="spacer"></span>
      <span class="count-pill" id="answered">0 / 0 answered</span>
      <button class="btn" id="submitBtn" type="button">Submit</button>
    </div>
  </section>

  <!-- ============ RESULTS ============ -->
  <section id="results" class="hidden"></section>

  <!-- ============ ANSWER KEY ============ -->
  <section id="answerkey" class="hidden"></section>

  <!-- ============ ANALYZER ============ -->
  <section id="analyzer" class="hidden"></section>

</main>

<footer class="foot">
  Aligned to the Science Georgia Standards of Excellence for Environmental Science (26.06110) and the GaDOE
  Environmental Science Teacher Notes &amp; High School Curriculum Map. Item distractors are drawn from the
  &ldquo;potential initial student ideas&rdquo; documented in the Teacher Notes. Built as a classroom diagnostic tool.
</footer>
"""

SCRIPT = r"""
<script>
const DATA = /*DATA*/;
const LET = ["A","B","C","D"];
const STD_ORDER = ["SEV1","SEV2","SEV3","SEV4","SEV5"];
const $ = s => document.querySelector(s);
const el = (t,c,h)=>{const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e;};
const esc = s => String(s).replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
function band(p){ return p>=80?"secure":(p>=50?"developing":"beginning"); }
function bandLabel(p){ return p>=80?"Secure":(p>=50?"Developing":"Beginning"); }

/* ---------- theme ---------- */
const themeBtn=$("#themeBtn");
themeBtn.addEventListener("click",()=>{
  const cur=document.documentElement.getAttribute("data-theme");
  const sysDark=window.matchMedia("(prefers-color-scheme:dark)").matches;
  const next=(cur? cur : (sysDark?"dark":"light"))==="dark"?"light":"dark";
  document.documentElement.setAttribute("data-theme",next);
});

/* ---------- blueprint badges ---------- */
(function(){
  const byStd={}; DATA.items.filter(i=>i.form==="A").forEach(i=>byStd[i.std]=(byStd[i.std]||0)+1);
  const row=$("#blueprintBadges");
  STD_ORDER.forEach(s=>row.appendChild(el("span","badge",esc(s)+" &middot; "+byStd[s]+" items")));
  row.appendChild(el("span","badge","40 items &middot; ~30 min"));
})();

/* ---------- view switch ---------- */
function show(id){
  ["home","test","results","answerkey","analyzer"].forEach(v=>$("#"+v).classList.toggle("hidden",v!==id));
  $("#rail").hidden = (id!=="test");
  window.scrollTo({top:0,behavior:"instant"in window?"instant":"auto"});
}

/* ================= TEST ENGINE ================= */
let ST=null;
function startTest(form,meta){
  const items=DATA.items.filter(i=>i.form===form);
  const sections=STD_ORDER.map(std=>({std,items:items.filter(i=>i.std===std)}));
  ST={form,meta,items,sections,cur:0,ans:{}};
  $("#testFormLabel").innerHTML = form==="A"?"Pre-Test &middot; Form A":"Post-Test &middot; Form B";
  renderSections(); renderDots(); gotoSection(0); updateCount();
  show("test");
}
function renderSections(){
  const host=$("#sections"); host.innerHTML="";
  ST.sections.forEach((sec,si)=>{
    const wrap=el("div","secblock"); wrap.dataset.si=si; if(si!==0) wrap.classList.add("hidden");
    const head=el("div","section-head");
    head.appendChild(el("span","std",esc(sec.std)));
    head.appendChild(el("h2",null,esc(DATA.standards[sec.std])));
    wrap.appendChild(head);
    wrap.appendChild(el("div","section-desc","Section "+(si+1)+" of 5"));
    sec.items.forEach((it,qi)=>{
      const fs=el("fieldset","q"); fs.id="q_"+it.id;
      const lg=el("legend");
      lg.appendChild(el("div","qmeta","Question "+(globalIndex(it.id)+1)));
      lg.appendChild(el("div","stem",esc(it.stem)));
      fs.appendChild(lg);
      it.options.forEach((op,oi)=>{
        const lab=el("label","opt");
        lab.innerHTML='<input type="radio" name="'+it.id+'" value="'+oi+'">'+
          '<span class="lett">'+LET[oi]+'</span><span>'+esc(op)+'</span>';
        lab.querySelector("input").addEventListener("change",()=>{ST.ans[it.id]=oi;updateCount();markDots();});
        fs.appendChild(lab);
      });
      wrap.appendChild(fs);
    });
    host.appendChild(wrap);
  });
}
function globalIndex(id){ return ST.items.findIndex(i=>i.id===id); }
function renderDots(){
  const d=$("#dots"); d.innerHTML="";
  ST.items.forEach((it,i)=>{
    const b=el("button","dot",(i+1)); b.type="button"; b.dataset.id=it.id;
    b.title="Question "+(i+1);
    b.addEventListener("click",()=>{ const si=STD_ORDER.indexOf(it.std); gotoSection(si);
      setTimeout(()=>{const q=$("#q_"+it.id); if(q)q.scrollIntoView({behavior:"smooth",block:"center"});},60); });
    d.appendChild(b);
  });
  markDots();
}
function markDots(){
  document.querySelectorAll("#dots .dot").forEach(b=>{ b.classList.toggle("done", ST.ans[b.dataset.id]!=null);
    const it=ST.items.find(i=>i.id===b.dataset.id);
    b.classList.toggle("current", STD_ORDER.indexOf(it.std)===ST.cur); });
}
function gotoSection(si){
  ST.cur=Math.max(0,Math.min(ST.sections.length-1,si));
  document.querySelectorAll(".secblock").forEach(b=>b.classList.toggle("hidden",+b.dataset.si!==ST.cur));
  $("#prevBtn").disabled=ST.cur===0;
  $("#nextBtn").classList.toggle("hidden",ST.cur===ST.sections.length-1);
  markDots(); updateFill();
  window.scrollTo({top:0,behavior:"smooth"});
}
function updateFill(){ $("#fill").style.width=((ST.cur+1)/ST.sections.length*100)+"%"; }
function updateCount(){
  const n=Object.keys(ST.ans).length, t=ST.items.length;
  $("#answered").textContent=n+" / "+t+" answered";
}
$("#prevBtn").addEventListener("click",()=>gotoSection(ST.cur-1));
$("#nextBtn").addEventListener("click",()=>gotoSection(ST.cur+1));
$("#startBtn").addEventListener("click",()=>{
  const name=$("#stuName").value.trim();
  if(!name){ $("#stuName").focus(); $("#stuName").style.borderColor="var(--crit)"; return; }
  const form=document.querySelector('input[name="form"]:checked').value;
  startTest(form,{name,cls:$("#stuClass").value.trim(),id:$("#stuId").value.trim()});
});
$("#submitBtn").addEventListener("click",()=>{
  const un=ST.items.length-Object.keys(ST.ans).length;
  if(un>0 && !confirm(un+" question(s) are still blank. Submit anyway? Blank answers count as not yet mastered.")) return;
  showResults(score(ST.form,ST.ans,ST.meta));
});

/* ================= SCORING ================= */
function score(form,ans,meta){
  const items=DATA.items.filter(i=>i.form===form);
  let correct=0; const byStd={}, byEl={}, misc={}, perItem=[];
  STD_ORDER.forEach(s=>byStd[s]={c:0,t:0});
  items.forEach(it=>{
    const key=it.std+it.el; byEl[key]=byEl[key]||{c:0,t:0,target:it.target};
    const sel=ans[it.id]; const ok=sel===it.answer;
    byStd[it.std].t++; byEl[key].t++;
    if(ok){correct++;byStd[it.std].c++;byEl[key].c++;}
    else if(sel!=null && it.diagnoses[String(sel)]){
      const m=it.diagnoses[String(sel)]; misc[m]=misc[m]||{n:0,std:it.std,el:it.el}; misc[m].n++;
    }
    perItem.push({id:it.id,std:it.std,el:it.el,ok,sel,answer:it.answer,blank:sel==null});
  });
  return {form,meta,correct,total:items.length,byStd,byEl,misc,perItem,
          pct:Math.round(correct/items.length*100)};
}

/* ================= RESULTS VIEW ================= */
function showResults(R){
  const host=$("#results"); host.innerHTML="";
  const pre=R.form==="A";
  host.appendChild(el("div","report-head",
    '<div class="eyebrow">'+(pre?"Pre-Test &middot; Form A &middot; Diagnostic":"Post-Test &middot; Form B &middot; Semester")+'</div>'+
    '<h2 style="font-size:1.6rem">'+esc(R.meta.name||"Results")+
    (R.meta.cls?' &middot; <span class="muted" style="font-size:1rem">'+esc(R.meta.cls)+'</span>':'')+'</h2>'));

  // scorecard + per-standard
  const sc=el("div"); const card=el("div","scorecard");
  const ring=el("div","ring"); ring.style.setProperty("--p",R.pct);
  ring.innerHTML='<div class="inner"><div><div class="pct tnum">'+R.pct+'%</div><div class="cap">'+R.correct+' / '+R.total+'</div></div></div>';
  card.appendChild(ring);
  const stdWrap=el("div"); stdWrap.style.flex="1"; stdWrap.style.minWidth="280px";
  STD_ORDER.forEach(s=>{
    const o=R.byStd[s], p=Math.round(o.c/o.t*100), bd=band(p);
    const row=el("div","std-row");
    row.innerHTML='<div class="lab"><div class="code">'+s+' &middot; '+o.c+'/'+o.t+'</div>'+
      '<div class="name">'+esc(DATA.standards[s])+'</div></div>'+
      '<div class="meter"><span class="fill '+bd+'" style="width:'+p+'%"></span></div>'+
      '<span class="band '+bd+'">'+bandLabel(p)+'</span>';
    stdWrap.appendChild(row);
  });
  card.appendChild(stdWrap); sc.appendChild(card); host.appendChild(sc);

  // student-facing framing
  const focus=STD_ORDER.filter(s=>R.byStd[s].c/R.byStd[s].t<0.5);
  const strong=STD_ORDER.filter(s=>R.byStd[s].c/R.byStd[s].t>=0.8);
  const p=el("div","panel");
  if(pre){
    p.innerHTML='<h3>What this means</h3><p class="muted" style="font-size:.92rem;margin:4px 0 0">'+
      'This is a pre-test &mdash; it does not count as a grade. It shows your teacher which topics to spend more time on for you. '+
      (strong.length?('You already show strength in <b>'+strong.join(", ")+'</b>. '):'')+
      (focus.length?('The class will build up <b>'+focus.join(", ")+'</b> together this semester.'):'You are off to a strong start across the board.')+'</p>';
  } else {
    p.innerHTML='<h3>Where you landed</h3><p class="muted" style="font-size:.92rem;margin:4px 0 0">'+
      'Overall mastery: <b>'+bandLabel(R.pct)+'</b>. '+
      (strong.length?('Secure standards: <b>'+strong.join(", ")+'</b>. '):'')+
      (focus.length?('Keep reviewing: <b>'+focus.join(", ")+'</b>.'):'Strong finish across every standard.')+
      ' Compare with your pre-test to see your growth.</p>';
  }
  host.appendChild(p);
  host.appendChild(bandKey());

  // result code + exports
  const code=encodeResult(R);
  const exp=el("div","panel export-row");
  exp.innerHTML='<h3>Submit your results</h3>'+
    '<p class="muted" style="font-size:.88rem;margin:4px 0 8px">Copy this result code and turn it in the way your teacher asked (paste into the assignment, form, or shared doc). It lets your teacher build the class report.</p>'+
    '<div class="codebox" id="codeBox">'+code+'</div>';
  const brow=el("div","btnrow"); brow.style.marginTop="12px";
  brow.appendChild(mkBtn("Copy result code","btn sm",()=>copy(code)));
  brow.appendChild(mkBtn("Download CSV","btn ghost sm",()=>downloadCSV(R)));
  brow.appendChild(mkBtn("Print / Save PDF","btn ghost sm",()=>window.print()));
  brow.appendChild(mkBtn("Home","btn ghost sm",()=>show("home")));
  exp.appendChild(brow); host.appendChild(exp);

  // TEACHER detail
  const det=el("details","teacher");
  det.appendChild(el("summary",null,"Teacher detail &mdash; element breakdown, misconceptions, item map"));
  const inner=el("div"); inner.style.padding="0 20px 20px";
  // element table
  inner.appendChild(el("h3",null,"Mastery by element"));
  inner.lastChild.style.margin="6px 0 4px"; inner.lastChild.style.fontSize="1rem";
  const tw=el("div","tablewrap"); const tb=el("table");
  tb.innerHTML="<thead><tr><th>Element</th><th>Target</th><th class='tnum'>Score</th><th>Band</th></tr></thead>";
  const tbody=el("tbody");
  Object.keys(DATA.elements).forEach(k=>{
    if(!R.byEl[k])return; const o=R.byEl[k], pp=Math.round(o.c/o.t*100), bd=band(pp);
    const tr=el("tr");
    tr.innerHTML="<td><b>"+k+"</b></td><td>"+esc(o.target)+"</td><td class='tnum'>"+o.c+"/"+o.t+
      "</td><td><span class='cellband "+bd+"'>"+pp+"%</span></td>";
    tbody.appendChild(tr);
  });
  tb.appendChild(tbody); tw.appendChild(tb); inner.appendChild(tw);
  // misconceptions
  inner.appendChild(el("h3",null,"Misconceptions to address"));
  inner.lastChild.style.margin="18px 0 4px"; inner.lastChild.style.fontSize="1rem";
  const mk=Object.keys(R.misc);
  if(mk.length){
    mk.sort((a,b)=>R.misc[b].n-R.misc[a].n).forEach(m=>{
      const mr=el("div","miscrow");
      mr.innerHTML='<span class="freq">'+R.misc[m].std+R.misc[m].el+'</span><span>'+esc(m)+'</span>';
      inner.appendChild(mr);
    });
  } else { inner.appendChild(el("p","muted","No keyed misconceptions were triggered. Any misses were blanks or non-diagnostic distractors.")); }
  det.appendChild(inner); host.appendChild(det);

  show("results");
}
function bandKey(){
  const k=el("div","legend-key");
  k.innerHTML='<span><b style="color:var(--good)">Secure</b> &ge;80%</span>'+
    '<span><b style="color:var(--warn)">Developing</b> 50&ndash;79%</span>'+
    '<span><b style="color:var(--crit)">Beginning</b> &lt;50%</span>';
  return k;
}
function mkBtn(label,cls,fn){ const b=el("button",cls,label); b.type="button"; b.addEventListener("click",fn); return b; }
function copy(t){ navigator.clipboard&&navigator.clipboard.writeText(t).then(()=>toast("Copied result code")).catch(()=>fallbackCopy(t)); }
function fallbackCopy(t){ const ta=el("textarea"); ta.value=t; document.body.appendChild(ta); ta.select();
  try{document.execCommand("copy");toast("Copied");}catch(e){} ta.remove(); }
let toastT; function toast(m){ let x=$("#toast"); if(!x){x=el("div");x.id="toast";
  x.style.cssText="position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:var(--primary);color:var(--primary-ink);padding:10px 18px;border-radius:20px;font-size:.85rem;z-index:60;box-shadow:var(--shadow)";document.body.appendChild(x);}
  x.textContent=m; x.style.opacity="1"; clearTimeout(toastT); toastT=setTimeout(()=>x.style.opacity="0",1400); }

/* ---------- encode / decode ---------- */
function encodeResult(R){
  const payload={v:1,f:R.form,n:R.meta.name,c:R.meta.cls,i:R.meta.id,
    a:{}}; R.perItem.forEach(p=>{payload.a[p.id]=p.blank?-1:p.sel});
  const json=JSON.stringify(payload);
  return "ENV-"+btoa(unescape(encodeURIComponent(json)));
}
function decodeResult(code){
  try{ const b=code.trim().replace(/^ENV-/,""); const json=decodeURIComponent(escape(atob(b)));
    const p=JSON.parse(json); if(!p.a)return null; return p; }catch(e){ return null; }
}
function downloadCSV(R){
  let rows=[["item","standard","element","selected","correct","result"]];
  R.perItem.forEach(p=>rows.push([p.id,p.std,p.std+p.el,p.blank?"blank":LET[p.sel],LET[p.answer],p.ok?"correct":"incorrect"]));
  let summary=[["","","","","",""],["SUMMARY","standard","score","percent","band",""]];
  STD_ORDER.forEach(s=>{const o=R.byStd[s],pp=Math.round(o.c/o.t*100);summary.push(["",s,o.c+"/"+o.t,pp+"%",bandLabel(pp),""]);});
  summary.push(["","OVERALL",R.correct+"/"+R.total,R.pct+"%",bandLabel(R.pct),""]);
  const csv=rows.concat(summary).map(r=>r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(",")).join("\n");
  const blob=new Blob([csv],{type:"text/csv"}); const a=el("a");
  a.href=URL.createObjectURL(blob);
  a.download=(R.meta.name||"student").replace(/[^a-z0-9]+/gi,"_")+"_"+(R.form==="A"?"pretest":"posttest")+".csv";
  a.click(); URL.revokeObjectURL(a.href);
}

/* ================= ANSWER KEY ================= */
$("#keyBtn").addEventListener("click",renderKey);
function renderKey(){
  const host=$("#answerkey"); host.innerHTML="";
  host.appendChild(el("div","report-head",
    '<div class="eyebrow">Teacher reference</div><h2 style="font-size:1.6rem">Answer key &amp; standards alignment</h2>'+
    '<p class="muted" style="margin:6px 0 0">Both parallel forms. Form&nbsp;A is the pre-test; Form&nbsp;B is the matched post-test.</p>'));
  const brow=el("div","btnrow"); brow.style.margin="14px 0";
  brow.appendChild(mkBtn("Print / Save PDF","btn ghost sm",()=>window.print()));
  brow.appendChild(mkBtn("Home","btn ghost sm",()=>show("home")));
  host.appendChild(brow);
  ["A","B"].forEach(f=>{
    const pan=el("div","panel");
    pan.appendChild(el("h3",null,(f==="A"?"Form A &mdash; Pre-Test":"Form B &mdash; Post-Test")));
    const tw=el("div","tablewrap"); const tb=el("table");
    tb.innerHTML="<thead><tr><th>#</th><th>Std</th><th>Elem</th><th>Key</th><th>Learning target</th></tr></thead>";
    const body=el("tbody");
    DATA.items.filter(i=>i.form===f).forEach((it,idx)=>{
      const tr=el("tr");
      tr.innerHTML="<td class='tnum'>"+(idx+1)+"</td><td>"+it.std+"</td><td>"+it.std+it.el+
        "</td><td class='ok'>"+LET[it.answer]+"</td><td>"+esc(it.target)+"</td>";
      body.appendChild(tr);
    });
    tb.appendChild(body); tw.appendChild(tb); pan.appendChild(tw); host.appendChild(pan);
  });
  show("answerkey");
}

/* ================= CLASS ANALYZER ================= */
$("#analyzeBtn").addEventListener("click",renderAnalyzer);
function renderAnalyzer(){
  const host=$("#analyzer"); host.innerHTML="";
  host.appendChild(el("div","report-head",
    '<div class="eyebrow">Teacher tool</div><h2 style="font-size:1.6rem">Class data analyzer</h2>'+
    '<p class="muted" style="margin:6px 0 0">Paste one result code per line (from your students\' submissions). '+
    'The report groups by standard so you can form instruction groups &mdash; and, on post-test day, see growth.</p>'));
  const pan=el("div","panel");
  pan.innerHTML='<h3>Paste result codes</h3><p class="muted" style="font-size:.85rem;margin:4px 0 8px">'+
    'One per line. Mix pre- and post-test codes freely &mdash; they are grouped by form.</p>';
  const ta=el("textarea"); ta.id="codes"; ta.placeholder="ENV-...\nENV-...\nENV-...";
  pan.appendChild(ta);
  const brow=el("div","btnrow"); brow.style.marginTop="12px";
  brow.appendChild(mkBtn("Build class report","btn sm",runAnalyzer));
  brow.appendChild(mkBtn("Home","btn ghost sm",()=>show("home")));
  pan.appendChild(brow); host.appendChild(pan);
  host.appendChild(el("div",null)).id="analyzerOut";
  show("analyzer");
}
function runAnalyzer(){
  const out=$("#analyzerOut"); out.innerHTML="";
  const lines=$("#codes").value.split(/\n+/).map(s=>s.trim()).filter(Boolean);
  const subs=lines.map(decodeResult).filter(Boolean);
  if(!subs.length){ out.appendChild(el("div","note","No valid result codes found. Codes start with <b>ENV-</b>.")); return; }
  ["A","B"].forEach(form=>{
    const group=subs.filter(s=>s.f===form); if(!group.length)return;
    const scored=group.map(s=>{
      const ans={}; Object.keys(s.a).forEach(k=>{ if(s.a[k]>=0) ans[k]=s.a[k]; });
      return score(form,ans,{name:s.n,cls:s.c,id:s.i});
    });
    out.appendChild(analyzerBlock(form,scored));
  });
}
function analyzerBlock(form,scored){
  const wrap=el("div");
  wrap.appendChild(el("div","report-head",
    '<h2 style="font-size:1.3rem;margin-top:18px">'+(form==="A"?"Pre-Test &middot; Form A":"Post-Test &middot; Form B")+
    ' <span class="muted" style="font-size:.95rem">&middot; '+scored.length+' student'+(scored.length>1?"s":"")+'</span></h2>'));

  // class averages by standard
  const avg={}; STD_ORDER.forEach(s=>{let c=0,t=0;scored.forEach(r=>{c+=r.byStd[s].c;t+=r.byStd[s].t;});avg[s]={c,t,p:Math.round(c/t*100)};});
  const clsPct=Math.round(scored.reduce((a,r)=>a+r.pct,0)/scored.length);
  const p1=el("div","panel");
  p1.appendChild(el("h3",null,"Class average by standard"));
  const sw=el("div"); sw.style.marginTop="6px";
  STD_ORDER.forEach(s=>{const bd=band(avg[s].p);const row=el("div","std-row");
    row.innerHTML='<div class="lab"><div class="code">'+s+'</div><div class="name">'+esc(DATA.standards[s])+'</div></div>'+
      '<div class="meter"><span class="fill '+bd+'" style="width:'+avg[s].p+'%"></span></div>'+
      '<span class="band '+bd+'">'+avg[s].p+'%</span>';
    sw.appendChild(row);});
  p1.appendChild(sw);
  p1.appendChild(el("p","muted","Class overall: <b>"+clsPct+"%</b> &middot; "+bandLabel(clsPct)));
  p1.lastChild.style.marginTop="10px";
  wrap.appendChild(p1);

  // heatmap roster
  const p2=el("div","panel"); p2.appendChild(el("h3",null,"Student &times; standard heatmap"));
  const tw=el("div","tablewrap"); const tb=el("table");
  tb.innerHTML="<thead><tr><th>Student</th><th>Class</th><th class='tnum'>Overall</th>"+
    STD_ORDER.map(s=>"<th class='tnum'>"+s+"</th>").join("")+"</tr></thead>";
  const body=el("tbody");
  scored.sort((a,b)=>a.pct-b.pct).forEach(r=>{
    let cells=STD_ORDER.map(s=>{const pp=Math.round(r.byStd[s].c/r.byStd[s].t*100);
      return "<td class='tnum'><span class='cellband "+band(pp)+"'>"+pp+"</span></td>";}).join("");
    const tr=el("tr");
    tr.innerHTML="<td><b>"+esc(r.meta.name||"—")+"</b></td><td class='muted'>"+esc(r.meta.cls||"")+"</td>"+
      "<td class='tnum'><span class='cellband "+band(r.pct)+"'>"+r.pct+"</span></td>"+cells;
    body.appendChild(tr);
  });
  tb.appendChild(body); tw.appendChild(tb); p2.appendChild(tw);
  p2.appendChild(bandKey()); wrap.appendChild(p2);

  // reteaching groups (beginning band per standard)
  const p3=el("div","panel"); p3.appendChild(el("h3",null,"Suggested reteaching groups"));
  p3.appendChild(el("p","muted","Students scoring in the Beginning band (&lt;50%) for each standard &mdash; ready-made small groups."));
  p3.lastChild.style.margin="4px 0 8px";
  let any=false;
  STD_ORDER.forEach(s=>{
    const names=scored.filter(r=>r.byStd[s].c/r.byStd[s].t<0.5).map(r=>r.meta.name||"—");
    if(names.length){any=true;const row=el("div","miscrow");
      row.innerHTML='<span class="freq">'+s+'</span><span><b>'+esc(DATA.standards[s])+'</b><br><span class="muted">'+names.map(esc).join(", ")+'</span></span>';
      p3.appendChild(row);}
  });
  if(!any)p3.appendChild(el("p","muted","No standard has students in the Beginning band. Consider enrichment/extension."));
  wrap.appendChild(p3);

  // item analysis (hardest items)
  const p4=el("div","panel"); p4.appendChild(el("h3",null,"Item analysis"));
  p4.appendChild(el("p","muted","Percent of students correct per item (p-value). Low values flag class-wide gaps."));
  p4.lastChild.style.margin="4px 0 8px";
  const items=DATA.items.filter(i=>i.form===form);
  const stats=items.map(it=>{let c=0;scored.forEach(r=>{const pi=r.perItem.find(x=>x.id===it.id);if(pi&&pi.ok)c++;});
    return {it,p:Math.round(c/scored.length*100)};});
  stats.sort((a,b)=>a.p-b.p);
  const tw2=el("div","tablewrap"); const tb2=el("table");
  tb2.innerHTML="<thead><tr><th>Item</th><th>Elem</th><th>Target</th><th class='tnum'>% correct</th></tr></thead>";
  const bd2=el("tbody");
  stats.forEach(s=>{const tr=el("tr");
    tr.innerHTML="<td>"+s.it.id+"</td><td>"+s.it.std+s.it.el+"</td><td>"+esc(s.it.target)+
      "</td><td class='tnum'><span class='cellband "+band(s.p)+"'>"+s.p+"%</span></td>";
    bd2.appendChild(tr);});
  tb2.appendChild(bd2); tw2.appendChild(tb2); p4.appendChild(tw2); wrap.appendChild(p4);

  // misconception frequency
  const p5=el("div","panel"); p5.appendChild(el("h3",null,"Most common misconceptions"));
  const freq={};
  scored.forEach(r=>Object.keys(r.misc).forEach(m=>{freq[m]=freq[m]||{n:0,tag:r.misc[m].std+r.misc[m].el};freq[m].n+=r.misc[m].n;}));
  const keys=Object.keys(freq).sort((a,b)=>freq[b].n-freq[a].n);
  if(keys.length){ keys.forEach(m=>{const row=el("div","miscrow");
    row.innerHTML='<span class="freq">'+freq[m].n+'&times;</span><span><span class="muted" style="font-weight:700">'+freq[m].tag+'</span> &mdash; '+esc(m)+'</span>';
    p5.appendChild(row);}); }
  else p5.appendChild(el("p","muted","No keyed misconceptions triggered across this group."));
  wrap.appendChild(p5);
  return wrap;
}

/* boot */
show("home");
</script>
"""

INNER = STYLE + BODY + SCRIPT.replace("/*DATA*/", JS_DATA)

# ------------------------------------------------------------------ standalone doc
STANDALONE = (
    "<!doctype html>\n<html lang=\"en\">\n<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "<title>Environmental Science Semester Diagnostic (SEV1–SEV5)</title>\n"
    "<meta name=\"description\" content=\"Grade 9 Georgia Environmental Science pre/post diagnostic — 40 aligned "
    "multiple-choice items with instant per-standard reporting and a class data analyzer.\">\n"
    + STYLE + "\n</head>\n<body>\n" + BODY + SCRIPT.replace("/*DATA*/", JS_DATA) + "\n</body>\n</html>\n"
)
with open(os.path.join(ROOT, "assessment.html"), "w", encoding="utf-8") as f:
    f.write(STANDALONE)

# index.html is identical to assessment.html so that a GitHub Pages / static-host
# site root (…/) opens the test directly instead of showing the README.
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(STANDALONE)

# Ensure static hosting serves files as-is (no Jekyll processing).
open(os.path.join(ROOT, ".nojekyll"), "w").close()

with open(os.path.join(ROOT, "build", "artifact_body.html"), "w", encoding="utf-8") as f:
    f.write("<title>Environmental Science Semester Diagnostic</title>\n" + INNER)

print("wrote assessment.html (%d KB) and build/artifact_body.html" % (len(STANDALONE)//1024))

# ------------------------------------------------------------------ TEACHER GUIDE
def form_items(f): return [i for i in ITEMS if i["form"] == f]

def md_escape(s): return s.replace("|", "\\|")

tg = []
tg.append("# Environmental Science Semester Diagnostic — Teacher Guide\n")
tg.append("**Course:** Environmental Science (GA 26.06110) · **Grade:** 9 · "
          "**Standards:** SEV1–SEV5 · **Format:** 40 multiple-choice items, online, auto-scored\n")
tg.append("This package contains **two parallel forms**. Give **Form A** as a **pre-test in Week 1** to "
          "diagnose starting points and plan the 18-week semester; give **Form B** as the matched "
          "**post-test at the end** to measure growth against the same targets.\n")

tg.append("## How to run it online\n")
tg.append("1. Open **`assessment.html`** in any browser, or upload it to Google Sites, your LMS "
          "(Canvas/Schoology/Google Classroom as an embedded page or hosted file), or any static host. "
          "It is fully self-contained — no internet, accounts, or plugins required.\n"
          "2. Students enter their name/class, pick the assigned form, and answer. Scoring is instant.\n"
          "3. Each student receives a **result code** (`ENV-…`). Collect the codes however you already collect "
          "work (paste into the assignment, a Google Form, or a shared doc).\n"
          "4. Open **Teacher tools → Class data analyzer**, paste the codes, and get a class heatmap, "
          "reteaching groups, item analysis, and misconception frequencies.\n")

tg.append("## Why this gives you *robust, individualized* data\n")
tg.append("- **Every item is tagged** to a standard **and** element (e.g., `SEV1b`), so subscores are meaningful, "
          "not just a single number.\n"
          "- **Distractors are diagnostic.** Most wrong answers are keyed to a specific *documented* student "
          "misconception from the GaDOE Teacher Notes (the “potential initial student ideas”). When a student "
          "picks that option, the report names the misconception — telling you *what* to reteach.\n"
          "- **Two items per element per form** give a stable read at the element level and let you compare "
          "pre → post on identical targets.\n")

tg.append("## Mastery bands\n")
tg.append("| Band | Score | Instructional move |\n|---|---|---|\n"
          "| **Secure** | ≥ 80% | Enrich / extend; use as peer experts |\n"
          "| **Developing** | 50–79% | Targeted practice on missed elements |\n"
          "| **Beginning** | < 50% | Small-group reteach (analyzer builds the groups) |\n")

# blueprint table
tg.append("## Test blueprint\n")
seg_of = {}
for seg, keys in SEGMENTS.items():
    for k in keys: seg_of[k] = seg
tg.append("| Standard | Element | Items/form | Curriculum-map segment |\n|---|---|---|---|")
cnt = defaultdict(int)
for it in form_items("A"): cnt[it["std"]+it["el"]] += 1
for k in ELEMENTS:
    tg.append("| %s | %s | %d | %s |" % (k[:4], md_escape(ELEMENTS[k]), cnt[k], seg_of.get(k, "—")))
tg.append("")
per_std = defaultdict(int)
for it in form_items("A"): per_std[it["std"]] += 1
tg.append("**Per standard (each form):** " + " · ".join("%s = %d" % (s, per_std[s]) for s in STANDARDS) +
          " · **Total = %d items**\n" % FORM_LEN)

# answer key + misconception map
for f, title in [("A", "Form A — Pre-Test"), ("B", "Form B — Post-Test")]:
    tg.append("## Answer key & item map — %s\n" % title)
    tg.append("| # | Item ID | Std·Elem | Key | Learning target |\n|---|---|---|---|---|")
    for idx, it in enumerate(form_items(f), 1):
        tg.append("| %d | %s | %s | **%s** | %s |" %
                  (idx, it["id"], it["std"]+it["el"], LETTERS[it["answer"]], md_escape(it["target"])))
    tg.append("")

tg.append("## Misconception map (diagnostic distractors)\n")
tg.append("If a student selects the listed option, they likely hold the stated misconception. "
          "These mirror the GaDOE Teacher-Notes “potential initial student ideas.”\n")
tg.append("| Item | If they choose | It suggests they think… |\n|---|---|---|")
for it in ITEMS:
    for oi, note in it["diagnoses"].items():
        tg.append("| %s | %s. %s | %s |" %
                  (it["id"], LETTERS[oi], md_escape(it["options"][oi][:48] + ("…" if len(it["options"][oi]) > 48 else "")),
                   md_escape(note)))
tg.append("")

tg.append("## Turning pre-test data into a semester plan\n")
tg.append("- **Sequence to your gaps.** The class heatmap shows which standards start lowest — front-load "
          "reteaching time there. The curriculum map’s four segments (Planet Earth → Rhythms → Humans → "
          "Sustaining) are your natural pacing spine for the 18 weeks.\n"
          "- **Form groups on day one.** The analyzer lists every student in the Beginning band per standard — "
          "those are your first small groups and your differentiation targets.\n"
          "- **Pre-teach vocabulary where misconceptions cluster.** A high-frequency misconception (e.g., "
          "“energy lost between trophic levels is destroyed”) tells you exactly which model to confront early.\n"
          "- **At semester end,** give Form B and compare the same element subscores. Growth per standard — "
          "and the shrinking misconception counts — is your evidence of learning.\n")

with open(os.path.join(ROOT, "TEACHER_GUIDE.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(tg))
print("wrote TEACHER_GUIDE.md")

# ------------------------------------------------------------------ ITEM BANK (printable)
ib = []
ib.append("# Environmental Science Semester Diagnostic — Item Bank\n")
ib.append("Grade 9 · GA 26.06110 · SEV1–SEV5. Form A = Pre-Test, Form B = Post-Test (parallel). "
          "Correct answers are marked with **✓** — remove them before printing a student copy.\n")
for f, title in [("A", "FORM A — PRE-TEST"), ("B", "FORM B — POST-TEST")]:
    ib.append("\n---\n\n## %s\n" % title)
    cur_std = None
    for idx, it in enumerate(form_items(f), 1):
        if it["std"] != cur_std:
            cur_std = it["std"]
            ib.append("\n### %s — %s\n" % (cur_std, STANDARDS[cur_std]))
        ib.append("**%d. %s**  \n_(%s · %s)_\n" % (idx, it["stem"], it["std"]+it["el"], it["target"]))
        for oi, op in enumerate(it["options"]):
            mark = " ✓" if oi == it["answer"] else ""
            ib.append("- %s. %s%s" % (LETTERS[oi], op, mark))
        ib.append("")
with open(os.path.join(ROOT, "ITEM_BANK.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(ib))
print("wrote ITEM_BANK.md")
print("done.")
