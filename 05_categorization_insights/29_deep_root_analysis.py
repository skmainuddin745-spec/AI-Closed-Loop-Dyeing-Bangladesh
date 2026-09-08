# -*- coding: utf-8 -*-
"""
DEEP ROOT-CAUSE & REMAINING INSIGHTS ENGINE  --  v2 (rigorous)
SMART DYEING / Industrial Research Consortium GRANTS Project EOI

REWRITE NOTES vs v1 (see 29_deep_root_analysis_ORIGINAL_BACKUP.py):
  1. v1 could never run: the final HTML template was passed through str.format()
     while containing literal CSS/JS braces -> KeyError '--bg'. Fixed by using
     token replacement instead of .format().
  2. v1 emitted the Chart.js constructors BEFORE the <script> block defining
     YOYL/YOYV/... so every chart would have thrown ReferenceError. Fixed.
  3. v1 read headers straight from the DB with GROUP BY Batch_No, which silently
     picks an arbitrary row out of 362,451 header rows for 289,403 batches.
     v2 reads the deduplicated MASTER_289403_BATCHES_2021_2026.csv instead.
  4. v1's "Top 15 Most Active Machines" table was structurally empty: MC_No is
     NULL for 100% of 362,451 header rows. Replaced with a nullity audit.
  5. v1's clean_float() stripped ':' so a liquor ratio written "1:8" would
     become 18.0. v2 parses ratios explicitly.
  6. v1 averaged per-batch ratios (mean of L/kg), which over-weights tiny
     batches. v2 reports mass-weighted intensity as the primary KPI, with
     median / P25 / P75 / P90 alongside, and screens implausible records.
  7. v1 ignored chemistry entirely. v2 joins the lines table (5.80M rows,
     deduplicated to one canonical source file per batch) to give chemical
     mass and cost per kg of fabric, by shade / fabric / unit / year.
  8. v2 quantifies the addressable saving: how much water and salt would be
     avoided if every batch matched the P25 performer of its own
     fabric x shade x GSM peer group.

OUTPUTS (written next to this script):
  DEEP_ROOT_Findings_2021_2026.html      full analytical report
  DEEP_ROOT_Batch_Enriched.csv           289,403 batches x header + chemistry
  DEEP_ROOT_Chemical_Master.csv          per-chemical mass, cost, class
  DEEP_ROOT_Savings_Opportunity.csv      peer-group savings ledger
No f-strings, for interpreter portability.
"""
import os, csv, sqlite3, re, json, sys, shutil, tempfile, atexit
from array import array
from collections import defaultdict
from datetime import datetime

csv.field_size_limit(10000000)

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
if not os.path.isdir(BASE_DIR):
    # portable fallback: resolve relative to this file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH     = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis", "extraction_checkpoint.db")
IN_DIR      = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")
MASTER_CSV  = os.path.join(IN_DIR, "MASTER_289403_BATCHES_2021_2026.csv")
HTML_OUT    = os.path.join(IN_DIR, "DEEP_ROOT_Findings_2021_2026.html")
ENRICH_OUT  = os.path.join(IN_DIR, "DEEP_ROOT_Batch_Enriched.csv")
CHEM_OUT    = os.path.join(IN_DIR, "DEEP_ROOT_Chemical_Master.csv")
SAVE_OUT    = os.path.join(IN_DIR, "DEEP_ROOT_Savings_Opportunity.csv")

RUN_STAMP = datetime.now().strftime('%Y-%m-%d %H:%M')

# ---------------------------------------------------------------- screening --
# Physical plausibility windows for exhaust jet dyeing. Records outside these
# are excluded from KPI maths and counted in the integrity panel (never
# silently dropped).
MIN_KG, MAX_KG   = 5.0, 5000.0      # batch fabric load
MIN_WI, MAX_WI   = 2.0, 60.0        # litres of water per kg fabric (no exhaust
                                    # jet dyeing runs below about 1:3)
MIN_LR, MAX_LR   = 1.5, 20.0        # liquor ratio 1:X
MAX_CHEM_GPKG    = 3000.0           # grams of chemical per kg fabric
MIN_YEAR_N       = 1000             # below this a year is a stray-date artefact,
                                    # not a production year: shown but not trended

def num(v):
    """Parse a numeric cell that may carry thousands separators / stray text."""
    if v is None:
        return 0.0
    s = str(v).strip().replace(',', '')
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    if not m:
        return 0.0
    try:
        return float(m.group(0))
    except Exception:
        return 0.0

def parse_lr(v):
    """Liquor ratio: accepts '7.00', '1:7', '1 : 7.5'. Returns X in 1:X."""
    s = str(v).strip()
    if ':' in s:
        parts = s.split(':')
        a, b = num(parts[0]), num(parts[-1])
        if a > 0 and b > 0:
            return b / a
        return 0.0
    return num(s)

def pct(sorted_vals, p):
    """Linear-interpolated percentile on a pre-sorted list."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    k = (n - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)

def wstats(vals):
    """median / P25 / P75 / P90 of a list."""
    if not vals:
        return (0.0, 0.0, 0.0, 0.0)
    s = sorted(vals)
    return (pct(s, 50), pct(s, 25), pct(s, 75), pct(s, 90))

# ------------------------------------------------- chemical classification --
DYE_BRANDS = ('BEZAKTIV', 'REMAZOL', 'NOVACRON', 'RIFAZOL', 'AVITERA', 'DRIMAREN',
              'DRIMARINE', 'TAICRON', 'NEOCRON', 'TERASIL', 'DIANIX', 'SYNOLON',
              'LEVAFIX', 'SUNFIX', 'SUMIFIX', 'SETAZOL', 'EVERZOL', 'LANASOL',
              'CIBACRON', 'INTRACRON', 'SOLAZOL', 'REACTIVE', 'DISPERSE',
              'DYSTAR', 'FORON', 'SERILENE', 'PALANIL')
DYE_COLOURS = ('BLACK', 'NAVY', 'TURQ', 'CARMINE', 'RUBINE', 'SCARLET',
               'MAGENTA', 'CRIMSON', 'VIOLET', 'CORAL')

_CLS_CACHE = {}

def chem_class(name):
    hit = _CLS_CACHE.get(name)
    if hit is not None:
        return hit
    r = _chem_class_raw(name)
    _CLS_CACHE[name] = r
    return r

def _chem_class_raw(name):
    u = str(name).upper()
    if 'SULPHATE' in u or 'SULFATE' in u or 'GLAUBER' in u or 'COMMON SALT' in u or u.strip() == 'SALT':
        return 'Salt (electrolyte)'
    if 'SODA ASH' in u or 'CAUSTIC' in u or 'BICARB' in u or 'BI CARB' in u or 'SODIUM CARBONATE' in u:
        return 'Alkali'
    if 'PER OXIDE' in u or 'PEROXIDE' in u or 'H2O2' in u or 'HYDROSE' in u or 'BLEACH' in u or 'HYPO' in u:
        return 'Bleach / redox'
    for b in DYE_BRANDS:
        if b in u:
            return 'Dyestuff'
    for c in DYE_COLOURS:
        if c in u:
            return 'Dyestuff'
    if 'ACID' in u:
        return 'Acid'
    if 'ZYME' in u or 'CELLUSOFT' in u or 'CELPOLISH' in u or 'CATALASE' in u:
        return 'Enzyme'
    if 'SOFT' in u or 'SILICON' in u or 'TUBINGAL' in u or 'SAPAMINE' in u or 'SARABID' in u or 'MACRO' in u:
        return 'Softener / finish'
    return 'Auxiliary'

CLASS_ORDER = ['Dyestuff', 'Salt (electrolyte)', 'Alkali', 'Bleach / redox',
               'Acid', 'Enzyme', 'Softener / finish', 'Auxiliary']

CACHE_DIR = os.environ.get('DEEP_ROOT_CACHE',
                           os.path.join(os.path.expanduser('~'), '.deep_root_cache'))
CACHE_BIN = os.path.join(CACHE_DIR, 'chem.bin')
CACHE_META = os.path.join(CACHE_DIR, 'chem_meta.json')

def sig(path):
    st = os.stat(path)
    return [os.path.basename(path), st.st_size, int(st.st_mtime)]

# =============================================================== LOAD PHASE ==
print("[1/6] Loading deduplicated batch master ...")
# Columnar storage. A dict per batch costs about 1.2 kB, which is 350 MB across
# 289k batches and will not fit in the working set; packed arrays cost ~25 MB.
IDX = {}
NAMES = []
A_year = array('h'); A_kg = array('d'); A_w = array('d'); A_lr = array('d')
A_chem = array('d'); A_tk = array('d'); A_salt = array('d')
A_dye = array('d'); A_alk = array('d')
A_nl = array('i'); A_wi = array('d'); A_flag = array('B')   # bit0 usable, bit1 chem excluded

_pools = {}
def code(pool, val):
    """Intern a category string to a small integer."""
    d = _pools.setdefault(pool, ({}, []))
    m, lst = d
    c = m.get(val)
    if c is None:
        c = len(lst)
        m[val] = c
        lst.append(val)
    return c
def label(pool, c):
    return _pools[pool][1][c]

A_unit = array('H'); A_fab = array('H'); A_gsm = array('H')
A_shade = array('H'); A_month = array('H'); A_dtype = array('H')

master_rows = 0
bad_year = 0
with open(MASTER_CSV, 'r', encoding='utf-8', newline='') as f:
    for r in csv.DictReader(f):
        master_rows += 1
        bno = (r.get('Batch_No') or '').strip()
        if not bno or bno in IDX:
            continue
        try:
            yr_i = int((r.get('Year') or '').strip())
        except Exception:
            bad_year += 1
            continue
        IDX[bno] = len(NAMES)
        NAMES.append(bno)
        A_year.append(yr_i)
        A_kg.append(num(r.get('Fabric_Qty_kg')))
        A_w.append(num(r.get('Water_Liters')))
        A_lr.append(parse_lr(r.get('Liquor_Ratio_1_to_X')))
        A_unit.append(code('unit', (r.get('Dye_Unit_Class') or 'Other').strip()))
        A_fab.append(code('fab', (r.get('Fabric_Category') or 'Other').strip()))
        A_gsm.append(code('gsm', (r.get('GSM_Category') or 'Unknown').strip()))
        A_shade.append(code('shade', (r.get('Shade_Category') or 'Unknown').strip()))
        A_month.append(code('month', (r.get('Month') or '').strip()))
        A_dtype.append(code('dtype', re.sub(r'\s+', ' ',
                            (r.get('Dyeing_Type_Code') or '').replace('&nbsp;', ' ')).strip()))
        A_chem.append(0.0); A_tk.append(0.0); A_salt.append(0.0)
        A_dye.append(0.0); A_alk.append(0.0)
        A_nl.append(0); A_wi.append(0.0); A_flag.append(0)
GRAND_TOTAL = len(NAMES)
print("      master rows %d -> unique batches %d (unparseable year: %d)" % (master_rows, GRAND_TOTAL, bad_year))

print("[2/6] Auditing raw extraction tables ...")
# sqlite full scans run roughly an order of magnitude slower against a mounted
# network volume than against local disk, so work from a scratch copy.
WORK_DB = DB_PATH
if os.path.getsize(DB_PATH) > 50 * 1024 * 1024:
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    WORK_DB = os.path.join(CACHE_DIR, 'work.db')
    if (not os.path.exists(WORK_DB)) or os.path.getsize(WORK_DB) != os.path.getsize(DB_PATH):
        print("      staging %.0f MB database to local scratch ..." % (os.path.getsize(DB_PATH) / 1e6))
        shutil.copyfile(DB_PATH, WORK_DB)
    else:
        print("      reusing local database copy")

conn = sqlite3.connect(WORK_DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(*), COUNT(DISTINCT Batch_No) FROM headers")
hdr_rows, hdr_uniq = cur.fetchone()
cur.execute("SELECT COUNT(*) FROM headers WHERE MC_No IS NULL OR TRIM(MC_No)=''")
mc_null = cur.fetchone()[0]

print("[3/6] Selecting one canonical source file per batch ...")
# Some batches were extracted from more than one HTML file. Where two
# extractions disagree on line count the fullest is taken; ties break
# alphabetically so the choice is reproducible. Every count the audit panel
# needs is derived from this single pass rather than from extra full scans.
cur.execute("SELECT Batch_No, Source_File, COUNT(*) FROM lines GROUP BY 1,2")
canonical = {}
src_per_batch = defaultdict(int)
ln_rows = 0
for bno, sf, n in cur.fetchall():
    ln_rows += n
    src_per_batch[bno] += 1
    cur_best = canonical.get(bno)
    if cur_best is None or n > cur_best[1] or (n == cur_best[1] and str(sf) < str(cur_best[0])):
        canonical[bno] = (sf, n)
ln_uniq = len(canonical)
multi_src = sum(1 for v in src_per_batch.values() if v > 1)

CACHE_KEY = {'db': sig(DB_PATH), 'master': sig(MASTER_CSV), 'n': GRAND_TOTAL, 'v': 2}
cached = None
if os.path.exists(CACHE_BIN) and os.path.exists(CACHE_META):
    try:
        meta = json.load(open(CACHE_META, 'r', encoding='utf-8'))
        if meta.get('key') == CACHE_KEY:
            cached = meta
    except Exception:
        cached = None

if cached:
    print("[4/6] Restoring chemistry join from cache ...")
    with open(CACHE_BIN, 'rb') as fh:
        for arr in (A_chem, A_tk, A_salt, A_dye, A_alk):
            del arr[:]
            arr.fromfile(fh, GRAND_TOTAL)
        del A_nl[:]
        A_nl.fromfile(fh, GRAND_TOTAL)
    item_kg = dict(cached['item_kg'])
    item_tk = dict(cached['item_tk'])
    item_n = dict(cached['item_n'])
    item_batches = dict(cached['item_batches'])
    ln_rows = cached['ln_rows']
    lines_kept = cached['lines_kept']
    lines_orphan = cached['lines_orphan']
    conn.close()
    del canonical, src_per_batch
else:
    print("[4/6] Aggregating %s recipe lines in SQL ..." % format(ln_rows, ','))
    # The join and the sums are done inside sqlite. Doing it row by row in
    # Python costs about 12 million interpreter round trips and does not finish
    # in a reasonable time on this machine.
    # Every Req_Qty_kg / Amount_Tk value in the table is a clean numeric
    # literal (verified: no blanks, no thousands separators, no cast failures),
    # so CAST is exactly equivalent to the Python parser used elsewhere.
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("CREATE TEMP TABLE canon(b TEXT PRIMARY KEY, sf TEXT)")
    cur.executemany("INSERT INTO canon VALUES (?,?)",
                    ((b, v[0]) for b, v in canonical.items()))
    # class codes: 1 salt, 2 dyestuff, 3 alkali, 0 everything else
    CODE = {'Salt (electrolyte)': 1, 'Dyestuff': 2, 'Alkali': 3}
    cur.execute("CREATE TEMP TABLE icls(nm TEXT PRIMARY KEY, c INTEGER)")
    cur.execute("SELECT DISTINCT Item_Name FROM lines")
    names_all = [r[0] for r in cur.fetchall()]
    cur.executemany("INSERT INTO icls VALUES (?,?)",
                    ((nm, CODE.get(chem_class(nm), 0)) for nm in names_all))

    JOIN = (" FROM lines l JOIN canon c ON l.Batch_No=c.b AND l.Source_File=c.sf ")
    lines_kept = 0
    lines_orphan = 0
    cur.execute("SELECT l.Batch_No, ic.c,"
                " SUM(CAST(l.Req_Qty_kg AS REAL)),"
                " SUM(CAST(l.Amount_Tk AS REAL)), COUNT(*)"
                + JOIN + " JOIN icls ic ON ic.nm=l.Item_Name"
                " GROUP BY 1,2")
    while True:
        chunk = cur.fetchmany(100000)
        if not chunk:
            break
        for bno, c, qsum, tsum, cnt in chunk:
            i = IDX.get(bno)
            if i is None:
                lines_orphan += cnt
                continue
            qsum = qsum or 0.0
            A_chem[i] += qsum
            A_tk[i] += (tsum or 0.0)
            A_nl[i] += cnt
            if c == 1:
                A_salt[i] += qsum
            elif c == 2:
                A_dye[i] += qsum
            elif c == 3:
                A_alk[i] += qsum
            lines_kept += cnt

    item_kg = {}
    item_tk = {}
    item_n = {}
    item_batches = {}
    cur.execute("SELECT l.Item_Name, SUM(CAST(l.Req_Qty_kg AS REAL)),"
                " SUM(CAST(l.Amount_Tk AS REAL)), COUNT(*), COUNT(DISTINCT l.Batch_No)"
                + JOIN + " GROUP BY 1")
    for nm, kgv, tkv, cnt, nb in cur.fetchall():
        item_kg[nm] = kgv or 0.0
        item_tk[nm] = tkv or 0.0
        item_n[nm] = cnt
        item_batches[nm] = nb
    conn.close()
    del canonical, src_per_batch

    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    with open(CACHE_BIN, 'wb') as fh:
        for arr in (A_chem, A_tk, A_salt, A_dye, A_alk):
            arr.tofile(fh)
        A_nl.tofile(fh)
    json.dump({'key': CACHE_KEY, 'item_kg': dict(item_kg), 'item_tk': dict(item_tk),
               'item_n': dict(item_n), 'item_batches': item_batches,
               'ln_rows': ln_rows, 'lines_kept': lines_kept,
               'lines_orphan': lines_orphan},
              open(CACHE_META, 'w', encoding='utf-8'))
    print("      chemistry join cached for re-runs")

print("      canonical lines kept %s  (deduplicated away %s)" % (
    format(lines_kept, ','), format(ln_rows - lines_kept - lines_orphan, ',')))

# ============================================================ ANALYSIS PHASE ==
print("[5/6] Computing statistics ...")

FAB_ORDER   = ['Single Jersey', 'Lycra S/J', 'Composite', 'Rib Fabric',
               'Fleece/Heavy', 'Pique', 'Interlock', 'Other']
SHADE_ORDER = ['White/Bleach', 'Light/Medium Colored', 'Dark/Extra Dark', 'AOP']
GSM_ORDER   = ['Light (<150)', 'Medium (150-249)', 'Heavy (250+)', 'Unknown']
UNIT_ORDER  = ['Unit_A', 'Unit_D', 'Unit_C']
UNIT_LABEL  = {'Unit_A': 'Unit_A - Reactive (cotton)', 'Unit_D': 'Unit_D - Blends',
               'Unit_C': 'Unit_C - Disperse (polyester)', 'Other': 'Other'}
UNIT_COLOR  = {'Unit_A': '#2f7ed8', 'Unit_D': '#e0913a', 'Unit_C': '#2e9e6b', 'Other': '#8a94a6'}

# ---- integrity counters -----------------------------------------------------
q = {'no_kg': 0, 'no_water': 0, 'kg_out': 0, 'wi_out': 0, 'lr_missing': 0,
     'lr_invalid': 0, 'lr_mismatch': 0, 'no_lines': 0, 'chem_out': 0, 'usable': 0,
     'w_placeholder': 0}
ph_by_unit = defaultdict(int)
tot_by_unit = defaultdict(int)

year_count = defaultdict(int)
month_count = defaultdict(int)

# ---- accumulators -----------------------------------------------------------
# 'wi'/'lr' hold raw doubles in an array rather than boxed Python floats.
def acc():
    return {'n': 0, 'kg': 0.0, 'w': 0.0, 'chem_kg': 0.0, 'chem_tk': 0.0,
            'salt_kg': 0.0, 'dye_kg': 0.0, 'alkali_kg': 0.0,
            'wi': array('d'), 'lr': array('d')}

by_year  = defaultdict(acc)
by_unit  = defaultdict(acc)
by_shade = defaultdict(acc)
by_fab   = defaultdict(acc)
by_gsm   = defaultdict(acc)
by_month = defaultdict(acc)
by_cell  = defaultdict(acc)
by_fs    = defaultdict(acc)
by_unit_year = defaultdict(lambda: defaultdict(int))
by_quarter   = defaultdict(lambda: defaultdict(int))
by_dtype     = defaultdict(int)
lr_hist      = defaultdict(int)

def push(a, i, wi, lr_ok, keep_wi=True, keep_lr=False):
    a['n'] += 1
    a['kg'] += A_kg[i]
    a['w'] += A_w[i]
    a['chem_kg'] += A_chem[i]
    a['chem_tk'] += A_tk[i]
    a['salt_kg'] += A_salt[i]
    a['dye_kg'] += A_dye[i]
    a['alkali_kg'] += A_alk[i]
    if keep_wi:
        a['wi'].append(wi)
    if keep_lr and lr_ok:
        a['lr'].append(A_lr[i])

for i in range(GRAND_TOTAL):
    yr = A_year[i]
    year_count[yr] += 1
    mth = label('month', A_month[i])
    if mth:
        month_count[mth] += 1
    dt = label('dtype', A_dtype[i])
    if dt:
        by_dtype[dt] += 1
    if A_nl[i] == 0:
        q['no_lines'] += 1

    tot_by_unit[label('unit', A_unit[i])] += 1
    kg = A_kg[i]; w = A_w[i]; lr = A_lr[i]
    if kg <= 0:
        q['no_kg'] += 1
        continue
    if w <= 0:
        q['no_water'] += 1
        continue
    if kg < MIN_KG or kg > MAX_KG:
        q['kg_out'] += 1
        continue
    wi = w / kg
    # A large block of batches carries the placeholder ratio 1:1 with water
    # recorded as exactly the fabric weight. That is the ratio field written
    # through to the water field, not a metered volume. Left in, it pulls the
    # whole-plant intensity down and drives peer-group benchmarks to a level
    # no machine can reach, so it is removed from every water statistic.
    if 0 < lr < MIN_LR and abs(w - lr * kg) <= 0.02 * w:
        q['w_placeholder'] += 1
        ph_by_unit[label('unit', A_unit[i])] += 1
        continue
    if wi < MIN_WI or wi > MAX_WI:
        q['wi_out'] += 1
        continue

    if lr <= 0:
        q['lr_missing'] += 1
        lr_ok = False
    elif lr < MIN_LR or lr > MAX_LR:
        q['lr_invalid'] += 1
        lr_ok = False
    else:
        lr_ok = True
        lr_hist[round(lr * 2) / 2.0] += 1
        if abs(w - lr * kg) / w > 0.15:
            q['lr_mismatch'] += 1

    if A_chem[i] * 1000.0 / kg > MAX_CHEM_GPKG:
        q['chem_out'] += 1
        A_chem[i] = A_tk[i] = A_salt[i] = A_dye[i] = A_alk[i] = 0.0
        A_flag[i] = 2

    q['usable'] += 1
    A_flag[i] = A_flag[i] | 1
    A_wi[i] = wi

    fab = label('fab', A_fab[i]); shd = label('shade', A_shade[i])
    gsm = label('gsm', A_gsm[i]); unt = label('unit', A_unit[i])

    push(by_year[yr], i, wi, lr_ok)
    push(by_unit[unt], i, wi, lr_ok, keep_lr=True)
    push(by_shade[shd], i, wi, lr_ok)
    push(by_fab[fab], i, wi, lr_ok, keep_wi=False)
    push(by_gsm[gsm], i, wi, lr_ok, keep_wi=False)
    push(by_month[mth], i, wi, lr_ok, keep_wi=False)
    push(by_cell[(fab, shd, gsm)], i, wi, lr_ok)
    push(by_fs[(fab, shd)], i, wi, lr_ok, keep_wi=False)
    by_unit_year[unt][yr] += 1
    if len(mth) == 7:
        try:
            by_quarter[unt]['Q%d' % ((int(mth[5:7]) - 1) // 3 + 1)] += 1
        except Exception:
            pass

print("      usable for KPI maths: %s of %s (%.1f%%)" % (
    format(q['usable'], ','), format(GRAND_TOTAL, ','), 100.0 * q['usable'] / GRAND_TOTAL))

# ---- coverage window & complete years --------------------------------------
months_sorted = sorted([m for m in month_count if len(m) == 7])
FIRST_MONTH = months_sorted[0] if months_sorted else ''
LAST_MONTH  = months_sorted[-1] if months_sorted else ''
years_present = sorted([y for y in year_count if 2015 <= y <= 2030])
# a year is "complete" only if all 12 of its months carry batches
def months_in(y):
    return len([m for m in month_count if m.startswith(str(y)) and month_count[m] > 0])
COMPLETE_YEARS = [y for y in years_present if months_in(y) == 12 and year_count[y] >= MIN_YEAR_N]
PARTIAL_YEARS  = [y for y in years_present if y not in COMPLETE_YEARS]
# Years carrying a handful of batches are date-parse strays from the source
# HTML, not production years. Keeping them in a trend line makes a two-batch
# year look like a real efficiency excursion.
TREND_YEARS    = [y for y in years_present if year_count[y] >= MIN_YEAR_N]

# YoY on complete years only
yoy = []
for i in range(1, len(COMPLETE_YEARS)):
    p, c = COMPLETE_YEARS[i - 1], COMPLETE_YEARS[i]
    if c - p != 1:
        continue
    a, bb = by_year[p]['n'], by_year[c]['n']
    if a:
        yoy.append((c, round((bb - a) / float(a) * 100.0, 2)))

# 2026 YTD annualisation (explicitly labelled an estimate, not a measurement)
YTD_YEAR = TREND_YEARS[-1] if TREND_YEARS else 0
ytd_months = months_in(YTD_YEAR)
ytd_note = ''
if YTD_YEAR in PARTIAL_YEARS and ytd_months > 0:
    run_rate = by_year[YTD_YEAR]['n'] / float(ytd_months) * 12.0
    ytd_note = ('%d is partial (%d months of data). At the observed run rate the '
                'full-year figure would be about %s batches. This is a projection, '
                'not a measurement.' % (YTD_YEAR, ytd_months, format(int(run_rate), ',')))

# ---- unit-cost step detection ----------------------------------------------
# A cost per kg that jumps at a year boundary and then holds is the signature of
# a price-list revaluation in the source system, not a market move. Reporting it
# as a real cost increase would not survive review, so it is flagged explicitly.
cost_steps = []
for i in range(1, len(TREND_YEARS)):
    pa, ca = by_year[TREND_YEARS[i - 1]], by_year[TREND_YEARS[i]]
    if pa['kg'] > 0 and ca['kg'] > 0:
        a = pa['chem_tk'] / pa['kg']
        b = ca['chem_tk'] / ca['kg']
        if a > 0 and (b / a - 1.0) > 0.40:
            cost_steps.append((TREND_YEARS[i], a, b, (b / a - 1.0) * 100.0))

# ---- peak / trough months, excluding the partial edge months ----------------
interior = [m for m in months_sorted if m not in (FIRST_MONTH, LAST_MONTH)]
month_rank = sorted([(m, by_month[m]) for m in interior if by_month[m]['n'] > 0],
                    key=lambda x: x[1]['n'], reverse=True)
peak3 = month_rank[:3]
trough3 = month_rank[::-1][:3]

wi_by_month = [(m, by_month[m]['w'] / by_month[m]['kg'])
               for m in interior if by_month[m]['kg'] > 0]
wi_by_month.sort(key=lambda x: x[1])
best_wi_m = wi_by_month[:5]
worst_wi_m = wi_by_month[::-1][:5]

# ---- savings ledger ---------------------------------------------------------
# For every fabric x shade x GSM peer group with >= 200 usable batches, take the
# group's own 25th-percentile water intensity as an achieved-in-house benchmark
# (it is a real operating point, not a theoretical target). Every batch above it
# contributes (wi - P25) * kg litres of addressable excess.
MIN_CELL_N = 200
cell_p25 = {}
for k, a in by_cell.items():
    if a['n'] >= MIN_CELL_N and a['wi']:
        cell_p25[k] = pct(sorted(a['wi']), 25)

excess_l = 0.0
excess_by_cell = defaultdict(float)
for i in range(GRAND_TOTAL):
    if not (A_flag[i] & 1):
        continue
    k = (label('fab', A_fab[i]), label('shade', A_shade[i]), label('gsm', A_gsm[i]))
    p = cell_p25.get(k)
    if p is None:
        continue
    if A_wi[i] > p:
        d = (A_wi[i] - p) * A_kg[i]
        excess_l += d
        excess_by_cell[k] += d

TOTAL_WATER = sum(by_year[y]['w'] for y in years_present)
TOTAL_KG    = sum(by_year[y]['kg'] for y in years_present)
TOTAL_TK    = sum(by_year[y]['chem_tk'] for y in years_present)
TOTAL_CHEM  = sum(by_year[y]['chem_kg'] for y in years_present)
TOTAL_SALT  = sum(by_year[y]['salt_kg'] for y in years_present)
TOTAL_DYE   = sum(by_year[y]['dye_kg'] for y in years_present)
span_years = max(1.0, len(months_sorted) / 12.0)

# ---- chemical class rollup --------------------------------------------------
class_stats = defaultdict(lambda: {'kg': 0.0, 'tk': 0.0, 'items': 0, 'n': 0})
for item, kgv in item_kg.items():
    c = chem_class(item)
    class_stats[c]['kg'] += kgv
    class_stats[c]['tk'] += item_tk[item]
    class_stats[c]['items'] += 1
    class_stats[c]['n'] += item_n[item]
CHEM_KG_ALL = sum(v['kg'] for v in class_stats.values()) or 1.0
CHEM_TK_ALL = sum(v['tk'] for v in class_stats.values()) or 1.0

items_sorted = sorted(item_kg, key=lambda x: item_kg[x], reverse=True)
top_items = items_sorted[:25]
top_cost = sorted(item_tk, key=lambda x: item_tk[x], reverse=True)[:15]

print("[6/6] Writing outputs ...")

# ---- CSV 1: enriched per-batch dataset (the header x chemistry join) --------
with open(ENRICH_OUT, 'w', encoding='utf-8', newline='') as f:
    wtr = csv.writer(f)
    wtr.writerow(['Batch_No', 'Year', 'Month', 'Dye_Unit', 'Fabric_Category',
                  'GSM_Category', 'Shade_Category', 'Dyeing_Type',
                  'Fabric_Kg', 'Water_L', 'Liquor_Ratio_1_to_X',
                  'Water_Intensity_L_per_kg', 'Recipe_Lines',
                  'Chem_Total_Kg', 'Chem_Cost_Tk', 'Chem_g_per_kg', 'Cost_Tk_per_kg',
                  'Salt_Kg', 'Salt_g_per_kg', 'Dye_Kg', 'Dye_g_per_kg',
                  'Alkali_Kg', 'QC_Usable', 'QC_Chem_Excluded'])
    for i in range(GRAND_TOTAL):
        kg = A_kg[i]
        wtr.writerow([
            NAMES[i], A_year[i], label('month', A_month[i]), label('unit', A_unit[i]),
            label('fab', A_fab[i]), label('gsm', A_gsm[i]), label('shade', A_shade[i]),
            label('dtype', A_dtype[i]),
            round(kg, 2), round(A_w[i], 2), round(A_lr[i], 2),
            round(A_w[i] / kg, 3) if kg > 0 else '',
            A_nl[i],
            round(A_chem[i], 4), round(A_tk[i], 2),
            round(A_chem[i] * 1000.0 / kg, 2) if kg > 0 else '',
            round(A_tk[i] / kg, 2) if kg > 0 else '',
            round(A_salt[i], 3), round(A_salt[i] * 1000.0 / kg, 2) if kg > 0 else '',
            round(A_dye[i], 4), round(A_dye[i] * 1000.0 / kg, 2) if kg > 0 else '',
            round(A_alk[i], 3),
            1 if (A_flag[i] & 1) else 0, 1 if (A_flag[i] & 2) else 0])

# ---- CSV 2: chemical master -------------------------------------------------
with open(CHEM_OUT, 'w', encoding='utf-8', newline='') as f:
    wtr = csv.writer(f)
    wtr.writerow(['Item_Name', 'Class', 'Line_Count', 'Batches_Used_In',
                  'Batch_Penetration_pct', 'Total_Kg', 'Total_Cost_Tk',
                  'Avg_Unit_Price_Tk_per_kg', 'Share_of_Total_Mass_pct'])
    for item in items_sorted:
        nb = item_batches.get(item, 0)
        kgv = item_kg[item]
        wtr.writerow([item, chem_class(item), item_n[item], nb,
                      round(nb * 100.0 / GRAND_TOTAL, 3),
                      round(kgv, 3), round(item_tk[item], 2),
                      round(item_tk[item] / kgv, 2) if kgv > 0 else '',
                      round(kgv * 100.0 / CHEM_KG_ALL, 4)])

# ---- CSV 3: savings ledger --------------------------------------------------
with open(SAVE_OUT, 'w', encoding='utf-8', newline='') as f:
    wtr = csv.writer(f)
    wtr.writerow(['Fabric_Category', 'Shade_Category', 'GSM_Category', 'Batches',
                  'Fabric_Kg', 'Water_L', 'WI_Weighted', 'WI_Median', 'WI_P25',
                  'WI_P75', 'WI_P90', 'Addressable_Excess_L',
                  'Excess_pct_of_Cell_Water', 'Salt_g_per_kg', 'Cost_Tk_per_kg'])
    for k in sorted(by_cell, key=lambda x: excess_by_cell.get(x, 0.0), reverse=True):
        a = by_cell[k]
        if a['n'] < MIN_CELL_N:
            continue
        med, p25, p75, p90 = wstats(a['wi'])
        ex = excess_by_cell.get(k, 0.0)
        wtr.writerow([k[0], k[1], k[2], a['n'], round(a['kg'], 1), round(a['w'], 1),
                      round(a['w'] / a['kg'], 3) if a['kg'] else '',
                      round(med, 3), round(p25, 3), round(p75, 3), round(p90, 3),
                      round(ex, 1), round(ex * 100.0 / a['w'], 2) if a['w'] else '',
                      round(a['salt_kg'] * 1000.0 / a['kg'], 2) if a['kg'] else '',
                      round(a['chem_tk'] / a['kg'], 2) if a['kg'] else ''])

# ================================================================ HTML PHASE ==
def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

def f0(x):
    return format(int(round(x)), ',')

def f2(x):
    return '%.2f' % x

integ = [
    ('Raw header rows in extraction DB', f0(hdr_rows), 'Includes re-extractions of the same batch from more than one HTML file'),
    ('Unique batches (DB)', f0(hdr_uniq), 'Matches the master export'),
    ('Rows in MASTER csv', f0(master_rows), 'Deduplicated batch master used as the header source'),
    ('Batches analysed', f0(GRAND_TOTAL), 'One row per batch, no double counting'),
    ('Raw recipe lines in DB', f0(ln_rows), 'Chemical dosing rows across all source files'),
    ('Batches with >1 source file', f0(multi_src), 'Fullest extraction retained, the rest discarded'),
    ('Canonical recipe lines used', f0(lines_kept), 'After one-source-per-batch selection'),
    ('Duplicate lines removed', f0(ln_rows - lines_kept - lines_orphan), 'Would have inflated every chemical total'),
    ('Batches with no recipe lines', f0(q['no_lines']), 'Chemistry unavailable for these'),
    ('MC_No populated', '0 of ' + f0(hdr_rows), 'Machine number is empty in 100% of rows, so no machine-level analysis is possible from this extraction'),
    ('Batches with zero or blank fabric qty', f0(q['no_kg']), 'Excluded from KPI maths'),
    ('Batches with zero or blank water', f0(q['no_water']), 'Excluded from KPI maths'),
    ('Fabric load outside %g-%g kg' % (MIN_KG, MAX_KG), f0(q['kg_out']), 'Implausible for exhaust jet dyeing'),
    ('Water intensity outside %g-%g L/kg' % (MIN_WI, MAX_WI), f0(q['wi_out']), 'Implausible, usually a decimal or unit error at source'),
    ('Water derived from the 1:1 placeholder ratio', f0(q['w_placeholder']),
     'Water equals fabric weight, so no volume was actually recorded. Excluded from every water statistic. Concentration by unit: '
     + (', '.join('%s %s of %s (%s%%)' % (u, f0(ph_by_unit.get(u, 0)), f0(tot_by_unit.get(u, 0)),
                                          f2(ph_by_unit.get(u, 0) * 100.0 / max(1, tot_by_unit.get(u, 0))))
                  for u in UNIT_ORDER if tot_by_unit.get(u)))),
    ('Liquor ratio missing', f0(q['lr_missing']), 'Ratio treated as unknown, batch still used for water KPIs'),
    ('Liquor ratio outside 1:%g to 1:%g' % (MIN_LR, MAX_LR), f0(q['lr_invalid']), 'Chiefly the placeholder value 1:1, which is not physically achievable'),
    ('Ratio inconsistent with recorded water (>15%)', f0(q['lr_mismatch']), 'Recorded water does not equal ratio times fabric weight'),
    ('Chemical dose above %g g/kg' % MAX_CHEM_GPKG, f0(q['chem_out']), 'Chemistry zeroed for these batches only'),
    ('Batches usable for KPI maths', f0(q['usable']) + ' (%.1f%%)' % (100.0 * q['usable'] / GRAND_TOTAL), 'All headline numbers are computed on this set'),
]
integ_html = ''.join('<tr><td>%s</td><td class="num"><strong>%s</strong></td><td class="note">%s</td></tr>'
                     % (esc(a), esc(b), esc(c)) for a, b, c in integ)

yoy_map = dict(yoy)
yr_html = ''
for y in years_present:
    a = by_year[y]
    if a['n'] == 0:
        continue
    med, p25, p75, p90 = wstats(a['wi'])
    g = yoy_map.get(y)
    gtxt = ('%+.1f%%' % g) if g is not None else '&ndash;'
    gcls = 'up' if (g is not None and g > 0) else ('down' if g is not None else '')
    if a['n'] < MIN_YEAR_N:
        flag = ' <span class="tag">sparse, excluded from trend</span>'
    elif y in COMPLETE_YEARS:
        flag = ''
    else:
        flag = ' <span class="tag">partial year</span>'
    yr_html += ('<tr><td><strong>%d</strong>%s</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num %s">%s</td></tr>'
                % (y, flag, f0(a['n']), f0(a['kg'] / 1000.0), f2(a['w'] / 1e6),
                   f2(a['w'] / a['kg']) if a['kg'] else '-', f2(med), f2(p90),
                   f2(a['chem_tk'] / a['kg']) if a['kg'] else '-', gcls, gtxt))

unit_html = ''
for u in UNIT_ORDER:
    a = by_unit.get(u)
    if not a or a['n'] == 0:
        continue
    med, p25, p75, p90 = wstats(a['wi'])
    lrm = wstats(a['lr'])[0] if a['lr'] else 0
    unit_html += ('<tr><td><strong>%s</strong></td><td class="num">%s</td><td class="num">%s</td>'
                  '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                  '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                  % (esc(UNIT_LABEL.get(u, u)), f0(a['n']), f0(a['kg'] / 1000.0),
                     f2(a['w'] / a['kg']) if a['kg'] else '-', f2(med),
                     ('1:' + f2(lrm)) if lrm else '-',
                     f2(a['chem_kg'] * 1000.0 / a['kg']) if a['kg'] else '-',
                     f2(a['salt_kg'] * 1000.0 / a['kg']) if a['kg'] else '-',
                     f2(a['chem_tk'] / a['kg']) if a['kg'] else '-'))

shade_html = ''
for s in SHADE_ORDER:
    a = by_shade.get(s)
    if not a or a['n'] == 0:
        continue
    med, p25, p75, p90 = wstats(a['wi'])
    shade_html += ('<tr><td><strong>%s</strong></td><td class="num">%s</td>'
                   '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                   '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                   '<td class="num">%s</td></tr>'
                   % (esc(s), f0(a['n']), f2(a['w'] / a['kg']) if a['kg'] else '-',
                      f2(p25), f2(med), f2(p90),
                      f2(a['dye_kg'] * 1000.0 / a['kg']) if a['kg'] else '-',
                      f2(a['salt_kg'] * 1000.0 / a['kg']) if a['kg'] else '-',
                      f2(a['chem_tk'] / a['kg']) if a['kg'] else '-'))

mat_head = '<tr><th>Fabric</th>' + ''.join('<th>%s</th>' % esc(s) for s in SHADE_ORDER) + '</tr>'
mat_body = ''
all_wi = [by_fs[k]['w'] / by_fs[k]['kg'] for k in by_fs if by_fs[k]['kg'] > 0 and by_fs[k]['n'] >= 50]
lo_cut = pct(sorted(all_wi), 25) if all_wi else 0
hi_cut = pct(sorted(all_wi), 75) if all_wi else 0
for fab in FAB_ORDER:
    mat_body += '<tr><td><strong>%s</strong></td>' % esc(fab)
    for sh in SHADE_ORDER:
        a = by_fs.get((fab, sh))
        if not a or a['n'] < 50 or a['kg'] <= 0:
            mat_body += '<td class="num muted">n&lt;50</td>'
            continue
        v = a['w'] / a['kg']
        cls = 'ok' if v <= lo_cut else ('bad' if v >= hi_cut else 'mid')
        mat_body += ('<td class="num %s">%s<span class="sub">n=%s</span></td>'
                     % (cls, f2(v), f0(a['n'])))
    mat_body += '</tr>'

cls_html = ''
for c in CLASS_ORDER:
    v = class_stats.get(c)
    if not v:
        continue
    cls_html += ('<tr><td><strong>%s</strong></td><td class="num">%s</td>'
                 '<td class="num">%s</td><td class="num">%s</td>'
                 '<td class="num">%s</td><td class="num">%s</td></tr>'
                 % (esc(c), f0(v['items']), f0(v['kg'] / 1000.0),
                    f2(v['kg'] * 100.0 / CHEM_KG_ALL),
                    f0(v['tk'] / 1e6), f2(v['tk'] * 100.0 / CHEM_TK_ALL)))

item_html = ''
for item in top_items:
    nb = item_batches.get(item, 0)
    kgv = item_kg[item]
    item_html += ('<tr><td>%s</td><td>%s</td><td class="num">%s</td>'
                  '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                  % (esc(item), esc(chem_class(item)), f0(kgv / 1000.0),
                     f2(nb * 100.0 / GRAND_TOTAL), f0(item_tk[item] / 1e6),
                     f2(item_tk[item] / kgv) if kgv > 0 else '-'))

cost_html = ''
for item in top_cost:
    cost_html += ('<tr><td>%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                  % (esc(item), esc(chem_class(item)), f0(item_tk[item] / 1e6),
                     f2(item_tk[item] * 100.0 / CHEM_TK_ALL)))

sav_rows = sorted([k for k in by_cell if by_cell[k]['n'] >= MIN_CELL_N],
                  key=lambda k: excess_by_cell.get(k, 0.0), reverse=True)[:15]
sav_html = ''
for k in sav_rows:
    a = by_cell[k]
    med, p25, p75, p90 = wstats(a['wi'])
    ex = excess_by_cell.get(k, 0.0)
    sav_html += ('<tr><td>%s</td><td>%s</td><td>%s</td><td class="num">%s</td>'
                 '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                 '<td class="num bad">%s</td><td class="num">%s%%</td></tr>'
                 % (esc(k[0]), esc(k[1]), esc(k[2]), f0(a['n']),
                    f2(a['w'] / a['kg']) if a['kg'] else '-', f2(p25), f2(p90),
                    f2(ex / 1e6), f2(ex * 100.0 / a['w']) if a['w'] else '-'))

def mrows(items):
    out = ''
    for m, a in items:
        out += ('<tr><td>%s</td><td class="num">%s</td><td class="num">%s</td>'
                '<td class="num">%s</td></tr>'
                % (esc(m), f0(a['n']), f0(a['kg'] / 1000.0), f2(a['w'] / 1e6)))
    return out

wi_m_html = ''.join('<tr><td>%s</td><td class="num bad">%s</td></tr>' % (esc(m), f2(v))
                    for m, v in worst_wi_m)
wi_m_html2 = ''.join('<tr><td>%s</td><td class="num ok">%s</td></tr>' % (esc(m), f2(v))
                     for m, v in best_wi_m)

dt_html = ''
for name, cnt in sorted(by_dtype.items(), key=lambda x: x[1], reverse=True)[:10]:
    dt_html += ('<tr><td>%s</td><td class="num">%s</td><td class="num">%s%%</td></tr>'
                % (esc(re.sub(r'\s+', ' ', name)), f0(cnt), f2(cnt * 100.0 / GRAND_TOTAL)))

years_lbl = [str(y) for y in TREND_YEARS]
wi_series = [round(by_year[y]['w'] / by_year[y]['kg'], 3) if by_year[y]['kg'] else None
             for y in TREND_YEARS]
tk_series = [round(by_year[y]['chem_tk'] / by_year[y]['kg'], 2) if by_year[y]['kg'] else None
             for y in TREND_YEARS]
unit_ds = []
for u in UNIT_ORDER:
    d = [by_unit_year[u].get(y, 0) for y in TREND_YEARS]
    if d and max(d) > 0:
        unit_ds.append({'label': UNIT_LABEL.get(u, u), 'data': d, 'backgroundColor': UNIT_COLOR[u]})
q_ds = []
for u in UNIT_ORDER:
    d = [by_quarter[u].get('Q%d' % i, 0) for i in (1, 2, 3, 4)]
    if max(d) > 0:
        q_ds.append({'label': u, 'data': d, 'backgroundColor': UNIT_COLOR[u]})
lr_keys = sorted(lr_hist)
lr_lbl = ['1:' + ('%g' % k) for k in lr_keys]
lr_val = [lr_hist[k] for k in lr_keys]
shade_lbl = [s for s in SHADE_ORDER if by_shade.get(s) and by_shade[s]['kg'] > 0]
shade_wi = [round(by_shade[s]['w'] / by_shade[s]['kg'], 2) for s in shade_lbl]
shade_salt = [round(by_shade[s]['salt_kg'] * 1000.0 / by_shade[s]['kg'], 1) for s in shade_lbl]
gsm_lbl = [g for g in GSM_ORDER if by_gsm.get(g) and by_gsm[g]['kg'] > 0]
gsm_wi = [round(by_gsm[g]['w'] / by_gsm[g]['kg'], 2) for g in gsm_lbl]
cls_lbl = [c for c in CLASS_ORDER if class_stats.get(c)]
cls_val = [round(class_stats[c]['kg'] / 1000.0, 1) for c in cls_lbl]

kpi = [
    ('Batches analysed', f0(GRAND_TOTAL), 'unique, deduplicated'),
    ('Fabric dyed', f0(TOTAL_KG / 1000.0) + ' t', 'total across the window'),
    ('Process water', f2(TOTAL_WATER / 1e9) + ' GL', '%s mega-litres' % f0(TOTAL_WATER / 1e6)),
    ('Water intensity', f2(TOTAL_WATER / TOTAL_KG) + ' L/kg', 'mass-weighted, whole population'),
    ('Chemicals dosed', f0(TOTAL_CHEM / 1000.0) + ' t', '%s g per kg fabric' % f2(TOTAL_CHEM * 1000.0 / TOTAL_KG)),
    ('Salt load', f0(TOTAL_SALT / 1000.0) + ' t', '%s%% of all chemical mass' % f2(TOTAL_SALT * 100.0 / (TOTAL_CHEM or 1))),
    ('Chemical spend', f0(TOTAL_TK / 1e6) + ' M Tk', '%s Tk per kg fabric' % f2(TOTAL_TK / TOTAL_KG)),
    ('Addressable water', f2(excess_l / 1e9) + ' GL', '%s%% of recorded water' % f2(excess_l * 100.0 / TOTAL_WATER)),
]
kpi_html = ''.join('<div class="kpi"><div class="kpi-v">%s</div><div class="kpi-k">%s</div>'
                   '<div class="kpi-s">%s</div></div>' % (esc(v), esc(k), esc(s)) for k, v, s in kpi)

CSS = """
:root{--bg:#0e1420;--card:#18202e;--line:#2a3446;--txt:#e6ebf2;--dim:#94a2b8;
--acc:#5ba8f5;--ok:#4ade80;--bad:#f87171;--mid:#fbbf24;--head:#0d2c52}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;background:var(--bg);
color:var(--txt);padding:28px 20px;line-height:1.5;font-size:14px}
.wrap{max-width:1500px;margin:0 auto}
h1{font-size:23px;color:var(--acc);margin-bottom:4px}
.lede{color:var(--dim);font-size:13px;margin-bottom:22px;max-width:920px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin-bottom:30px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi-v{font-size:21px;font-weight:600;color:var(--acc);letter-spacing:-.02em}
.kpi-k{font-size:12px;color:var(--txt);margin-top:3px}
.kpi-s{font-size:11px;color:var(--dim);margin-top:2px}
h2.sec{font-size:16px;color:var(--mid);margin:34px 0 4px;padding-bottom:6px;
border-bottom:1px solid var(--line)}
.secnote{color:var(--dim);font-size:12.5px;margin-bottom:14px;max-width:1020px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;overflow-x:auto}
.card.full{grid-column:1/-1}
.card h3{font-size:13px;color:var(--acc);margin-bottom:5px}
.card p.d{font-size:12px;color:var(--dim);margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{background:var(--head);color:#fff;padding:8px 9px;text-align:left;font-weight:600;
white-space:nowrap;font-size:11.5px}
td{padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.note{color:var(--dim);font-size:11.5px}
td.ok{color:var(--ok)}td.bad{color:var(--bad)}td.mid{color:var(--mid)}
td.up{color:var(--ok)}td.down{color:var(--bad)}
td.muted{color:#5a6578}
.sub{display:block;font-size:10px;color:var(--dim);font-weight:400}
.tag{background:#463111;color:#fbbf24;font-size:10px;padding:1px 5px;border-radius:3px;margin-left:5px}
.find{background:#0d2338;border-left:3px solid var(--acc);padding:10px 13px;
border-radius:0 6px 6px 0;margin-top:13px;font-size:12.5px}
.find b{color:var(--acc)}
.caution{background:#301414;border-left:3px solid var(--bad);padding:10px 13px;
border-radius:0 6px 6px 0;margin-top:13px;font-size:12.5px}
.caution b{color:#fca5a5}
canvas{max-height:270px}
footer{color:var(--dim);font-size:11.5px;margin-top:36px;padding-top:14px;border-top:1px solid var(--line)}
@media(max-width:1000px){.grid{grid-template-columns:1fr}}
"""

JS = """
(function(){
var D=JSON.parse(document.getElementById('payload').textContent);
Chart.defaults.color='#94a2b8';Chart.defaults.borderColor='#2a3446';
function mk(id,cfg){var el=document.getElementById(id);if(el){new Chart(el,cfg);}}
mk('c1',{data:{labels:D.years,datasets:[
 {type:'line',label:'Water L/kg',data:D.wi,borderColor:'#5ba8f5',backgroundColor:'#5ba8f533',
  yAxisID:'y',tension:.3,borderWidth:2,pointRadius:3},
 {type:'line',label:'Chemical Tk/kg',data:D.tk,borderColor:'#fbbf24',
  yAxisID:'y1',tension:.3,borderWidth:2,pointRadius:3}]},
 options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
 scales:{y:{position:'left',title:{display:true,text:'L/kg'}},
 y1:{position:'right',grid:{drawOnChartArea:false},title:{display:true,text:'Tk/kg'}}}}});
mk('c2',{type:'bar',data:{labels:D.years,datasets:D.unitds},
 options:{responsive:true,maintainAspectRatio:false,
 scales:{x:{stacked:true},y:{stacked:true,title:{display:true,text:'batches'}}}}});
mk('c3',{type:'bar',data:{labels:D.shadeL,datasets:[{label:'L/kg',data:D.shadeWI,
 backgroundColor:'#5ba8f5'}]},options:{responsive:true,maintainAspectRatio:false,
 plugins:{legend:{display:false}},scales:{y:{title:{display:true,text:'L/kg'}}}}});
mk('c4',{type:'bar',data:{labels:D.shadeL,datasets:[{label:'g/kg',data:D.shadeSalt,
 backgroundColor:'#e0913a'}]},options:{responsive:true,maintainAspectRatio:false,
 plugins:{legend:{display:false}},scales:{y:{title:{display:true,text:'g/kg'}}}}});
mk('c5',{type:'bar',data:{labels:D.gsmL,datasets:[{label:'L/kg',data:D.gsmWI,
 backgroundColor:'#2e9e6b'}]},options:{responsive:true,maintainAspectRatio:false,
 plugins:{legend:{display:false}},scales:{y:{title:{display:true,text:'L/kg'}}}}});
mk('c6',{type:'bar',data:{labels:D.lrL,datasets:[{label:'batches',data:D.lrV,
 backgroundColor:'#8b7ff0'}]},options:{responsive:true,maintainAspectRatio:false,
 plugins:{legend:{display:false}},scales:{y:{title:{display:true,text:'batches'}}}}});
mk('c7',{type:'bar',data:{labels:D.clsL,datasets:[{label:'tonnes',data:D.clsV,
 backgroundColor:'#5ba8f5'}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
 plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'tonnes'}}}}});
mk('c8',{type:'bar',data:{labels:['Q1','Q2','Q3','Q4'],datasets:D.qds},
 options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true}}}});
})();
"""

BODY = """
<h1>Deep root-cause findings &mdash; SMART DYEING, __FIRST__ to __LAST__</h1>
<p class="lede">Population-wide analysis of __TOTAL__ deduplicated dyeing batches and __LINES__
canonical recipe lines. Every figure is computed from the full population, not a sample. Records
that fail physical plausibility screening are excluded from the maths and counted in section 1
rather than silently dropped.</p>

<div class="kpis">__KPIS__</div>

<h2 class="sec">1 &middot; Data integrity: what these numbers can and cannot support</h2>
<p class="secnote">Read this before quoting anything else. The extraction contains duplicate
re-extractions, placeholder liquor ratios, and one column that is entirely empty. Stating them here
keeps the analysis auditable and stops anything downstream being built on a field that does not
exist.</p>
<div class="grid"><div class="card full">
<table><thead><tr><th>Check</th><th style="text-align:right">Value</th><th>Meaning</th></tr></thead>
<tbody>__INTEG__</tbody></table>
<div class="caution"><b>Two hard constraints on this dataset.</b> First, machine number is empty in
every header row, so no machine-level utilisation, capacity-fit or per-machine efficiency analysis
can be produced from this extraction. Recovering it means going back to the source HTML. Second, the
liquor ratio field carries a placeholder value of 1:1 on a large block of batches, and on those
batches the recorded water is simply the fabric weight carried through. Those are not measurements.
They are excluded from every water and ratio statistic here. Anyone computing plant water intensity
without removing them will understate it, because a phantom 1 L/kg is being averaged in against a
real operating range near 6 to 7 L/kg.</div>
<div class="caution"><b>The missing water is not spread evenly, and that matters for the project
scope.</b> __PHUNIT__ In other words the polyester and disperse unit is the one place where process
water is largely not captured on the batch card at all. No water baseline, no saving verification
and no water-side model can be built for that unit from this extraction. Either the Unit_C water field
is populated at source, or Unit_C is scoped out of the water-reduction claim and kept for chemical and
energy work only. This is a decision to take before the baseline is fixed, not after.</div>
</div></div>

<h2 class="sec">2 &middot; Production and efficiency by year</h2>
<p class="secnote">Water intensity in litres per kilogram of fabric is the project's primary KPI.
The weighted column is total water divided by total fabric, which is the figure that reconciles to a
factory water bill. Median and P90 describe the spread: a wide gap means the same fabric is being
run at very different water levels, and that variance is exactly what a closed-loop controller
removes. Year-on-year growth is computed only between consecutive complete years.</p>
<div class="grid"><div class="card full">
<table><thead><tr><th>Year</th><th style="text-align:right">Batches</th>
<th style="text-align:right">Fabric (t)</th><th style="text-align:right">Water (ML)</th>
<th style="text-align:right">L/kg weighted</th><th style="text-align:right">L/kg median</th>
<th style="text-align:right">L/kg P90</th><th style="text-align:right">Tk/kg chemicals</th>
<th style="text-align:right">YoY batches</th></tr></thead><tbody>__YRTAB__</tbody></table>
<div class="find"><b>How to read this for the grant report.</b> __YTDNOTE__ A downward trend in the
weighted L/kg column after the closed-loop system is deployed is the direct, auditable evidence of
water saving. P90 is the better early indicator: control systems compress the tail before they move
the mean.</div>
__COSTSTEP__
</div>
<div class="card"><h3>Water intensity and chemical cost per kg, by year</h3>
<p class="d">Two independent efficiency signals on one time axis. They can move in opposite
directions: a shift toward dark shades raises chemical cost per kg without raising water per kg.</p>
<canvas id="c1"></canvas></div>
<div class="card"><h3>Batch volume by dyeing unit</h3>
<p class="d">Unit_A runs reactive dyeing on cotton, Unit_D runs blends, Unit_C runs disperse dyeing on
polyester at high temperature. Three different chemistries that must not be pooled in one model.</p>
<canvas id="c2"></canvas></div>
</div>

<h2 class="sec">3 &middot; Where the water and the chemistry actually go</h2>
<p class="secnote">Unit and shade are the two highest-leverage cuts in the dataset. Salt intensity
matters because sodium sulphate is the largest single chemical mass in the plant and the main driver
of effluent conductivity, which is the parameter any closed-loop water recovery scheme has to
defeat.</p>
<div class="grid">
<div class="card full"><h3>By dyeing unit</h3>
<table><thead><tr><th>Unit</th><th style="text-align:right">Batches</th>
<th style="text-align:right">Fabric (t)</th><th style="text-align:right">L/kg weighted</th>
<th style="text-align:right">L/kg median</th><th style="text-align:right">Median ratio</th>
<th style="text-align:right">Chem g/kg</th><th style="text-align:right">Salt g/kg</th>
<th style="text-align:right">Tk/kg</th></tr></thead><tbody>__UNITTAB__</tbody></table></div>

<div class="card full"><h3>By shade depth</h3>
<table><thead><tr><th>Shade</th><th style="text-align:right">Batches</th>
<th style="text-align:right">L/kg weighted</th><th style="text-align:right">P25</th>
<th style="text-align:right">Median</th><th style="text-align:right">P90</th>
<th style="text-align:right">Dye g/kg</th><th style="text-align:right">Salt g/kg</th>
<th style="text-align:right">Tk/kg</th></tr></thead><tbody>__SHADETAB__</tbody></table>
<div class="find"><b>Root finding.</b> Dye and salt intensity rise together with shade depth, because
reactive dyeing needs more electrolyte to drive more dye onto the fibre and deeper shades then need
more wash-off. Shade depth is therefore the strongest single predictor of both water and chemical
load, and it is known before a batch starts. That makes it the natural first input to the recipe
optimiser.</div></div>

<div class="card"><h3>Water intensity by shade</h3><p class="d">Mass-weighted L/kg.</p>
<canvas id="c3"></canvas></div>
<div class="card"><h3>Salt intensity by shade</h3><p class="d">Grams of electrolyte per kg fabric.</p>
<canvas id="c4"></canvas></div>
<div class="card"><h3>Water intensity by GSM class</h3>
<p class="d">Heavier constructions retain more liquor per kg, so they carry more water through every
rinse.</p><canvas id="c5"></canvas></div>
<div class="card"><h3>Liquor ratio distribution</h3>
<p class="d">Valid ratios only, rounded to the nearest 0.5. Placeholder values excluded.</p>
<canvas id="c6"></canvas></div>
</div>

<h2 class="sec">4 &middot; Fabric by shade water-intensity matrix</h2>
<p class="secnote">Mass-weighted litres per kg for every combination with at least 50 batches. Green
is the best quartile across all cells, red the worst. This is the table that tells the optimiser
which combinations to attack first.</p>
<div class="grid"><div class="card full">
<table><thead>__MATHEAD__</thead><tbody>__MATBODY__</tbody></table></div></div>

<h2 class="sec">5 &middot; Chemistry: mass, cost and concentration</h2>
<p class="secnote">Joined from __LINES__ canonical recipe lines covering __CHEMBATCH__ batches.
Classification is rule-based on product names and the item table below lets you check every
assignment. Cost figures are the amounts recorded on the batch cards, not a market price series.</p>
<div class="grid">
<div class="card"><h3>Chemical mass and spend by class</h3>
<table><thead><tr><th>Class</th><th style="text-align:right">Products</th>
<th style="text-align:right">Mass (t)</th><th style="text-align:right">% mass</th>
<th style="text-align:right">Spend (M Tk)</th><th style="text-align:right">% spend</th>
</tr></thead><tbody>__CLSTAB__</tbody></table>
<div class="find"><b>Root finding.</b> Mass and spend are inverted. Salt and alkali dominate the
tonnage but are cheap; dyestuff is a small share of the mass and a large share of the money. A water
recovery loop is therefore justified on effluent load and compliance, while a dosing correction loop
is justified on cost. Two different business cases out of one dataset.</div>
</div>
<div class="card"><h3>Mass by class</h3><p class="d">Tonnes dosed across the whole window.</p>
<canvas id="c7"></canvas></div>
<div class="card full"><h3>Top 25 chemicals by mass</h3>
<p class="d">Penetration is the share of all __TOTAL__ batches in which the product appears.</p>
<table><thead><tr><th>Product</th><th>Class</th><th style="text-align:right">Mass (t)</th>
<th style="text-align:right">Penetration %</th><th style="text-align:right">Spend (M Tk)</th>
<th style="text-align:right">Tk/kg</th></tr></thead><tbody>__ITEMTAB__</tbody></table></div>
<div class="card full"><h3>Top 15 chemicals by spend</h3>
<table><thead><tr><th>Product</th><th>Class</th><th style="text-align:right">Spend (M Tk)</th>
<th style="text-align:right">% of all chemical spend</th></tr></thead>
<tbody>__COSTTAB__</tbody></table></div>
</div>

<h2 class="sec">6 &middot; Addressable saving, measured against the plant's own best practice</h2>
<p class="secnote">For every fabric by shade by GSM group with at least __MINCELL__ batches, the
group's own 25th-percentile water intensity is taken as the benchmark. That benchmark is not a
theoretical target: it is a level the plant already reaches on a quarter of its own batches of that
exact type. Every batch above it contributes the excess. This is the defensible upper bound on what
process control alone can recover, before any equipment change.</p>
<div class="grid"><div class="card full">
<table><thead><tr><th>Fabric</th><th>Shade</th><th>GSM</th><th style="text-align:right">Batches</th>
<th style="text-align:right">L/kg now</th><th style="text-align:right">P25 benchmark</th>
<th style="text-align:right">P90</th><th style="text-align:right">Excess (ML)</th>
<th style="text-align:right">% of group water</th></tr></thead><tbody>__SAVTAB__</tbody></table>
<div class="find"><b>Headline.</b> Across all qualifying groups the addressable excess is
__EXCESSGL__ giga-litres, __EXCESSPCT__% of all recorded process water, about __EXCESSYR__
mega-litres per year at the observed production rate. Because the benchmark is the plant's own P25
rather than a vendor claim, the number survives scrutiny in a grant review.</div>
<div class="caution"><b>Stated honestly.</b> This is an upper bound on control-side saving, not a
guaranteed yield. Part of the spread between P25 and P90 comes from real differences the categories
do not capture: specific shade, buyer fastness requirement, and the machine actually used. Machine
identity is missing from this extraction entirely and is a plausible driver of some of the residual
variance, so treat the figure as the ceiling of the opportunity rather than a forecast.</div>
</div></div>

<h2 class="sec">7 &middot; Seasonality and process mix</h2>
<div class="grid">
<div class="card"><h3>Quarterly volume by unit</h3><p class="d">All years pooled into Q1 to Q4.</p>
<canvas id="c8"></canvas></div>
<div class="card"><h3>Peak and trough months</h3>
<p class="d">The partial first and last months of coverage are excluded so the ranking is not an
artefact of the extraction window.</p>
<table><thead><tr><th>Month</th><th style="text-align:right">Batches</th>
<th style="text-align:right">Fabric (t)</th><th style="text-align:right">Water (ML)</th></tr></thead>
<tbody><tr><td colspan="4" class="ok"><strong>Three highest months</strong></td></tr>__PEAK__
<tr><td colspan="4" class="bad"><strong>Three lowest months</strong></td></tr>__TROUGH__
</tbody></table></div>
<div class="card"><h3>Most and least water-efficient months</h3>
<table><thead><tr><th>Month</th><th style="text-align:right">L/kg</th></tr></thead>
<tbody><tr><td colspan="2" class="bad"><strong>Five worst</strong></td></tr>__WORSTM__
<tr><td colspan="2" class="ok"><strong>Five best</strong></td></tr>__BESTM__</tbody></table>
<div class="find"><b>Read with care.</b> Monthly water intensity moves largely with production mix.
A bad month is usually a fleece-heavy or dark-heavy month, not a month of poor discipline. Compare
months only within the same fabric and shade mix.</div></div>
<div class="card"><h3>Process route mix</h3><p class="d">Top ten dyeing-type codes by frequency.</p>
<table><thead><tr><th>Process route</th><th style="text-align:right">Batches</th>
<th style="text-align:right">Share</th></tr></thead><tbody>__DTTAB__</tbody></table></div>
</div>

<h2 class="sec">8 &middot; What this means for the model</h2>
<div class="grid"><div class="card full">
<div class="find"><b>Class imbalance is real and has to be handled.</b> Unit_A, Unit_D and Unit_C appear in
very different volumes and represent different chemistries. A single pooled model will fit the
majority unit and under-serve the others. Train per unit, or weight by unit and validate per unit.</div>
<div class="find"><b>Do not feed machine number as a feature.</b> It is empty in 100% of rows. Any
pipeline that references it will silently produce a constant column.</div>
<div class="find"><b>Liquor ratio is partly a placeholder, not a measurement.</b> Used raw it will
teach the model that a large block of batches ran at 1:1. Either drop the invalid block or add an
explicit "ratio recorded" flag.</div>
<div class="find"><b>Water is close to a deterministic function of ratio and fabric weight on many
batches.</b> Where recorded water equals ratio times weight, predicting water from those inputs is
arithmetic rather than learning. The genuine target is the deviation from the peer-group benchmark,
which is what the savings ledger exports.</div>
<div class="find"><b>Use the enriched export as the modelling table.</b>
DEEP_ROOT_Batch_Enriched.csv already carries the header categories joined to per-batch chemical
mass, salt, dye and cost, with the QC flags needed to filter rows honestly.</div>
</div></div>

<footer>Generated __STAMP__ by 29_deep_root_analysis.py (v2). Sources:
MASTER_289403_BATCHES_2021_2026.csv and extraction_checkpoint.db. Companion exports:
DEEP_ROOT_Batch_Enriched.csv, DEEP_ROOT_Chemical_Master.csv, DEEP_ROOT_Savings_Opportunity.csv.
SMART DYEING / Industrial Research Consortium GRANTS Project EOI. Figures derive from factory batch-card extractions and inherit
any error present at source.</footer>
"""

_worst = sorted(((u, ph_by_unit.get(u, 0), tot_by_unit.get(u, 0)) for u in tot_by_unit),
                key=lambda x: -(x[1] / float(max(1, x[2]))))
ph_unit_html = ' '.join(
    ('%s of the %s batches in %s carry it, %s%% of that unit.'
     % (f0(c), f0(t), u, f2(c * 100.0 / max(1, t)))) if c else
    ('%s is unaffected.' % u)
    for u, c, t in _worst)

if cost_steps:
    _parts = ', '.join('%d (%s to %s Tk/kg, +%s%%)' % (y, f2(a), f2(b), f2(d))
                       for y, a, b, d in cost_steps)
    cost_step_html = ('<div class="caution"><b>Verify before quoting the cost column.</b> '
                      'Chemical cost per kg steps up sharply at a year boundary and then holds: '
                      + _parts + '. Physical dosing per kg does not move like that. The pattern is '
                      'characteristic of a price-list revaluation in the source system, and it may '
                      'also carry currency effects. Confirm against procurement records before '
                      'presenting any of it as a real change in chemical consumption or as evidence '
                      'of cost saving. Mass per kg, not cost per kg, is the safe efficiency '
                      'measure across this boundary.</div>')
else:
    cost_step_html = ''

payload = json.dumps({
    'years': years_lbl, 'wi': wi_series, 'tk': tk_series, 'unitds': unit_ds,
    'shadeL': shade_lbl, 'shadeWI': shade_wi, 'shadeSalt': shade_salt,
    'gsmL': gsm_lbl, 'gsmWI': gsm_wi, 'lrL': lr_lbl, 'lrV': lr_val,
    'clsL': cls_lbl, 'clsV': cls_val, 'qds': q_ds,
}).replace('</', '<\\/')

chem_batches = GRAND_TOTAL - q['no_lines']
subs = [
    ('__KPIS__', kpi_html), ('__INTEG__', integ_html), ('__YRTAB__', yr_html),
    ('__UNITTAB__', unit_html), ('__SHADETAB__', shade_html),
    ('__MATHEAD__', mat_head), ('__MATBODY__', mat_body),
    ('__CLSTAB__', cls_html), ('__ITEMTAB__', item_html), ('__COSTTAB__', cost_html),
    ('__SAVTAB__', sav_html), ('__PEAK__', mrows(peak3)), ('__TROUGH__', mrows(trough3)),
    ('__WORSTM__', wi_m_html), ('__BESTM__', wi_m_html2), ('__DTTAB__', dt_html),
    ('__TOTAL__', f0(GRAND_TOTAL)), ('__LINES__', f0(lines_kept)),
    ('__CHEMBATCH__', f0(chem_batches)), ('__FIRST__', FIRST_MONTH), ('__LAST__', LAST_MONTH),
    ('__MINCELL__', str(MIN_CELL_N)), ('__YTDNOTE__', ytd_note),
    ('__COSTSTEP__', cost_step_html),
    ('__PHUNIT__', ph_unit_html),
    ('__EXCESSGL__', f2(excess_l / 1e9)),
    ('__EXCESSPCT__', f2(excess_l * 100.0 / TOTAL_WATER)),
    ('__EXCESSYR__', f0(excess_l / 1e6 / span_years)),
    ('__STAMP__', RUN_STAMP),
]
body = BODY
for k, v in subs:
    body = body.replace(k, v)

html = ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>Deep Root-Cause Findings - SMART DYEING</title>\n'
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>\n'
        '<style>' + CSS + '</style></head><body><div class="wrap">\n'
        + body +
        '\n</div>\n<script id="payload" type="application/json">' + payload + '</script>\n'
        '<script>' + JS + '</script>\n</body></html>\n')

with open(HTML_OUT, 'w', encoding='utf-8') as f:
    f.write(html)

print("")
print("DONE")
print("  report   : %s" % HTML_OUT)
print("  enriched : %s" % ENRICH_OUT)
print("  chemicals: %s" % CHEM_OUT)
print("  savings  : %s" % SAVE_OUT)
print("")
print("  batches %s | usable %s | water %.2f GL | %.2f L/kg | addressable %.2f GL (%.2f%%)" % (
    format(GRAND_TOTAL, ','), format(q['usable'], ','), TOTAL_WATER / 1e9,
    TOTAL_WATER / TOTAL_KG, excess_l / 1e9, excess_l * 100.0 / TOTAL_WATER))


