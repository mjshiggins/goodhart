#!/usr/bin/env python
import argparse
import os
from datetime import datetime
from datetime import timedelta
import string
import subprocess
from subprocess import Popen
import sys
import tempfile
import calendar
from colorama import Fore, Back, Style, init
import shutil

# 7-row bitmaps: rows are Sunday..Saturday, letters 5 columns wide, space 2.
letters = {
    'A': [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'B': ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    'C': [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    'D': ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    'E': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    'F': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    'G': [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ### "],
    'H': ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'I': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    'J': ["#####", "    #", "    #", "    #", "    #", "#   #", " ### "],
    'K': ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    'L': ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    'M': ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    'N': ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    'O': [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'P': ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    'Q': [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    'R': ["#### ", "#   #", "#   #", "#### ", "#  # ", "#   #", "#   #"],
    'S': [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    'U': ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'V': ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    'W': ["#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "],
    'X': ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    'Y': ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    'Z': ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    ' ': ["  ", "  ", "  ", "  ", "  ", "  ", "  "],
}

def visible_window(today):
    """Start Sunday and usable width of the GitHub contribution window.

    GitHub shows 53 week-columns (weeks start Sunday) ending with the
    current partial week. Days after today can't show contributions, so
    only the 52 complete weeks are safely usable for glyph pixels.
    """
    today = datetime(today.year, today.month, today.day)
    days_since_sunday = (today.weekday() + 1) % 7  # Mon=0..Sun=6 -> Sun=0
    current_week_sunday = today - timedelta(days=days_since_sunday)
    start_sunday = current_week_sunday - timedelta(weeks=52)
    return start_sunday, 52


def layout_text(text, letters):
    """Render text to a list of week-columns; each column is 7 booleans
    (rows Sunday..Saturday). One blank spacer column between glyphs,
    none after the last."""
    columns = []
    for i, ch in enumerate(text):
        glyph = letters[ch]
        if i > 0:
            columns.append([False] * 7)
        for col in range(len(glyph[0])):
            columns.append([glyph[row][col] == '#' for row in range(7)])
    return columns


def fit_report(text, needed, available):
    """Human-readable fit feedback and whether the text fits."""
    if needed <= available:
        margin = available - needed
        left = margin // 2
        return ('"%s" needs %d of %d available week-columns -- fits, '
                'with %d columns of margin (%d left, %d right after centering).'
                % (text, needed, available, margin, left, margin - left)), True
    over = needed - available
    cut = -(-over // 6)  # ceil: each letter costs ~6 columns (5 + spacer)
    return ('"%s" needs %d week-columns but only %d are available -- '
            '%d over; remove about %d character(s).'
            % (text, needed, available, over, cut)), False

HEADER_START = '<!-- goodhart:start -->'
HEADER_END = '<!-- goodhart:end -->'


def render_text_art(columns, lit='\u2588', blank=' '):
    """7-line ASCII-art rendering of laid-out glyph columns (row 0 = top,
    matching Sunday..Saturday). Lit pixels become full blocks; blanks become
    spaces. Trailing blanks are trimmed per row."""
    lines = []
    for row in range(7):
        line = ''.join(lit if col[row] else blank for col in columns)
        lines.append(line.rstrip())
    return '\n'.join(lines)


def readme_with_header(existing, text, art):
    """README content with a rendered-text header spliced in at the very top.
    If a previous header block exists it is replaced in place (idempotent);
    otherwise the block is prepended and existing content is preserved.

    Markers only count as block delimiters when they occupy their own line
    (as the inserted block always writes them). This prevents inline prose
    mentions of the marker strings -- e.g. in this tool's own docs -- from
    being mistaken for an existing block."""
    block = ('%s\n'
             '### Currently rendered on my GitHub contribution graph: `%s`\n\n'
             '```\n%s\n```\n'
             '%s' % (HEADER_START, text, art, HEADER_END))
    lines = existing.split('\n')
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == HEADER_START and start_idx is None:
            start_idx = i
        elif line.strip() == HEADER_END and start_idx is not None:
            end_idx = i
            break
    if start_idx is not None and end_idx is not None:
        new_lines = lines[:start_idx] + block.split('\n') + lines[end_idx + 1:]
        return '\n'.join(new_lines)
    return block + '\n\n' + existing


def build_day_counts(columns, start_sunday, today, offset, background,
                     highlight):
    """Commits per calendar day: `background` on every visible day from
    start_sunday through today, `highlight` (replacing, not adding) on days
    under a lit pixel."""
    counts = {}
    day = start_sunday.date()
    while day <= today.date():
        counts[day] = background
        day += timedelta(days=1)
    for col_index, column in enumerate(columns):
        for row in range(7):
            if column[row]:
                lit = (start_sunday
                       + timedelta(weeks=offset + col_index, days=row)).date()
                if lit in counts:
                    counts[lit] = highlight
    return counts

def fast_import_stream(day_counts, name, email, from_sha):
    """Bytes for one `git fast-import` run creating every commit in
    day_counts on refs/heads/main, oldest day first, timestamps spread in
    one-second steps from 12:00. Author and committer both carry the
    backdated timestamp.

    Every commit overwrites the throwaway file `canvas.txt` with its own
    unique timestamp. This makes each commit a real, non-empty change:
    GitHub's contribution graph reliably counts commits that change files,
    whereas empty commits (identical tree to the parent) are counted
    inconsistently. The README is never touched."""
    parts = []
    first = True
    for day in sorted(day_counts):
        for i in range(day_counts[day]):
            stamp = (datetime(day.year, day.month, day.day, 12, 0, 0)
                     + timedelta(seconds=i))
            # Per-day offset so days in the other DST regime keep local noon.
            tz = stamp.astimezone().strftime('%z')
            ident = '%s <%s> %d %s' % (name, email,
                                       int(stamp.timestamp()), tz)
            msg = stamp.strftime('Contribution: %Y-%m-%d %H:%M:%S')
            # Unique per-commit content so every tree differs (no empty commit).
            content = msg + '\n'
            block = ('commit refs/heads/main\n'
                     'author %s\n'
                     'committer %s\n'
                     'data %d\n'
                     '%s\n' % (ident, ident, len(msg.encode()), msg))
            if first:
                block += 'from %s\n' % from_sha
                first = False
            block += ('M 644 inline canvas.txt\n'
                      'data %d\n'
                      '%s' % (len(content.encode()), content))
            parts.append(block)
    return ''.join(parts).encode()

def get_remote_url():
    try:
        return subprocess.check_output(['git', 'remote', 'get-url', 'origin']).decode().strip()
    except subprocess.CalledProcessError:
        return None

def git_config(key):
    try:
        return subprocess.check_output(
            ['git', 'config', key]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def clean_git_history(name, email):
    # Store the remote URL before cleaning
    remote_url = get_remote_url()

    # Back up the old .git OUTSIDE the repo so `git add .` can't pick it up
    # and leak the wiped history into the new initial commit.
    backup_dir = None
    if os.path.exists('.git'):
        backup_dir = tempfile.mkdtemp()
        shutil.move('.git', os.path.join(backup_dir, '.git_old'))

    # Initialize a new git repository directly on `main` (no transient
    # `master` branch that later has to be renamed).
    run(['git', 'init'])
    run(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'])

    # Configure identity BEFORE the initial commit so it carries the
    # resolved name/email (and so the flow works without a global identity).
    run(['git', 'config', 'user.name', name])
    run(['git', 'config', 'user.email', email])

    # Add all files
    run(['git', 'add', '.'])
    
    # Commit the files
    run(['git', 'commit', '-m', '"Initial commit"'])
    
    # Restore the remote URL if it existed
    if remote_url:
        run(['git', 'remote', 'add', 'origin', remote_url])
    
    # Remove the backed-up old .git folder
    if backup_dir is not None:
        shutil.rmtree(backup_dir, ignore_errors=True)

    return remote_url

def main(def_args=sys.argv[1:]):
    args = arguments(def_args)
    text = args.text.upper()

    unsupported = sorted({ch for ch in text if ch not in letters})
    if unsupported:
        print('Unsupported character(s): %s' % ', '.join(repr(c) for c in unsupported))
        print('Supported characters: A-Z and space.')
        sys.exit(1)

    if not any(ch in string.ascii_uppercase for ch in text):
        print('Text must contain at least one letter.')
        sys.exit(1)

    today = datetime.now()
    start_sunday, available = visible_window(today)
    columns = layout_text(text, letters)

    report, fits = fit_report(text, len(columns), available)
    print(report)
    if not fits:
        sys.exit(1)

    if args.background_commits < 1 or \
            args.highlight_commits <= args.background_commits:
        print('highlight-commits must be greater than background-commits, '
              'and background-commits at least 1.')
        sys.exit(1)

    if args.highlight_commits > 43200:
        print('highlight-commits must be at most 43200 '
              '(one-second steps from noon must stay within the day).')
        sys.exit(1)

    offset = (available - len(columns)) // 2
    day_counts = build_day_counts(columns, start_sunday, today, offset,
                                  args.background_commits,
                                  args.highlight_commits)
    total = sum(day_counts.values())
    print('This run will generate %d commits.' % total)

    name = args.user_name or git_config('user.name')
    email = args.user_email or git_config('user.email')
    if not name or not email:
        print('Set git user.name and user.email (or pass -un/-ue).')
        sys.exit(1)

    highlight_days = {day for day, count in day_counts.items()
                      if count == args.highlight_commits}
    visualize_graph(highlight_days, start_sunday, today)

    proceed = input("\nDoes the graph look correct? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Aborting. Nothing was modified.")
        return

    # Advertise the rendered text at the top of the README so the repo shows
    # what is currently drawn. Written before the wipe so it lands in history.
    existing = ''
    if os.path.exists('README.md'):
        with open('README.md', encoding='utf-8') as f:
            existing = f.read()
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_with_header(existing, text, render_text_art(columns)))

    clean_git_history(name, email)
    run(['git', 'branch', '-M', 'main'])

    from_sha = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD']).decode().strip()
    stream = fast_import_stream(day_counts, name, email, from_sha)
    result = subprocess.run(['git', 'fast-import', '--quiet'], input=stream,
                            stdout=subprocess.DEVNULL)
    if result.returncode != 0:
        print('git fast-import failed (exit %d). The repo has been '
              're-initialized; your previous history is gone, but the '
              'initial commit is intact.' % result.returncode)
        sys.exit(1)
    run(['git', 'reset', '--hard', 'main'])

    print('\nCommits generated. Publish with: ./push.sh')

def run(commands):
    Popen(commands).wait()

def arguments(argsval):
    parser = argparse.ArgumentParser(
        description='Draw text on your GitHub contribution graph.')
    parser.add_argument('text', type=str,
                        help='Text to draw (A-Z and spaces; case-insensitive).')
    parser.add_argument('-un', '--user_name', type=str, required=False,
                        help='Overrides user.name git config for the '
                             'generated commits.')
    parser.add_argument('-ue', '--user_email', type=str, required=False,
                        help='Overrides user.email git config for the '
                             'generated commits.')
    parser.add_argument('-hc', '--highlight-commits', type=int, default=100,
                        help='Commits per lit-pixel day (default 100).')
    parser.add_argument('-bc', '--background-commits', type=int, default=1,
                        help='Commits per non-lit visible day (default 1).')
    return parser.parse_args(argsval)

def visualize_graph(highlight_days, start_sunday, today):
    init(autoreset=True, strip=False)
    total_columns = 53

    header = '   '
    last_month = None
    for week in range(total_columns):
        week_start = start_sunday + timedelta(weeks=week)
        if week_start.month != last_month:
            header += calendar.month_abbr[week_start.month][:2]
            last_month = week_start.month
        else:
            header += '  '
    print('\nGitHub contribution graph preview (visible window):')
    print(header)

    for weekday in range(7):
        # day_abbr is Mon-first; row 0 must be Sunday
        print('%s ' % calendar.day_abbr[(weekday + 6) % 7][:2], end='')
        for week in range(total_columns):
            day = (start_sunday + timedelta(weeks=week, days=weekday)).date()
            if day > today.date():
                print('  ', end='')
            elif day in highlight_days:
                print(Back.GREEN + '  ' + Style.RESET_ALL, end='')
            else:
                print(Back.LIGHTGREEN_EX + '  ' + Style.RESET_ALL, end='')
        print()

if __name__ == "__main__":
    main()