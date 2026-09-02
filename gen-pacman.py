import random

random.seed(42)

# ============================================================
# V5 — custom scripted route (grid stays wide/horizontal, 52x7):
#   Zone 1 (cols 0..Q):        fine zigzag DOWN
#   Connector:                  hop along bottom row to the 1/2 mark
#   Zone 2 (cols Q..2Q):        fine zigzag UP
#   Connector:                  hop along top row to the 3/4 mark
#   Zone 3 (cols 3Q..3Q+6):     full vertical sweeps (down/up), dodges the ghost
#   Zone 4 (remaining cols):    fine zigzag again, finishes top-right
# v1..v4 untouched.
# ============================================================

CELL = 14
GAP = 2
PITCH = CELL + GAP
COLS = 52
ROWS = 7
GRID_W = COLS * PITCH - GAP
GRID_H = ROWS * PITCH - GAP

MARGIN_X = 26
GRID_TOP = 82
TITLE_Y = 34
SUBLINE_Y = 58
FOOTER_Y = GRID_TOP + GRID_H + 36

VIEW_W = GRID_W + MARGIN_X * 2
VIEW_H = FOOTER_Y + 18

TOTAL_DUR = 24.0
EPS = 0.0009
DODGE_LEAD = 4
DODGE_BUMP = 5
GHOST_DUR = TOTAL_DUR / 3.0

LEVEL_WEIGHTS = [0.32, 0.30, 0.20, 0.12, 0.06]
def generate_contribution_data(cols, rows, seed=42):
    r = random.Random(seed)
    return [[r.choices([0, 1, 2, 3, 4], weights=LEVEL_WEIGHTS)[0] for _ in range(cols)]
            for _ in range(rows)]
levels_grid = generate_contribution_data(COLS, ROWS, seed=42)

def cell_xy(row, col):
    return MARGIN_X + col * PITCH, GRID_TOP + row * PITCH
def cell_center(row, col):
    x, y = cell_xy(row, col)
    return x + CELL / 2, y + CELL / 2
def fmt(x):
    return f"{x:.6f}".rstrip('0').rstrip('.') if '.' in f"{x:.6f}" else f"{x:.6f}"

Q = COLS // 4                       # 13
Z1_LO, Z1_HI = 0, Q                 # 0..13
Z2_LO, Z2_HI = Q, 2 * Q             # 13..26
Z3_START = 3 * Q                    # 39
Z3_COLS = 7
Z3_LO, Z3_HI = Z3_START, Z3_START + Z3_COLS - 1   # 39..45
Z4_LO, Z4_HI = Z3_HI, COLS - 1                     # 45..51

GHOST_ROW = 3
ghost_x_lo = MARGIN_X + Z3_LO * PITCH + CELL / 2
ghost_x_hi = MARGIN_X + Z3_HI * PITCH + CELL / 2
ghost_y = GRID_TOP + GHOST_ROW * PITCH + CELL / 2

# ---------- path builder with explicit row/col state (avoids diagonal bugs) ----------
d_parts = []
segments = []
acc = 0.0
current_row = None
current_col = None

def moveto(row, col):
    global current_row, current_col
    x, y = cell_center(row, col)
    d_parts.append(f"M {x:.1f},{y:.1f}")
    current_row, current_col = row, col

def hmove(col):
    """Move horizontally to `col`, staying on current_row."""
    global current_col, acc
    x0, _ = cell_center(current_row, current_col)
    x1, y = cell_center(current_row, col)
    if x1 != x0:
        d_parts.append(f"L {x1:.1f},{y:.1f}")
        segments.append(dict(kind='h', fixed=y, a=x0, b=x1, cum=acc))
        acc += abs(x1 - x0)
    current_col = col

def vmove(row, dodge=False):
    """Move vertically to `row`, staying on current_col."""
    global current_row, acc
    _, y0 = cell_center(current_row, current_col)
    x, y1 = cell_center(row, current_col)
    if y1 != y0:
        if dodge:
            dir_sign = 1 if y1 > y0 else -1
            ya = ghost_y - dir_sign * DODGE_LEAD
            yb = ghost_y + dir_sign * DODGE_LEAD
            d_parts.append(f"L {x:.1f},{ya:.1f}")
            d_parts.append(f"Q {x+DODGE_BUMP:.1f},{ghost_y:.1f} {x:.1f},{yb:.1f}")
            d_parts.append(f"L {x:.1f},{y1:.1f}")
        else:
            d_parts.append(f"L {x:.1f},{y1:.1f}")
        segments.append(dict(kind='v', fixed=x, a=y0, b=y1, cum=acc))
        acc += abs(y1 - y0)
    current_row = row

# --- Zone 1: zigzag DOWN, cols [Z1_LO, Z1_HI] ---
moveto(0, Z1_LO)
for r in range(ROWS):
    target_col = Z1_HI if (r % 2 == 0) else Z1_LO
    hmove(target_col)
    if r < ROWS - 1:
        vmove(r + 1)

# --- Connector: bottom row hop to the 1/2 mark ---
hmove(Z2_HI)

# --- Zone 2: zigzag UP, cols [Z2_LO, Z2_HI] ---
for r in range(ROWS - 2, -1, -1):
    vmove(r)
    target_col = Z2_LO if current_col == Z2_HI else Z2_HI
    hmove(target_col)

# --- Connector: top row hop to the 3/4 mark ---
hmove(Z3_LO)

# --- Zone 3: full vertical sweeps w/ ghost dodge, cols [Z3_LO, Z3_HI] ---
down = True
for c in range(Z3_LO, Z3_HI + 1):
    if c > Z3_LO:
        hmove(c)
    target_row = ROWS - 1 if down else 0
    vmove(target_row, dodge=True)
    down = not down
last_z3_row = current_row

# --- Zone 4: zigzag again, cols [Z4_LO, Z4_HI], finishes at top ---
rows_seq = list(range(last_z3_row, -1, -1)) if last_z3_row != 0 else [0]
for i, r in enumerate(rows_seq):
    vmove(r)
    target_col = Z4_HI if current_col == Z4_LO else Z4_LO
    hmove(target_col)

path_d = " ".join(d_parts)
total_distance = acc

def fraction_for_cell(row, col):
    cx, cy = cell_center(row, col)
    best = None
    # pass 1: strict (the segment's fixed coordinate must match this cell's row/col line)
    for seg in segments:
        if seg['kind'] == 'h' and abs(seg['fixed'] - cy) < 0.6:
            lo, hi = min(seg['a'], seg['b']), max(seg['a'], seg['b'])
            if lo - 0.6 <= cx <= hi + 0.6:
                dist = seg['cum'] + abs(cx - seg['a'])
                if best is None or dist < best:
                    best = dist
        elif seg['kind'] == 'v' and abs(seg['fixed'] - cx) < 0.6:
            lo, hi = min(seg['a'], seg['b']), max(seg['a'], seg['b'])
            if lo - 0.6 <= cy <= hi + 0.6:
                dist = seg['cum'] + abs(cy - seg['a'])
                if best is None or dist < best:
                    best = dist
    if best is not None:
        return best / total_distance
    # pass 2 (fallback for the "gap" columns between zone2 and zone3, which the
    # route only crosses once via the top-row connector): credit the cell to
    # that connector's pass-by, so nothing is left permanently uneaten.
    for seg in segments:
        if seg['kind'] == 'h':
            lo, hi = min(seg['a'], seg['b']), max(seg['a'], seg['b'])
            if lo - 0.6 <= cx <= hi + 0.6:
                dist = seg['cum'] + abs(cx - seg['a'])
                if best is None or dist < best:
                    best = dist
    return None if best is None else best / total_distance

missing = [(row, col) for row in range(ROWS) for col in range(COLS) if fraction_for_cell(row, col) is None]
print("total_distance", total_distance, "path parts", len(d_parts), "segments", len(segments))
print("missing cells:", len(missing), missing[:30])
print("last_z3_row", last_z3_row, "ends at row/col", current_row, current_col)

# ============================================================
# 3) PELLETS
# ============================================================
LEVEL_R = {0: 0, 1: 1.6, 2: 2.3, 3: 3.0, 4: 3.7}
LEVEL_CLASS = {0: "lv0", 1: "lv1", 2: "lv2", 3: "lv3", 4: "lv4"}

pellet_svgs = []
pellet_events = []
total_score = 0
for row in range(ROWS):
    for col in range(COLS):
        lvl = levels_grid[row][col]
        total_score += lvl
        cx, cy = cell_center(row, col)
        t1 = fraction_for_cell(row, col)
        if lvl == 0:
            pellet_svgs.append(f'<circle class="pellet lv0" cx="{cx:.1f}" cy="{cy:.1f}" r="1"/>')
            continue
        pellet_events.append((t1, lvl))
        t2 = min(1.0, t1 + EPS)
        if t1 <= 0.0:
            key_times, values = f"0;{fmt(t2)};1", "0;1;1"
        else:
            key_times, values = f"0;{fmt(t1)};{fmt(t2)};1", "1;1;0;0"
        rr = LEVEL_R[lvl]
        pellet_svgs.append(
            f'<circle class="pellet {LEVEL_CLASS[lvl]}" cx="{cx:.1f}" cy="{cy:.1f}" r="{rr}">'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
            f'dur="{TOTAL_DUR}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>'
            f'</circle>'
        )

# ============================================================
# 4) SCORE COUNTER — evenly spaced time checkpoints
# ============================================================
NUM_CHECKPOINTS = 8
pellet_events.sort()
boundaries = [i / NUM_CHECKPOINTS for i in range(NUM_CHECKPOINTS + 1)]

def score_at(fraction):
    return sum(lvl for t, lvl in pellet_events if t <= fraction)

checkpoint_scores = [score_at(b) for b in boundaries]
FLASH = 0.02

score_texts = []
n = NUM_CHECKPOINTS
for i in range(n):
    start, end = boundaries[i], boundaries[i + 1]
    label = checkpoint_scores[i]
    is_last = (i == n - 1)
    end_main = max(start + EPS * 2, end - FLASH) if is_last else end
    if start <= 0.0:
        kt = [0.0, end_main - EPS, end_main, 1.0]
        vals = [1, 1, 0, 0]
    else:
        kt = [0.0, start, start + EPS, end_main - EPS, end_main, 1.0]
        vals = [0, 0, 1, 1, 0, 0]
    kt_str = ";".join(fmt(x) for x in kt)
    val_str = ";".join(str(v) for v in vals)
    score_texts.append(
        f'<text class="score-text" x="{MARGIN_X}" y="{FOOTER_Y}" opacity="0">'
        f'<tspan class="score-prefix">$ </tspan>score: {label}'
        f'<animate attributeName="opacity" values="{val_str}" keyTimes="{kt_str}" '
        f'dur="{TOTAL_DUR}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>'
        f'</text>'
    )

fstart = max(0.0, 1.0 - FLASH)
kt = [0.0, fstart, fstart + EPS, 1.0]
vals = [0, 0, 1, 1]
kt_str = ";".join(fmt(x) for x in kt)
val_str = ";".join(str(v) for v in vals)
score_texts.append(
    f'<text class="score-text score-final" x="{MARGIN_X}" y="{FOOTER_Y}" opacity="0">'
    f'<tspan class="score-prefix">$ </tspan>score: {total_score} &#10022;'
    f'<animate attributeName="opacity" values="{val_str}" keyTimes="{kt_str}" '
    f'dur="{TOTAL_DUR}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>'
    f'</text>'
)

# ============================================================
# 5) ASSEMBLE FULL SVG — palette matched to the terminal-style card
#    (bg gradient #0d1117→#111827, border #30363d, accent #58a6ff,
#    text #c9d1d9 / muted #8b949e, same monospace stack). Fixed dark
#    theme (no @media toggle), same as the terminal SVG it pairs with.
# ============================================================
pacman_r = 6.2
HEADER_H = 40

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {VIEW_W} {VIEW_H}" width="100%" role="img" aria-label="Pac-Man scripted route animation eating a GitHub contribution graph and dodging a ghost">
<defs>
  <path id="pacRouteV5" d="{path_d}"/>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0d1117"/>
    <stop offset="100%" stop-color="#111827"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: "SFMono-Regular", "Cascadia Code", "Roboto Mono", Consolas, monospace; }}
  .title {{ fill: #8b949e; font-size: 13px; letter-spacing: 0.5px; text-anchor: middle; }}
  .score-prefix {{ fill: #58a6ff; font-weight: 600; }}
  .score-text {{ fill: #c9d1d9; font-size: 13px; font-weight: 600; }}
  .score-final {{ fill: #58a6ff; }}
  .card {{ fill: url(#bg); stroke: #30363d; stroke-width: 1; }}
  .header {{ fill: #161b22; }}
  .header-rule {{ stroke: #30363d; stroke-width: 1; }}
  .pellet.lv0 {{ fill: #30363d; }}
  .pellet.lv1 {{ fill: #234a6e; }}
  .pellet.lv2 {{ fill: #2f6feb; }}
  .pellet.lv3 {{ fill: #58a6ff; }}
  .pellet.lv4 {{ fill: #a5d6ff; }}
  .pac-body {{ fill: #ffd23f; stroke: rgba(0,0,0,0.4); stroke-width: 0.6; }}
  .pac-mouth {{ fill: #0d1117; }}
  .pac-eye {{ fill: rgba(0,0,0,0.6); }}
  .ghost-body {{ fill: #58a6ff; opacity: 0.9; }}
  .ghost-eye {{ fill: #0d1117; }}
  .ghost-pupil {{ fill: #c9d1d9; }}
</style>

<rect class="card" x="1" y="1" width="{VIEW_W-2}" height="{VIEW_H-2}" rx="14"/>
<rect class="header" x="1" y="1" width="{VIEW_W-2}" height="{HEADER_H-1}" rx="14"/>
<rect class="header" x="1" y="{HEADER_H-16}" width="{VIEW_W-2}" height="16"/>
<line class="header-rule" x1="1" y1="{HEADER_H}" x2="{VIEW_W-1}" y2="{HEADER_H}"/>

<circle cx="22" cy="20" r="5" fill="#ff5f56"/>
<circle cx="40" cy="20" r="5" fill="#ffbd2e"/>
<circle cx="58" cy="20" r="5" fill="#27c93f"/>
<text class="title" x="{VIEW_W/2:.0f}" y="24">pac-man &#215; github</text>

<g class="pellets">
{chr(10).join(pellet_svgs)}
</g>

<g class="ghost">
  <g transform="translate(0,0)">
    <path class="ghost-body" d="M -6,2 a6,6 0 1 1 12,0 v6 l-2,-2 l-2,2 l-2,-2 l-2,2 l-2,-2 l-2,2 Z"/>
    <circle class="ghost-eye" cx="-2.6" cy="0.5" r="1.7"/>
    <circle class="ghost-eye" cx="2.6" cy="0.5" r="1.7"/>
    <circle class="ghost-pupil" cx="-2.3" cy="0.7" r="0.8"/>
    <circle class="ghost-pupil" cx="2.9" cy="0.7" r="0.8"/>
    <animateTransform attributeName="transform" type="translate"
      values="{ghost_x_lo:.1f},{ghost_y:.1f}; {ghost_x_hi:.1f},{ghost_y:.1f}; {ghost_x_lo:.1f},{ghost_y:.1f}"
      keyTimes="0;0.5;1" dur="{GHOST_DUR}s" begin="0s" repeatCount="indefinite" additive="sum"/>
    <animateTransform attributeName="transform" type="translate"
      values="0,0; 0,-2; 0,0; 0,2; 0,0" keyTimes="0;0.25;0.5;0.75;1"
      dur="0.9s" begin="0s" repeatCount="indefinite" additive="sum"/>
  </g>
</g>

<g class="pacman">
  <circle class="pac-body" r="{pacman_r}"/>
  <circle class="pac-eye" cx="1.4" cy="-3.6" r="0.9"/>
  <path class="pac-mouth" d="M 0,0 L {pacman_r+1},0 L {pacman_r+1},0 Z">
    <animate attributeName="d"
      values="M 0,0 L {pacman_r+1},-0.3 L {pacman_r+1},0.3 Z;
              M 0,0 L {pacman_r+1},-{pacman_r*0.95:.1f} L {pacman_r+1},{pacman_r*0.95:.1f} Z;
              M 0,0 L {pacman_r+1},-0.3 L {pacman_r+1},0.3 Z"
      dur="0.42s" begin="0s" repeatCount="indefinite"/>
  </path>
  <animateMotion dur="{TOTAL_DUR}s" begin="0s" repeatCount="indefinite" rotate="auto" calcMode="linear">
    <mpath href="#pacRouteV5" xlink:href="#pacRouteV5"/>
  </animateMotion>
</g>

{chr(10).join(score_texts)}

</svg>
'''

with open('/home/claude/pacman_v5.svg', 'w') as f:
    f.write(svg)

print("wrote", len(svg), "bytes, total_score", total_score)