from collections import defaultdict
from datetime import datetime
import re
from pathlib import Path
import subprocess
import sys

import toml


commit_parser = re.compile(r'(?P<tag>\[\S+\])?(?P<message>.+)')


def main():
    pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    pyproject = toml.load(pyproject_path)
    config: dict = pyproject['tool'].get('changelog', {})
    changelog_path = Path(config.get('changelog_path', 'CHANGELOG.md'))
    git_cmd = ['git', 'log', '--format=%B']
    date = config.get('date')
    if date:
        git_cmd.append(f'--since={date}')
    commits = [line for line in subprocess.check_output(git_cmd).splitlines()]
    sections = defaultdict(list)
    for commit in commits:
        match = commit_parser.search(commit).groupdict()
        sections[match.get('tag', 'other')].append(match.get('message'))
    tag_mapping = config.get('tag_mapping', {})
    changelog = f'# {pyproject["tool"]["poetry"]["name"]} v{sys.argv[-1]}\n\n'
    for tag, messages in sections.items():
        t = tag[1:-1]
        changelog += f'## {tag_mapping.get(t, t)}\n'
        changelog += '\n'.join(f'- {msg}' for msg in messages)
    existing = changelog_path.read_text()
    changelog_path.write_text(changelog + '\n\n' + existing)
    config['date'] = datetime.today().strftime('%Y-%m-%d')
    pyproject['tool']['changelog'] = config
    pyproject_path.write_text(toml.dumps(pyproject))
