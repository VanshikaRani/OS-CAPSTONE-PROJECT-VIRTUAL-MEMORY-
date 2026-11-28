# Virtual Memory Lab

A small, integrated Python application for learning how virtual-memory paging behaves. It accepts a page-reference string and frame count, runs FIFO, LRU, and Optimal replacement, shows the full frame-by-frame trace, compares fault/hit rates, and graphs both policy performance and the relationship between allocated frames and page faults.

## Requirements

- Python 3.10 or newer
- No third-party packages
- Windows, macOS, or Linux terminal

## Run it

Open a terminal in this folder and run:

```text
python app.py
```

On some Linux/macOS installations, use `python3 app.py`. Choose **4** to load and immediately run the Lab 3 sample comparison. Choose **1** for a single trace, **2** to compare a custom reference string, **3** for working-set/thrashing analysis, or **6** to graph page faults as frame count changes. The menu also offers a short explanation of the algorithms.

Batch examples:

```text
python app.py --reference 7,0,1,2,0,3,0,4,2,3 --frames 3 --compare
python app.py --reference 1,2,3,1,4 --frames 2 --algorithm LRU
```

The `--compare` option writes three trace files, `outputs/comparison.csv`, and `outputs/comparison_graph.svg`. Menu option 6 writes `outputs/frame_sensitivity.svg` and prints a frame-count table. A single algorithm writes a `.txt` trace and a `.csv` trace. Menu activity is recorded in the root-level `activity.log` (ignored by Git). Generated outputs can be recreated at any time by running the examples again.

## Capstone brief

**Problem statement:** Given a finite number of physical frames and a sequence of virtual-page references, determine which pages remain resident, when page faults occur, and how replacement policy and frame count affect paging performance.

**OS concepts:** Virtual memory, demand paging, page faults, physical frames, FIFO/LRU/Optimal replacement, working sets, and thrashing risk.

**Significant functionalities:** (1) simulate each algorithm with a complete frame-by-frame hit/fault trace; (2) compare policies using counts, ratios, and a graph; (3) vary frame count and graph page-fault sensitivity; (4) inspect recent working-set sizes.

**Performance metrics:** Total page faults and hits, fault ratio (`faults / references`), hit ratio (`hits / references`), and faults versus frame count. Simulation is O(n × f) for FIFO/LRU (with the simple frame lookup) and O(n × f × n) worst case for Optimal, where n is references and f is frames.

**Test coverage:** Normal sample and repeated-page hits; boundary case of one frame and one-reference input; invalid empty/malformed/negative references, frame limits, algorithm names, and working-set windows. Run the included unit suite as described below.

**GitHub:** The folder is repository-ready. Initialize a repository and publish it to your chosen GitHub account using the commands in the report. No remote repository is created by this local deliverable.

To publish from this folder after creating an empty repository on GitHub:

```text
git init
git add .
git commit -m "Add Virtual Memory Lab capstone"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

**Demonstration and viva:** Follow the short script in `REPORT.md`; viva prompts are included there to help each team member explain their own implementation and observations.

## Input format and rules

- Reference string: one or more comma-separated, non-negative whole-number page IDs (for example `7,0,1,2`).
- Frames: integer from 1 through 64.
- Algorithms: `FIFO`, `LRU`, or `OPTIMAL`.
- Working-set window: integer from 1 through the length of the reference string.
- Invalid values produce a clear error and do not crash the application.

## Project map

| Path | Purpose |
| --- | --- |
| `app.py` | Menu, command-line interface, validation, algorithms, trace and CSV reporting |
| `sample.json` | Reproducible sample input |
| `tests/test_app.py` | Unit tests for algorithm results, hits, edge cases, and validation |
| `outputs/` | Example traces, comparison, frame-sensitivity graph, and visual evidence |
| `activity.log` | Timestamped application activity and rejected-operation log (created when the app runs) |
| `REPORT.md` | Concise phase-wise design, analysis, testing, and demonstration report |

## Test

```text
python -m unittest discover -s tests -v
```

The implementation uses only Python's standard library. On Windows, `run.bat` starts the menu and `run_sample.bat` runs the sample comparison.
