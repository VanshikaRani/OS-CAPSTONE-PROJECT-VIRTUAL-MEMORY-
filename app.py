#!/usr/bin/env python3
"""Virtual Memory Lab: an integrated paging and page-replacement learning app."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT
OUTPUT_DIR = ROOT / "outputs"
LOG_DIR = ROOT
for folder in (OUTPUT_DIR,):
    folder.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_DIR / "activity.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class Step:
    index: int
    page: int
    frames: list[int | None]
    result: str
    evicted: int | None


@dataclass
class Simulation:
    algorithm: str
    reference: list[int]
    frame_count: int
    steps: list[Step]
    page_faults: int
    hits: int
    fault_rate: float


def parse_reference(value: str | Iterable[int]) -> list[int]:
    try:
        pages = [int(x) for x in value.split(",")] if isinstance(value, str) else [int(x) for x in value]
    except (ValueError, TypeError) as exc:
        raise ValueError("Page reference must be comma-separated whole numbers (example: 7,0,1).") from exc
    if not pages:
        raise ValueError("Enter at least one page reference.")
    if any(p < 0 for p in pages):
        raise ValueError("Page numbers cannot be negative.")
    return pages


def simulate(reference: str | Iterable[int], frame_count: int, algorithm: str) -> Simulation:
    pages = parse_reference(reference)
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count < 1 or frame_count > 64:
        raise ValueError("Frame count must be an integer from 1 to 64.")
    algo = algorithm.strip().upper()
    if algo not in {"FIFO", "LRU", "OPTIMAL"}:
        raise ValueError("Algorithm must be FIFO, LRU, or OPTIMAL.")
    frames: list[int | None] = [None] * frame_count
    loaded_at: dict[int, int] = {}
    last_used: dict[int, int] = {}
    steps: list[Step] = []
    faults = 0
    for i, page in enumerate(pages):
        evicted = None
        if page in frames:
            result = "HIT"
        else:
            faults += 1
            result = "FAULT"
            if None in frames:
                slot = frames.index(None)
            else:
                resident = [int(p) for p in frames]
                if algo == "FIFO":
                    victim = min(resident, key=lambda p: loaded_at[p])
                elif algo == "LRU":
                    victim = min(resident, key=lambda p: last_used[p])
                else:
                    def next_use(p: int) -> float:
                        try:
                            return pages.index(p, i + 1)
                        except ValueError:
                            return float("inf")
                    victim = max(resident, key=next_use)
                slot = frames.index(victim)
                evicted = victim
                loaded_at.pop(victim, None)
                last_used.pop(victim, None)
            frames[slot] = page
            loaded_at[page] = i
        last_used[page] = i
        steps.append(Step(i + 1, page, frames.copy(), result, evicted))
    return Simulation(algo, pages, frame_count, steps, faults, len(pages) - faults, faults / len(pages))


def working_set(reference: str | Iterable[int], window: int) -> list[dict[str, int]]:
    pages = parse_reference(reference)
    if not isinstance(window, int) or isinstance(window, bool) or window < 1 or window > len(pages):
        raise ValueError(f"Window must be between 1 and {len(pages)}.")
    return [{"step": i + 1, "page": page,
             "working_set_size": len(set(pages[max(0, i-window+1):i+1]))}
            for i, page in enumerate(pages)]


def compare(reference: str | Iterable[int], frame_count: int) -> list[Simulation]:
    return [simulate(reference, frame_count, algo) for algo in ("FIFO", "LRU", "OPTIMAL")]


def trace_text(sim: Simulation) -> str:
    headers = [f"Virtual Memory Lab — {sim.algorithm}",
               f"Reference string: {', '.join(map(str, sim.reference))}",
               f"Frames: {sim.frame_count}", "", "Step | Page | " + " | ".join(f"F{i+1}" for i in range(sim.frame_count)) + " | Result | Evicted",
               "-" * (37 + sim.frame_count * 6)]
    for s in sim.steps:
        cells = ["-" if p is None else str(p) for p in s.frames]
        headers.append(f"{s.index:>4} | {s.page:>4} | " + " | ".join(f"{x:>2}" for x in cells) +
                       f" | {s.result:<5} | {s.evicted if s.evicted is not None else '-'}")
    headers += ["", f"Page faults: {sim.page_faults}", f"Hits: {sim.hits}",
                f"Fault rate: {sim.fault_rate:.1%}", f"Hit rate: {1-sim.fault_rate:.1%}"]
    return "\n".join(headers) + "\n"


def save_simulation(sim: Simulation, stem: str = "latest") -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    txt, csv_path = OUTPUT_DIR / f"{stem}_{sim.algorithm.lower()}.txt", OUTPUT_DIR / f"{stem}_{sim.algorithm.lower()}.csv"
    txt.write_text(trace_text(sim), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "page", *[f"frame_{i+1}" for i in range(sim.frame_count)], "result", "evicted"])
        for s in sim.steps:
            writer.writerow([s.index, s.page, *["" if p is None else p for p in s.frames], s.result,
                             "" if s.evicted is None else s.evicted])
    return txt, csv_path


def save_comparison(sims: list[Simulation], stem: str = "comparison") -> Path:
    path = OUTPUT_DIR / f"{stem}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["algorithm", "frames", "references", "faults", "hits", "fault_rate_percent"])
        for s in sims: writer.writerow([s.algorithm, s.frame_count, len(s.reference), s.page_faults, s.hits, f"{s.fault_rate*100:.2f}"])
    return path


def save_comparison_graph(sims: list[Simulation]) -> Path:
    """Create a dependency-free SVG bar chart for the algorithm comparison."""
    colors = {"FIFO": "#ef8354", "LRU": "#4f9da6", "OPTIMAL": "#55c271"}
    max_faults = max(1, max(s.page_faults for s in sims))
    bars = []
    for i, sim in enumerate(sims):
        y, width = 145 + i * 100, 600 * sim.page_faults / max_faults
        bars.append(f'<text x="58" y="{y+28}" class="label">{sim.algorithm}</text>'
                    f'<rect x="190" y="{y}" width="{width:.1f}" height="42" rx="8" fill="{colors[sim.algorithm]}"/>'
                    f'<text x="{205+width:.1f}" y="{y+28}" class="value">{sim.page_faults} faults</text>'
                    f'<text x="850" y="{y+28}" class="value">{sim.hits} hits · {sim.fault_rate:.1%}</text>')
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="500" viewBox="0 0 1100 500">
<rect width="1100" height="500" rx="22" fill="#0b1220"/><style>.title{font:700 28px Arial;fill:#edf4ff}.sub{font:16px Arial;fill:#9fb1c9}.label{font:700 18px Arial;fill:#dce7f6}.value{font:16px Arial;fill:#dce7f6}</style>
<text x="56" y="58" class="title">Page replacement comparison</text><text x="56" y="91" class="sub">Same reference string and frame count · fewer faults is better</text>''' + "".join(bars) + '''
<text x="56" y="470" class="sub">Optimal uses future knowledge; shown as a theoretical benchmark.</text></svg>'''
    path = OUTPUT_DIR / "comparison_graph.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def save_frame_sweep(reference: str | Iterable[int], max_frames: int = 6) -> Path:
    """Save a line chart of faults by frame count to support memory-pressure demos."""
    pages = parse_reference(reference)
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or not 1 <= max_frames <= 64:
        raise ValueError("Maximum frame count must be an integer from 1 to 64.")
    algos = ("FIFO", "LRU", "OPTIMAL")
    colors = {"FIFO": "#ef8354", "LRU": "#4f9da6", "OPTIMAL": "#55c271"}
    values = {a: [simulate(pages, n, a).page_faults for n in range(1, max_frames+1)] for a in algos}
    high = max(1, max(max(v) for v in values.values()))
    left, top, width, height = 90, 130, 700, 300
    parts = []
    for k in range(5):
        y = top + height*k/4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+width}" y2="{y:.1f}" stroke="#28394f"/>')
    for a in algos:
        pts=[]
        for j, faults in enumerate(values[a]):
            x=left+width*j/max(1,max_frames-1); y=top+height-height*faults/high
            pts.append(f"{x:.1f},{y:.1f}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{colors[a]}"/>')
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[a]}" stroke-width="4"/>')
    for j in range(max_frames):
        x=left+width*j/max(1,max_frames-1)
        parts.append(f'<text x="{x:.1f}" y="{top+height+28}" text-anchor="middle" class="tick">{j+1}</text>')
    for i,a in enumerate(algos):
        parts.append(f'<circle cx="850" cy="{155+i*40}" r="6" fill="{colors[a]}"/><text x="868" y="{161+i*40}" class="legend">{a}</text>')
    svg='''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="520" viewBox="0 0 1000 520"><rect width="1000" height="520" rx="22" fill="#0b1220"/><style>.title{font:700 27px Arial;fill:#edf4ff}.sub,.legend{font:16px Arial;fill:#9fb1c9}.tick{font:14px Arial;fill:#cbd8e9}</style>
<text x="54" y="56" class="title">Frame count vs page faults</text><text x="54" y="88" class="sub">More faults indicate greater paging pressure for this reference string.</text>''' + "".join(parts) + '''<text x="385" y="500" class="sub">Frames allocated</text></svg>'''
    path=OUTPUT_DIR / "frame_sensitivity.svg"
    path.write_text(svg,encoding="utf-8")
    return path


def print_comparison(sims: list[Simulation]) -> None:
    print("\nAlgorithm  Faults  Hits  Fault rate")
    print("---------  ------  ----  ----------")
    for s in sims: print(f"{s.algorithm:<9}  {s.page_faults:>6}  {s.hits:>4}  {s.fault_rate:>9.1%}")
    best = min(sims, key=lambda s: s.page_faults)
    print(f"\nLowest fault count for this dataset: {best.algorithm} ({best.page_faults} faults).")


def get_input(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(prompt + suffix + ": ").strip()
    return value or (default if default is not None else "")


def run_menu() -> None:
    print("\n=== VIRTUAL MEMORY LAB ===")
    print("Study paging, replacement algorithms and working-set pressure.\n")
    while True:
        print("1. Simulate page replacement\n2. Compare FIFO, LRU and Optimal\n3. Analyze working set / thrashing\n4. Load sample dataset\n5. Help\n6. Graph faults across frame counts\n0. Exit")
        choice = input("Select: ").strip()
        if choice == "0": print("Goodbye."); return
        if choice == "5":
            print("A page fault means the requested page was absent from all frames. A hit means it was resident.\n"
                  "FIFO evicts the oldest loaded page; LRU evicts the least recently used; Optimal evicts the page\n"
                  "whose next use is farthest away (or never occurs). Optimal is a theoretical benchmark.")
            continue
        if choice == "6":
            reference = get_input("Page references, comma-separated", "7,0,1,2,0,3,0,4,2,3")
            try:
                maximum = int(get_input("Largest frame count to graph (1-64)", "6"))
                graph = save_frame_sweep(reference, maximum)
                print("Frames | FIFO faults | LRU faults | Optimal faults")
                for n in range(1, maximum+1):
                    print(f"{n:>6} | {simulate(reference,n,'FIFO').page_faults:>11} | {simulate(reference,n,'LRU').page_faults:>10} | {simulate(reference,n,'OPTIMAL').page_faults:>14}")
                print(f"Saved {graph.relative_to(ROOT)}")
            except (ValueError, OSError) as exc:
                print(f"Input or file error: {exc}")
            continue
        if choice == "4":
            data = json.loads((DATA_DIR / "sample.json").read_text(encoding="utf-8"))
            reference, count = data["reference"], data["frames"]
            print(f"Loaded sample: {reference} with {count} frames.")
            try:
                sims = compare(reference, count)
                print_comparison(sims)
                for sim in sims:
                    save_simulation(sim, "comparison")
                save_comparison_graph(sims)
                print(f"Saved comparison.csv, comparison_graph.svg, and per-algorithm traces.")
            except (ValueError, OSError) as exc:
                logging.warning("sample run failed: %s", exc)
                print(f"Input or file error: {exc}")
            continue
        elif choice in {"1", "2", "3"}:
            reference = get_input("Page references, comma-separated", "7,0,1,2,0,3,0,4,2,3")
            try: count = int(get_input("Number of frames", "3"))
            except ValueError: print("Please enter a whole-number frame count."); continue
        else: print("Choose 0, 1, 2, 3, 4, or 5."); continue
        try:
            if choice == "3":
                max_window = len(parse_reference(reference))
                try: window = int(get_input(f"Working-set window (1-{max_window})", str(min(4, max_window))))
                except ValueError: print("Window must be a whole number."); continue
                rows = working_set(reference, window)
                print("\nStep | Page | Distinct pages in recent window")
                for row in rows: print(f"{row['step']:>4} | {row['page']:>4} | {row['working_set_size']:>5}")
                print("\nCompare working-set size with available frames. Repeated demand above capacity can indicate thrashing.")
                out = OUTPUT_DIR / "working_set.csv"
                with out.open("w", newline="", encoding="utf-8") as f:
                    w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
                print(f"Saved {out.relative_to(ROOT)}")
            elif choice == "1":
                algo = get_input("Algorithm (FIFO/LRU/OPTIMAL)", "FIFO")
                sim = simulate(reference, count, algo); print("\n" + trace_text(sim))
                for p in save_simulation(sim): print(f"Saved {p.relative_to(ROOT)}")
            elif choice == "2":
                sims = compare(reference, count); print_comparison(sims)
                for sim in sims: save_simulation(sim, "comparison")
                save_comparison_graph(sims)
                print("Saved comparison.csv, comparison_graph.svg, and per-algorithm traces.")
            logging.info("menu choice=%s references=%s frames=%s", choice, reference, count)
        except (ValueError, OSError) as exc:
            logging.warning("operation rejected: %s", exc); print(f"Input or file error: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Virtual Memory Lab: simulate and compare page replacement.")
    parser.add_argument("--reference", help="Comma-separated page references")
    parser.add_argument("--frames", type=int, help="Number of physical frames (1-64)")
    parser.add_argument("--algorithm", choices=["FIFO", "LRU", "OPTIMAL"], help="Algorithm to simulate")
    parser.add_argument("--compare", action="store_true", help="Compare all three algorithms")
    args = parser.parse_args()
    if any(x is not None for x in (args.reference, args.frames, args.algorithm)) or args.compare:
        if args.reference is None or args.frames is None or (not args.compare and args.algorithm is None):
            parser.error("batch use requires --reference and --frames, plus --algorithm unless --compare is set")
        try:
            if args.compare:
                sims = compare(args.reference, args.frames); print_comparison(sims)
                for sim in sims: print(f"\n{trace_text(sim)}"); save_simulation(sim, "comparison")
                print(f"Summary saved to {save_comparison(sims)}")
                print(f"Graph saved to {save_comparison_graph(sims)}")
            else:
                sim = simulate(args.reference, args.frames, args.algorithm); print(trace_text(sim))
                for p in save_simulation(sim): print(f"Saved {p}")
            return 0
        except (ValueError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr); return 2
    run_menu(); return 0


if __name__ == "__main__": raise SystemExit(main())
