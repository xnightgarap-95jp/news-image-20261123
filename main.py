#!/usr/bin/env python3
"""Draw Monday 23 November 2026's world news as one 1024x1024 front page.

Pure Python standard library only: the PNG is written by hand with zlib,
the type is real DejaVu Serif from fontdata.py (bitmaps rendered once
with PIL on the build machine), and every picture is drawn with the
primitives in this file. No network, no files read except fontdata.py.
Deterministic: two runs write byte-identical output.

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""
import base64
import math
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontdata import FONT  # noqa: E402

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 227)
INK = (25, 23, 19)
RED = (158, 27, 27)
BLUE = (29, 78, 121)
GREEN = (46, 107, 52)
GOLD = (176, 124, 16)
GREY = (107, 101, 90)
LIGHT = (232, 226, 208)
SKY = (205, 224, 238)
SEA = (186, 211, 228)
LAND = (233, 220, 186)
LANDLINE = (150, 132, 96)
WHITE = (255, 255, 255)
CREAM2 = (250, 246, 236)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(bg) * (w * h))
        self.clip = (0, 0, w, h)

    def set_clip(self, x0, y0, x1, y1):
        self.clip = (max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1))

    def reset_clip(self):
        self.clip = (0, 0, self.w, self.h)

    def px(self, x, y, c):
        cx0, cy0, cx1, cy1 = self.clip
        if cx0 <= x < cx1 and cy0 <= y < cy1:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        cx0, cy0, cx1, cy1 = self.clip
        x0, y0 = max(x, cx0), max(y, cy0)
        x1, y1 = min(x + w, cx1), min(y + h, cy1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x0, x1, y, c):
        if x0 > x1:
            x0, x1 = x1, x0
        self.fill_rect(x0, y, x1 - x0 + 1, 1, c)

    def vline(self, x, y0, y1, c):
        if y0 > y1:
            y0, y1 = y1, y0
        self.fill_rect(x, y0, 1, y1 - y0 + 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, c, t=1):
        for k in range(t):
            self.hline(x + k, x + w - 1 - k, y + k, c)
            self.hline(x + k, x + w - 1 - k, y + h - 1 - k, c)
            self.vline(x + k, y + k, y + h - 1 - k, c)
            self.vline(x + w - 1 - k, y + k, y + h - 1 - k, c)

    def disc(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - dx, cx + dx, cy + dy, c)

    def ring(self, cx, cy, r, c, t=1):
        for k in range(t):
            rr = r - k
            for a in range(0, 360):
                th = math.radians(a)
                self.px(cx + int(rr * math.cos(th)), cy + int(rr * math.sin(th)), c)

    def poly(self, pts, c):
        """Scanline-filled polygon, pts = [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(math.ceil(xs[i])), int(math.floor(xs[i + 1])), y, c)

    def polyline(self, pts, c):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c)


# ------------------------------------------------------------------- text
def _font_for(weight, size):
    base = 16 if size <= 20 else 40
    return FONT[(weight, base)], size / base


def text_w(s, weight, size):
    font, scale = _font_for(weight, size)
    total = 0.0
    for ch in s:
        g = font.get(ch) or font["?"]
        total += g[0] * scale
    return total


def draw_text(cv, x, y, s, weight, size, color):
    """Draw s with its baseline at y, starting at x. Returns end x."""
    font, scale = _font_for(weight, size)
    cx = int(x)
    y = int(y)
    for ch in s:
        g = font.get(ch) or font["?"]
        adv, w, h, top, b64 = g
        if w and h:
            data = base64.b64decode(b64)
            rb = (w + 7) // 8
            tw = max(1, int(round(w * scale)))
            th = max(1, int(round(h * scale)))
            gy0 = int(round(y + top * scale))
            # Area-coverage sampling: each target pixel covers a small
            # rectangle of source pixels and is inked when at least a
            # quarter of that rectangle is ink. This keeps thin serif
            # strokes from vanishing when a glyph is drawn smaller than
            # the size it was extracted at.
            for ty in range(th):
                sy0 = int(ty / scale)
                sy1 = max(sy0 + 1, int((ty + 1) / scale))
                for tx in range(tw):
                    sx0 = int(tx / scale)
                    sx1 = max(sx0 + 1, int((tx + 1) / scale))
                    ink = tot = 0
                    for syy in range(sy0, min(sy1, h)):
                        row = data[syy * rb:(syy + 1) * rb]
                        for sxx in range(sx0, min(sx1, w)):
                            tot += 1
                            if row[sxx // 8] & (1 << (7 - sxx % 8)):
                                ink += 1
                    if tot and ink * 4 >= tot:
                        cv.px(cx + tx, gy0 + ty, color)
        cx += int(round(adv * scale))
    return cx


def draw_text_c(cv, cx, y, s, weight, size, color):
    draw_text(cv, int(cx - text_w(s, weight, size) / 2), y, s, weight, size, color)


def wrap(s, weight, size, maxw):
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_w(trial, weight, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(cv, x, y, s, weight, size, maxw, leading, color, max_lines=None):
    lines = wrap(s, weight, size, maxw)
    if max_lines:
        lines = lines[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * leading, ln, weight, size, color)
    return y + len(lines) * leading


# ---------------------------------------------------------------- content
STATS = [
    ("429", "flights due at Brussels Airport, most cancelled"),
    ("59,500", "passengers hit by the Brussels cancellations"),
    ("14", "hours of Belgian airspace shutdown, 7am-9pm"),
    ("34", "delegates in Nepal PM Shah's Delhi party"),
    ("23,000", "workers called out by IG Metall on Monday"),
    ("-10.4%", "Nasdaq 100's fall last week, worst since 2020"),
]

REGIONS = "EUROPE 10   \u00b7   ASIA-PACIFIC 10   \u00b7   GLOBAL 8   \u00b7   THE AMERICAS 4   \u00b7   MIDDLE EAST 2   \u00b7   AFRICA 1"

LEADS = [
    dict(kicker="BELGIUM  \u00b7  EUROPE", scene="strike",
         head="A national strike brings Belgium to a standstill",
         body="Air control stopped 7am-9pm; most of 429 Brussels flights "
              "cancelled, about 59,500 passengers hit; trains cut back and "
              "a march filled the capital."),
    dict(kicker="NEPAL - INDIA  \u00b7  ASIA-PACIFIC", scene="talks",
         head="Nepal's new PM sits down with Modi in Delhi",
         body="First bilateral trip abroad since taking office in March; "
              "talks, a joint press conference, a call on President Murmu "
              "and deals on energy and health."),
    dict(kicker="MARKETS  \u00b7  GLOBAL", scene="market",
         head="Wall Street starts a short week after its worst rout since 2020",
         body="Nasdaq 100 fell 10.43% last week, S&P 500 8.61%, chips 17.1% "
              "- the worst week since March 2020. Markets shut Thursday "
              "for Thanksgiving."),
]

MEDIUM = [
    dict(icon="burst", head="Two more die of wounds from the Al-Mawasi strike",
         body="Two Palestinians died on Monday after an Israeli strike west of "
              "Khan Younis; five were wounded at the weekend."),
    dict(icon="truck", head="Tunisian fuel-tanker drivers strike for three days",
         body="Walkout runs Mon-Wed; a 275-dinar bonus offered 17 Nov failed to "
              "call it off - only a signed deal will."),
    dict(icon="parliament", head="Eisenkot's coalition talks with Likud drag on",
         body="Marathon negotiations carried on through Monday as the deadline "
              "to form a government drew closer."),
    dict(icon="book", head="Hyderabad students keep up their protest",
         body="Students demand a faculty member be sacked over alleged casteist "
              "remarks; the protest ran into Monday."),
    dict(icon="factory", head="IG Metall calls 23,000 workers out on Monday",
         body="24-hour strike at 19 firms in the north, incl. Mercedes-Benz and "
              "Meyer Werft; union wants 5%."),
    dict(icon="chip", head="New details link Alice Huang to a chip-smuggling web",
         body="FT ties her to a network moving AI chips to China; the WSJ says "
              "operator Li Ming is on bail in Singapore."),
    dict(icon="flags", head="India-EU trade pact set to be signed on 16 December",
         body="Deal would create the world's biggest free trade zone - a quarter "
              "of humanity, 25% of world GDP."),
    dict(icon="megaphone", head="Youth wing warns of more protests against Meta",
         body="An opposition youth wing vowed further protests after clashes "
              "with police over the platform's role."),
    dict(icon="clock", head="Miliband: closer EU ties give UK a voice in Brussels",
         body="Foreign Secretary backs deeper ties as PM Burnham 'brainstorms' "
              "integration; May says 'move on'."),
    dict(icon="cricket", head="New Zealand fight to save the Test on day five",
         body="Conway 59* and Ravindra 27* resume at 119/2, still 233 short of "
              "making India bat again."),
]

ALSO = [
    "14 \u00b7 Bitcoin traders eye the weekly close - coin slid to $55,106 on Saturday",
    "15 \u00b7 IEA launches its Energy Efficiency market report worldwide",
    "16 \u00b7 US data: S&P flash PMI, Fed's Williams speaks, HPE earnings",
    "17 \u00b7 Brussels march sets off 11am, Gare du Nord to Gare du Midi",
    "18 \u00b7 Charleroi airport: no takeoffs or landings, 7am-9pm",
    "19 \u00b7 Theresa May tells Burnham to \u201cmove on\u201d from Brexit",
    "20 \u00b7 Japan: what happens to foreign spouses when a marriage ends",
    "21 \u00b7 Hong Kong can help connect global bay areas, Paul Chan says",
    "22 \u00b7 McLaren pair hail Las Vegas podium redemption after 2025 DQ",
    "23 \u00b7 Verstappen revels in Russell's misfortune in Las Vegas",
    "24 \u00b7 Prince Harry: UK school life boosted Archie and Lilibet",
    "25 \u00b7 German agency borrows US-style campaigning to boost the left",
    "26 \u00b7 US PCE inflation due Wednesday - the week's big data release",
    "27 \u00b7 Monday is Thanksgiving week's calmest travel day: 81.5m trips",
    "28 \u00b7 East Coast storm exits New England early on Monday morning",
    "29 \u00b7 SCMP view: UK needs real China expertise, not more hawks",
    "30 \u00b7 IG Metall wants 5% pay rise plus job safeguards",
    "31 \u00b7 Nvidia: all chip shipments were legal and authorised",
    "32 \u00b7 Kashmir's saffron fields used as dumping grounds, Mufti says",
    "33 \u00b7 Trump urges Nvidia board to give Huang a second chance",
    "34 \u00b7 IFFI 2026 hosts a BRICS roundtable on film partnerships",
    "35 \u00b7 De Lijn runs about six in ten buses and trams on strike day",
]

DATECHECK = [
    "COP31 collapsed with no deal - Sunday 22 Nov",
    "Las Vegas GP: Verstappen won - Saturday night",
    "India declared 720/9, a record - Sunday 22 Nov",
    "S. Korea education minister resigned - Sun 22 Nov",
    "Indonesia candy factory fire - Saturday 21 Nov",
    "Russian ship Sparta II hit by drones - Sat 21 Nov",
    "ICE arrests at Seattle airport - Saturday 21 Nov",
    "Kota crash kills nine pilgrims - Sunday 22 Nov",
    "Titanic ring sells for \u00a3150,000 - Sat 21 Nov",
    "EU-UK youth mobility deal finalised - Fri 20 Nov",
]

PINS = [
    (1, "Brussels", 4.35, 50.85),
    (2, "Kathmandu", 85.3, 27.7),
    (3, "New York", -74.0, 40.7),
    (4, "Khan Younis", 34.45, 31.35),
    (5, "Tunis", 10.2, 36.8),
    (6, "Jerusalem", 35.2, 31.8),
    (7, "Hyderabad", 78.5, 17.4),
    (8, "Berlin", 13.4, 52.5),
    (9, "Washington", -77.0, 38.9),
    (10, "London", -0.1, 51.5),
    (11, "Wellington", 174.8, -41.3),
]

CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 72), (-95, 80), (-80, 73), (-75, 62),
     (-65, 45), (-75, 35), (-80, 25), (-90, 20), (-97, 16), (-105, 20),
     (-117, 33), (-125, 40), (-125, 49), (-140, 60), (-165, 60)],
    [(-80, 10), (-75, 5), (-60, 0), (-50, -5), (-35, -8), (-40, -20),
     (-48, -28), (-58, -38), (-65, -45), (-70, -52), (-73, -40),
     (-72, -20), (-77, -12), (-80, -3)],
    [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (18, 56), (21, 55), (24, 58), (30, 60), (28, 70), (20, 70),
     (15, 68), (5, 60), (-2, 58), (-10, 50), (-10, 43)],
    [(-17, 15), (-10, 30), (0, 36), (10, 37), (20, 32), (30, 31),
     (35, 28), (43, 12), (51, 11), (48, 0), (40, -10), (35, -18),
     (30, -26), (20, -35), (15, -30), (12, -18), (9, -1), (9, 4),
     (-8, 5), (-13, 8), (-17, 15)],
    [(30, 60), (40, 68), (50, 70), (60, 70), (70, 72), (80, 73), (90, 75),
     (100, 77), (110, 76), (120, 73), (130, 72), (140, 72), (150, 70),
     (160, 66), (162, 60), (158, 52), (142, 50), (140, 40), (135, 35),
     (130, 33), (127, 35), (122, 38), (120, 30), (115, 22), (108, 18),
     (105, 10), (100, 8), (97, 16), (92, 21), (88, 22), (80, 13), (77, 8),
     (72, 20), (66, 25), (60, 25), (57, 26), (52, 28), (48, 30), (43, 12),
     (40, 15), (38, 20), (35, 28), (30, 36), (28, 45), (30, 55)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (129, -32), (132, -32),
     (136, -35), (140, -38), (145, -38), (150, -37), (153, -32), (153, -27),
     (150, -22), (146, -19), (142, -11), (137, -12), (132, -12), (126, -14),
     (122, -17), (118, -20)],
]


# ------------------------------------------------------------------ scenes
def scene_strike(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + h - 26, w, 26, (120, 118, 110))          # tarmac
    cv.fill_rect(x, y + h - 26, w, 3, WHITE)                     # runway line
    for i in range(0, w, 26):                                    # dashes
        cv.fill_rect(x + i + 4, y + h - 14, 14, 2, (220, 220, 210))
    # grounded plane, nose right
    px, py = x + 30, y + 34
    cv.poly([(px, py), (px + 150, py), (px + 185, py + 10), (px + 150, py + 20),
             (px, py + 20)], (235, 235, 228))                    # fuselage
    cv.poly([(px + 55, py + 2), (px + 105, py + 2), (px + 88, py + 20),
             (px + 62, py + 20)], (200, 30, 30))                 # wing
    cv.poly([(px + 8, py - 14), (px + 26, py - 14), (px + 30, py + 2),
             (px + 12, py + 2)], (200, 30, 30))                  # tail fin
    for wx in (px + 40, px + 90, px + 135, px + 168):            # windows
        cv.fill_rect(wx, py + 6, 8, 5, BLUE)
    cv.fill_rect(px + 45, py + 20, 6, 12, INK)                   # wheels
    cv.fill_rect(px + 130, py + 20, 6, 12, INK)
    # red barrier cross over the plane
    cv.line(px + 150, py - 22, px + 205, py + 32, RED)
    cv.line(px + 205, py - 22, px + 150, py + 32, RED)
    # picket signs
    for i, sx in enumerate((x + 12, x + 62, x + 232, x + 282)):
        cv.vline(sx + 8, y + h - 52, y + h - 28, INK)
        cv.fill_rect(sx, y + h - 66, 26, 14, WHITE)
        cv.rect(sx, y + h - 66, 26, 14, INK)
    draw_text(cv, x + 16, y + h - 55, "NO", "b", 9, RED)
    draw_text(cv, x + 66, y + h - 55, "NO", "b", 9, RED)
    draw_text(cv, x + 236, y + h - 55, "NO", "b", 9, RED)
    draw_text(cv, x + 286, y + h - 55, "NO", "b", 9, RED)


def scene_talks(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (222, 232, 220))
    cv.fill_rect(x, y + h - 30, w, 30, (168, 140, 100))          # floor
    # Nepal flag (crimson double pennon, simplified)
    cv.vline(x + 52, y + 12, y + h - 12, INK)
    cv.poly([(x + 52, y + 14), (x + 100, y + 24), (x + 52, y + 34)], (220, 20, 60))
    cv.poly([(x + 52, y + 36), (x + 86, y + 44), (x + 52, y + 52)], (220, 20, 60))
    # India flag (saffron / white / green + wheel)
    cv.vline(x + 236, y + 12, y + h - 12, INK)
    cv.fill_rect(x + 236, y + 14, 64, 12, (255, 153, 51))
    cv.fill_rect(x + 236, y + 26, 64, 12, WHITE)
    cv.fill_rect(x + 236, y + 38, 64, 12, (19, 136, 8))
    cv.ring(x + 268, y + 32, 5, BLUE)
    # table with documents
    cv.fill_rect(x + 118, y + 58, 116, 8, (122, 84, 48))
    cv.fill_rect(x + 126, y + 66, 8, 10, (122, 84, 48))
    cv.fill_rect(x + 218, y + 66, 8, 10, (122, 84, 48))
    cv.poly([(x + 140, y + 46), (x + 168, y + 46), (x + 176, y + 58),
             (x + 140, y + 58)], WHITE)
    cv.poly([(x + 182, y + 46), (x + 210, y + 46), (x + 218, y + 58),
             (x + 182, y + 58)], WHITE)
    cv.line(x + 144, y + 51, x + 164, y + 51, GREY)
    cv.line(x + 186, y + 51, x + 206, y + 51, GREY)
    # handshake: two forearms meeting over the table
    cv.line(x + 140, y + 56, x + 170, y + 42, INK)
    cv.line(x + 142, y + 58, x + 172, y + 44, INK)
    cv.line(x + 216, y + 56, x + 186, y + 42, INK)
    cv.line(x + 214, y + 58, x + 184, y + 44, INK)
    cv.disc(x + 178, y + 42, 6, (232, 196, 150))
    cv.ring(x + 178, y + 42, 6, INK)


def scene_market(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (238, 232, 220))
    gx, gy, gw, gh = x + 26, y + 12, w - 52, h - 34
    cv.fill_rect(gx, gy, gw, gh, WHITE)
    cv.rect(gx, gy, gw, gh, INK)
    for i in range(1, 4):                                        # gridlines
        cv.hline(gx + 1, gx + gw - 2, gy + i * gh // 4, LIGHT)
    # falling line with arrow
    pts = [(gx + 8, gy + 10), (gx + 40, gy + 16), (gx + 72, gy + 14),
           (gx + 104, gy + 30), (gx + 136, gy + 28), (gx + 168, gy + 44),
           (gx + 200, gy + 42), (gx + 232, gy + 58), (gx + gw - 8, gy + 62)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED)
        cv.line(pts[i][0], pts[i][1] + 1, pts[i + 1][0], pts[i + 1][1] + 1, RED)
    ex, ey = pts[-1]
    cv.poly([(ex, ey), (ex - 12, ey - 8), (ex - 12, ey + 8)], RED)
    # candlesticks
    for i, (cx, top, bot) in enumerate([(gx + 30, 18, 34), (gx + 90, 22, 44),
                                        (gx + 150, 36, 56), (gx + 210, 50, 66)]):
        cv.vline(cx, gy + top, gy + bot, RED)
        cv.fill_rect(cx - 4, gy + top + 4, 9, bot - top - 8, RED)
    draw_text(cv, gx + 8, y + h - 8, "-10.4%  NASDAQ 100", "b", 13, RED)


def draw_icon(cv, x, y, kind):
    """40x40 pictogram at (x, y)."""
    cv.fill_rect(x, y, 40, 40, CREAM2)
    cv.rect(x, y, 40, 40, LANDLINE)
    if kind == "burst":
        for a in range(0, 360, 30):
            th = math.radians(a)
            cv.line(x + 20, y + 20, x + 20 + int(15 * math.cos(th)),
                    y + 20 + int(15 * math.sin(th)), RED)
        cv.disc(x + 20, y + 20, 6, GOLD)
    elif kind == "truck":
        cv.fill_rect(x + 5, y + 12, 20, 12, BLUE)
        cv.fill_rect(x + 25, y + 16, 10, 8, RED)
        cv.disc(x + 11, y + 28, 4, INK)
        cv.disc(x + 29, y + 28, 4, INK)
        cv.fill_rect(x + 5, y + 8, 20, 3, (200, 200, 190))
    elif kind == "parliament":
        cv.poly([(x + 6, y + 18), (x + 20, y + 8), (x + 34, y + 18)], RED)
        cv.fill_rect(x + 6, y + 18, 28, 14, LIGHT)
        for cx in (x + 11, x + 18, x + 25):
            cv.vline(cx, y + 20, y + 30, INK)
        cv.fill_rect(x + 4, y + 32, 32, 3, INK)
    elif kind == "book":
        cv.poly([(x + 6, y + 12), (x + 20, y + 17), (x + 20, y + 30),
                 (x + 6, y + 25)], WHITE)
        cv.poly([(x + 34, y + 12), (x + 20, y + 17), (x + 20, y + 30),
                 (x + 34, y + 25)], WHITE)
        cv.line(x + 20, y + 17, x + 20, y + 30, INK)
        cv.poly([(x + 8, y + 8), (x + 20, y + 3), (x + 32, y + 8),
                 (x + 20, y + 13)], INK)
    elif kind == "factory":
        cv.fill_rect(x + 6, y + 18, 28, 14, GREY)
        cv.fill_rect(x + 8, y + 8, 5, 10, INK)
        cv.fill_rect(x + 16, y + 5, 5, 13, INK)
        cv.poly([(x + 6, y + 18), (x + 20, y + 10), (x + 34, y + 18)], RED)
        cv.disc(x + 28, y + 26, 4, GOLD)
    elif kind == "chip":
        cv.fill_rect(x + 12, y + 12, 16, 16, INK)
        cv.fill_rect(x + 16, y + 16, 8, 8, GREEN)
        for i in range(3):
            cv.vline(x + 15 + i * 5, y + 6, y + 12, INK)
            cv.vline(x + 15 + i * 5, y + 28, y + 34, INK)
            cv.hline(x + 6, x + 12, y + 15 + i * 5, INK)
            cv.hline(x + 28, x + 34, y + 15 + i * 5, INK)
    elif kind == "flags":
        cv.fill_rect(x + 6, y + 10, 12, 16, (255, 153, 51))
        cv.fill_rect(x + 6, y + 16, 12, 5, WHITE)
        cv.fill_rect(x + 6, y + 21, 12, 5, (19, 136, 8))
        cv.fill_rect(x + 22, y + 10, 12, 16, BLUE)
        for i in range(5):
            cv.disc(x + 25 + (i % 3) * 4, y + 14 + (i // 3) * 5, 1, GOLD)
    elif kind == "megaphone":
        cv.poly([(x + 8, y + 16), (x + 28, y + 8), (x + 28, y + 30),
                 (x + 8, y + 24)], RED)
        cv.fill_rect(x + 5, y + 16, 4, 8, INK)
        cv.line(x + 30, y + 10, x + 34, y + 6, INK)
        cv.line(x + 30, y + 19, x + 35, y + 19, INK)
        cv.line(x + 30, y + 28, x + 34, y + 32, INK)
    elif kind == "clock":
        cv.fill_rect(x + 16, y + 4, 8, 30, INK)
        cv.poly([(x + 16, y + 4), (x + 20, y + 0), (x + 24, y + 4)], INK)
        cv.disc(x + 20, y + 14, 7, WHITE)
        cv.ring(x + 20, y + 14, 7, INK)
        cv.line(x + 20, y + 14, x + 20, y + 9, INK)
        cv.line(x + 20, y + 14, x + 24, y + 15, INK)
        cv.fill_rect(x + 6, y + 34, 28, 3, INK)
    elif kind == "cricket":
        cv.line(x + 10, y + 30, x + 26, y + 10, INK)
        cv.line(x + 12, y + 32, x + 28, y + 12, INK)
        cv.fill_rect(x + 24, y + 6, 8, 6, (180, 140, 80))
        cv.disc(x + 32, y + 28, 4, RED)
        cv.line(x + 6, y + 34, x + 20, y + 34, GREEN)


# ------------------------------------------------------------------- page
def draw_page(cv):
    cv.fill_rect(0, 0, W, H, PAPER)
    cv.rect(5, 5, W - 10, H - 10, INK, 2)
    cv.rect(9, 9, W - 18, H - 18, INK, 1)

    # ---- masthead
    draw_text_c(cv, 512, 62, "THE WORLD IN ONE DAY", "b", 46, INK)
    cv.hline(60, 964, 72, INK)
    cv.hline(60, 964, 75, INK)
    draw_text_c(cv, 512, 98, "MONDAY 23 NOVEMBER 2026", "b", 17, RED)
    draw_text(cv, 512 + text_w("MONDAY 23 NOVEMBER 2026", "b", 17) / 2 + 12,
              98, " \u00b7  35 STORIES  \u00b7  SIX REGIONS", "r", 13, INK)

    # ---- stat strip
    sy, sh = 110, 42
    cv.fill_rect(14, sy, 996, sh, INK)
    cw = 996 // 6
    for i, (num, label) in enumerate(STATS):
        x = 14 + i * cw
        if i:
            cv.vline(x, sy + 5, sy + sh - 5, (90, 85, 75))
        draw_text_c(cv, x + cw // 2, sy + 18, num, "b", 19, (255, 214, 130))
        lines = wrap(label, "r", 10, cw - 16)
        for j, ln in enumerate(lines[:2]):
            draw_text_c(cv, x + cw // 2, sy + 29 + j * 11, ln, "r", 10, WHITE)

    # ---- region bar
    draw_text_c(cv, 512, 166, REGIONS, "b", 12, BLUE)
    cv.hline(14, 1010, 174, INK)

    # ---- leads
    ly, lcol, lgap = 182, 322, 15
    for i, lead in enumerate(LEADS):
        x = 14 + i * (lcol + lgap)
        draw_text(cv, x, ly + 12, lead["kicker"], "b", 11, RED)
        sc_y = ly + 20
        cv.set_clip(x, sc_y, x + lcol, sc_y + 76)
        if lead["scene"] == "strike":
            scene_strike(cv, x, sc_y, lcol, 76)
        elif lead["scene"] == "talks":
            scene_talks(cv, x, sc_y, lcol, 76)
        else:
            scene_market(cv, x, sc_y, lcol, 76)
        cv.reset_clip()
        cv.rect(x, sc_y, lcol, 76, INK)
        hy = sc_y + 76 + 18
        hy = para(cv, x, hy, lead["head"], "b", 18, lcol, 20, INK, max_lines=2)
        para(cv, x, hy + 13, lead["body"], "r", 11.5, lcol, 13, INK, max_lines=3)
        if i < 2:
            cv.vline(x + lcol + 7, ly, ly + 200, GREY)
    cv.hline(14, 1010, 392, INK)

    # ---- medium stories
    my = 400
    draw_text(cv, 14, my + 13, "THE DAY IN BRIEF", "b", 14, INK)
    draw_text(cv, 1010 - text_w("10 MORE STORIES FROM MONDAY", "r", 11),
              my + 13, "10 MORE STORIES FROM MONDAY", "r", 11, GREY)
    my += 22
    row_h = 46
    for i, m in enumerate(MEDIUM):
        col = i % 2
        row = i // 2
        x = 14 + col * 502
        y = my + row * row_h
        draw_icon(cv, x, y + 2, m["icon"])
        tx = x + 48
        tw = 492 - 48
        draw_text(cv, tx, y + 13, m["head"], "b", 13.5, INK)
        para(cv, tx, y + 26, m["body"], "r", 11, tw, 13, GREY, max_lines=2)
    my += 5 * row_h + 4
    cv.hline(14, 1010, my, INK)

    # ---- also list
    ay = my + 8
    draw_text(cv, 14, ay + 12, "ALSO ON MONDAY  \u2014  22 MORE", "b", 13, INK)
    ay += 20
    for i, item in enumerate(ALSO):
        col = i // 11
        row = i % 11
        x = 14 + col * 502
        draw_text(cv, x, ay + row * 13 + 11, item, "r", 10.5, INK)
    ay += 11 * 13 + 6
    cv.hline(14, 1010, ay, INK)

    # ---- bottom: map + date check
    by = ay + 8
    bh = 1004 - by
    # map panel
    mx, mw = 14, 634
    draw_text(cv, mx, by + 13, "WHERE IT HAPPENED", "b", 12, INK)
    map_x0, map_y0, map_w, map_h = mx + 4, by + 20, mw - 8, bh - 48
    cv.fill_rect(map_x0, map_y0, map_w, map_h, SEA)
    cv.rect(map_x0, map_y0, map_w, map_h, INK)

    def to_xy(lon, lat):
        px = map_x0 + (lon + 170) / 360.0 * map_w
        py = map_y0 + (75 - lat) / 130.0 * map_h
        return int(px), int(py)

    cv.set_clip(map_x0, map_y0, map_x0 + map_w, map_y0 + map_h)
    for cont in CONTINENTS:
        cv.poly([to_xy(lon, lat) for lon, lat in cont], LAND)
        cv.polyline([to_xy(lon, lat) for lon, lat in cont] + [to_xy(*cont[0])],
                    LANDLINE)
    # pins with leader lines to numbered badges (offsets spread the
    # crowded European pins apart so no two badges collide)
    badge_off = {1: (-15, -13), 2: (10, -12), 3: (-16, -10), 4: (12, 10),
                 5: (-13, 12), 6: (14, -8), 7: (12, 9), 8: (3, -17),
                 9: (-14, 9), 10: (-17, -12), 11: (-10, -14)}
    for num, name, lon, lat in PINS:
        px, py = to_xy(lon, lat)
        ox, oy = badge_off[num]
        bx, byy = px + ox, py + oy
        cv.line(px, py, bx, byy, RED)
        cv.disc(px, py, 3, RED)
        cv.ring(px, py, 3, WHITE)
        cv.disc(bx, byy, 7, RED)
        cv.ring(bx, byy, 7, WHITE)
        label = str(num)
        draw_text(cv, bx - int(text_w(label, "b", 9) / 2), byy + 3,
                  label, "b", 9, WHITE)
    cv.reset_clip()
    legend = ("1 Brussels  2 Kathmandu  3 New York  4 Khan Younis  5 Tunis  "
              "6 Jerusalem  7 Hyderabad  8 Berlin  9 Washington  "
              "10 London  11 Wellington")
    for j, ln in enumerate(wrap(legend, "r", 10, mw - 8)):
        draw_text(cv, mx + 4, by + bh - 22 + j * 12, ln, "r", 10, INK)

    # date-check panel
    dx, dw = 656, 354
    cv.vline(648, by, 1004, GREY)
    draw_text(cv, dx, by + 13, "NOT MONDAY'S NEWS \u2014 LEFT OUT", "b", 12, RED)
    dy = by + 26
    for item in DATECHECK:
        draw_text(cv, dx, dy, "\u2713  " + item, "r", 9.5, INK)
        dy += 11.5
    draw_text(cv, dx, dy + 3, "Full list with sources: NEWS.md", "r", 10, GREY)

    # ---- footer
    draw_text_c(cv, 512, 1012,
                "Drawn by hand in code  \u00b7  Sources in NEWS.md  \u00b7  "
                "make.fun \u2014 news-image-20261123",
                "r", 10, GREY)


# --------------------------------------------------------------------- png
def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw.extend(cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3])
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_page(cv)
    path = os.path.join(outdir, "entry.png")
    size = write_png(cv, path)
    print(f"wrote {path} {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
