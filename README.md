<!-- goodhart:start -->
### Currently rendered on my GitHub contribution graph: `ALL SLOP`

```
 ███  █     █         ████ █      ███  ████
█   █ █     █        █     █     █   █ █   █
█   █ █     █        █     █     █   █ █   █
█████ █     █         ███  █     █   █ ████
█   █ █     █            █ █     █   █ █
█   █ █     █            █ █     █   █ █
█   █ █████ █████    ████  █████  ███  █
```
<!-- goodhart:end -->

# goodhart

> "When a measure becomes a target, it ceases to be a good measure." — Goodhart's Law

A tool that draws words on your GitHub contribution graph by generating backdated commits. Named after Goodhart's Law, because if the little green squares are the measure, this repo makes them the target.

## What it does

GitHub renders your last ~12 months of commit activity as a 7-row (days of the week) by ~53-column (weeks) grid of green squares. Each square is a "pixel". This tool treats that grid as a canvas:

1. **Checks fit first.** Before touching anything, it validates your text (A–Z and spaces, case-insensitive) and prints a fit report against the 52 usable week-columns in the visible window. Too-wide or invalid text exits immediately with no side effects.
2. **Previews before committing.** It prints a colorized mock-up of the exact visible contribution window in your terminal and asks for confirmation. Declining leaves everything untouched.
3. **Cleans the slate.** On confirm, it wipes this repo's git history (re-initializing `.git` while preserving the `origin` remote) so every run starts fresh and stale pixels from previous runs disappear.
4. **Maps text to the grid.** Each letter is a 7×5 bitmap (5 pixel columns plus a 1-column spacer between letters; spaces are 2 columns wide). Text is centered across the calendar, one column of pixels per week, starting roughly a year ago.
5. **Intensity blowout.** Every visible day gets background commits (`--background-commits`, default 1); lit pixel days get highlight commits (`--highlight-commits`, default 100). GitHub colors each day relative to your yearly max, so the ~100:1 ratio makes text pixels the darkest green while real activity in your other repos blends into the light-green background instead of leaving gray holes.
6. **Generates the commits.** All commits are created in a single `git fast-import` pass — a default 8-letter run (~13,000 commits) completes in about a second. Every commit overwrites a throwaway `canvas.txt` file with its own timestamp so it is a real, non-empty change (GitHub counts commits that change files reliably, but counts empty commits inconsistently). The backdated commits touch only `canvas.txt`; the README is written once (see step 7). Both author and committer dates are backdated to the target day.
7. **Records what's drawn.** It writes an ASCII-art rendering of the current text to the very top of this `README.md` (between HTML comment markers, replaced in place on each run) so the repo itself shows what's on the graph. This header lands in the initial commit.
8. **Pushes separately.** Once commits are generated, you run `./push.sh` to force-push to GitHub. Pushing is a deliberate second step because history is always freshly re-initialized.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The only dependency is `colorama` (for the terminal preview).

## Usage

```bash
python run.py "YOUR TEXT" [-un USER_NAME] [-ue USER_EMAIL] [-hc HIGHLIGHT] [-bc BACKGROUND]
./push.sh
```

**Text argument** — positional, required. A–Z and spaces only (case-insensitive). Letters are 7×5 bitmaps laid out as 5 pixel columns plus a 1-column spacer; spaces are 2 columns wide. GitHub shows 53 week-columns but the current week is partial, so 52 complete weeks are usable — roughly **8 letters max**. Text is centered; the tool prints an exact fit report before doing anything:

```
"HIRE ME" needs 38 of 52 available week-columns -- fits, with 14 columns of margin (7 left, 7 right after centering).
```

If the text is too wide or contains unsupported characters, `run.py` exits with code 1 and makes no changes.

After the fit report, the tool prints `This run will generate N commits.` (exact count for this run), then a colorized preview of the contribution graph and a `y/n` prompt. The preview has three states: **dark green** (lit text pixels), **light green** (background days), and **blank** (future days). Only on confirmation does it wipe history and generate commits. When done, it tells you to run `./push.sh`.

**`./push.sh`** — prints the remote URL, warns that the push will overwrite remote history, asks `y/n`, then runs `git branch -M main && git push --force -u origin main`. A plain `--force` is intentional: local history is always freshly re-initialized, so a force push is required every time.

**Optional flags:**

- `-un / --user_name`, `-ue / --user_email` — override git identity for the generated commits (must match a verified email on your GitHub account for the squares to show up). If omitted, values come from `git config user.name` and `user.email`; the run aborts early if either is unset.
- `-hc / --highlight-commits` — commits per lit-pixel day (default 100, max 43200). Must be greater than `--background-commits`.
- `-bc / --background-commits` — commits per non-lit visible day (default 1). Must be at least 1.

A default 8-letter run generates roughly 13,000 commits and completes in about a second.

## Tests

```bash
source .venv/bin/activate
python -m unittest discover tests -v
```

55 tests using stdlib `unittest`.

## Requirements

- Python 3
- Dependencies in `requirements.txt` — install via the [Setup](#setup) venv steps above

## Caveats

- The commits are backdated, so the word only appears once GitHub processes the pushed history; profile contribution settings (private contribution visibility) can affect rendering. Each commit writes the throwaway `canvas.txt` file rather than being empty, because GitHub counts empty commits (no file change) inconsistently.
- The intensity blowout works while this repo's lit days remain your yearly max. A day with more than ~`highlight-commits`/4 commits elsewhere may still tint mid-green.
- Each letter costs 6 week-columns (5 pixels + 1 spacer); spaces cost 2. With 52 usable columns, you get about 8 letters — the fit report tells you exactly whether your text fits and how much margin remains.
- Since history is rewritten each run, `./push.sh` always force-pushes; that's by design, not an edge case.
