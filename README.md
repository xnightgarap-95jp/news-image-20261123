# The World in One Day — Monday 23 November 2026

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/xnightgarap-95jp/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/xnightgarap-95jp/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A one-page newspaper front page for **Monday 23 November 2026** — 35
stories from 6 regions, every one of them happened, or was first
reported, on that day. Built for the
[news-image-20261123](https://make.fun/bounty/news-image-20261123)
bounty on [make.fun](https://make.fun).

## The day in one line

Belgium grounded · Nepal's PM in Delhi · Wall Street's worst week since 2020

## What's on the page

- **3 leads:** Belgium's national strike shuts the country down; Nepal's
  PM Balendra Shah meets Modi in Delhi; Wall Street opens a
  Thanksgiving-shortened week after its worst rout since March 2020.
- **10 more stories:** two die of their wounds in Gaza; Tunisia's
  fuel-tanker drivers walk out; Eisenkot's coalition talks drag on;
  Hyderabad students keep protesting; IG Metall calls 23,000 workers
  out; Alice Huang is linked to a chip-smuggling web; the India–EU
  trade pact is set for 16 December; more Meta protests warned;
  Miliband on closer EU ties; New Zealand fight to save the Test.
- **22 more stories** in the "also" list, a world map with 11 numbered
  pins, a stat strip (429 flights, 59,500 passengers, 14 hours,
  34 delegates, 23,000 strikers, −10.4%), and a **DATE CHECK** box
  naming the big stories from other days that were deliberately left
  out — COP31's collapse, the Las Vegas Grand Prix, India's 720/9,
  the Seattle airport arrests, the Kota crash, and more.

## How it is made

`main.py` (Python 3, standard library only) draws the whole page:
real DejaVu Serif type from `fontdata.py` (glyph bitmaps rendered once
with PIL on this machine — the entry program itself needs no Pillow),
every picture drawn by hand with the primitives in the file, and the
PNG written by hand with `zlib`. No network, no files read except
`fontdata.py`. Two runs write byte-identical output.

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
```

`NEWS.md` is the source document: all 35 stories with their sources,
plus the full DATE CHECK list and the stat strip.

## Sources

EU Today, Tragento, New Kerala, Particle News, The Daily Jagran, Talk
Markets, Yonhap, WAFA, Manassa News, UGTT, 360 Live News, DW, Reuters,
Financial Times, Wall Street Journal, Jagran Josh, European
Parliament, The Guardian, The Times, ESPNcricinfo, NZ Sportswire,
Coin Edition, Finnhub, The Japan Times, South China Morning Post,
The Times of India, CNA, weather.com, AAA. Original drawings.
