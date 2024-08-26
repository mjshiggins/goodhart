#!/usr/bin/env python
import argparse
import os
from datetime import datetime
from datetime import timedelta
from subprocess import Popen
import sys
import calendar
from colorama import Fore, Back, Style, init
import shutil

# Define the 7x5 representations for each letter
letters = {
    'G': [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ### "],
    'O': [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'D': ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    'H': ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'A': [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'R': ["#### ", "#   #", "#   #", "#### ", "#  # ", "#   #", "#   #"],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
}

def clean_git_history():
    if os.path.exists('.git'):
        # Rename the .git folder as a backup
        shutil.move('.git', '.git_old')
    
    # Initialize a new git repository
    run(['git', 'init'])
    
    # Add all files
    run(['git', 'add', '.'])
    
    # Commit the files
    run(['git', 'commit', '-m', '"Initial commit"'])
    
    # Remove the old .git folder
    if os.path.exists('.git_old'):
        shutil.rmtree('.git_old')

def main(def_args=sys.argv[1:]):
    args = arguments(def_args)
    curr_date = datetime.now()
    repository = args.repository
    user_name = args.user_name
    user_email = args.user_email
    
    # Clean git history
    clean_git_history()
    
    # Configure user name and email if provided
    if user_name is not None:
        run(['git', 'config', 'user.name', user_name])

    if user_email is not None:
        run(['git', 'config', 'user.email', user_email])

    # Calculate the start date: one year ago plus one month from today
    start_date = curr_date - timedelta(days=365) + timedelta(days=30)
    # Adjust to the previous Sunday to align with GitHub's graph
    start_date -= timedelta(days=start_date.weekday() + 1)

    # Map each letter to the activity graph, row by row
    graph = map_word_to_graph("GOODHART", start_date, letters)
    
    # Visualize the graph before committing
    visualize_graph(graph)
    
    # Ask for confirmation before proceeding
    proceed = input("\nDoes the graph look correct? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Aborting operation. Please adjust the parameters and try again.")
        return

    for commit_date in graph:
        contribute(commit_date)

    if repository is not None:
        run(['git', 'remote', 'add', 'origin', repository])
        run(['git', 'branch', '-M', 'main'])
        run(['git', 'push', '-u', 'origin', 'main'])

    print('\nRepository generation ' +
          '\x1b[6;30;42mcompleted successfully\x1b[0m!')

def map_word_to_graph(word, start_date, letters):
    graph = []
    for letter_index, letter in enumerate(word):
        for row in range(7):
            for col in range(5):
                if letters[letter][row][col] == "#":
                    # Add 1 to letter_index to account for the space between letters
                    commit_date = start_date + timedelta(weeks=(letter_index * 6) + col, days=row)
                    graph.append(commit_date)
    return graph

def contribute(date):
    readme_path = os.path.join(os.getcwd(), 'README.md')
    
    # Create README.md if it doesn't exist
    if not os.path.exists(readme_path):
        open(readme_path, 'w').close()
    
    with open(readme_path, 'a') as file:
        file.write(message(date) + '\n\n')
    
    run(['git', 'add', '.'])
    run(['git', 'commit', '-m', '"%s"' % message(date),
         '--date', date.strftime('"%Y-%m-%d %H:%M:%S"')])

def run(commands):
    Popen(commands).wait()

def message(date):
    return date.strftime('Contribution: %Y-%m-%d %H:%M')

def arguments(argsval):
    parser = argparse.ArgumentParser()
    parser.add_argument('-nw', '--no_weekends',
                        required=False, action='store_true', default=False,
                        help="""do not commit on weekends""")
    parser.add_argument('-r', '--repository', type=str, required=False,
                        help="""A link on an empty non-initialized remote git
                        repository. If specified, the script pushes the changes
                        to the repository. The link is accepted in SSH or HTTPS
                        format. For example: git@github.com:user/repo.git or
                        https://github.com/user/repo.git""")
    parser.add_argument('-un', '--user_name', type=str, required=False,
                        help="""Overrides user.name git config.
                        If not specified, the global config is used.""")
    parser.add_argument('-ue', '--user_email', type=str, required=False,
                        help="""Overrides user.email git config.
                        If not specified, the global config is used.""")
    parser.add_argument('-db', '--days_before', type=int, default=365,
                        required=False, help="""Specifies the number of days
                        before the current date when the script will start
                        adding commits. For example: if it is set to 30 the
                        first commit date will be the current date minus 30
                        days.""")
    parser.add_argument('-da', '--days_after', type=int, default=0,
                        required=False, help="""Specifies the number of days
                        after the current date until which the script will be
                        adding commits. For example: if it is set to 30 the
                        last commit will be on a future date which is the
                        current date plus 30 days.""")
    return parser.parse_args(argsval)

def visualize_graph(graph):
    init(autoreset=True)  # Initialize colorama
    curr_date = datetime.now()
    start_date = curr_date - timedelta(days=365) + timedelta(days=30)
    start_date -= timedelta(days=start_date.weekday() + 1)  # Adjust to previous Sunday
    end_date = curr_date + timedelta(days=7)  # Show up to next week
    
    print(f"\nGitHub Activity Graph (Last 12 months + current month):")
    print("   " + " ".join(calendar.month_abbr[m % 12 + 1] for m in range(start_date.month - 1, start_date.month + 11)))
    
    for weekday in range(7):
        print(f"{calendar.day_abbr[weekday][:2]} ", end="")
        current_date = start_date + timedelta(days=weekday)
        while current_date <= end_date:
            if any(commit_date.date() == current_date.date() for commit_date in graph):
                print(Back.GREEN + "  " + Style.RESET_ALL, end="")
            else:
                print(Back.WHITE + "  " + Style.RESET_ALL, end="")
            current_date += timedelta(weeks=1)
        print()  # New line after each day of the week

if __name__ == "__main__":
    main()