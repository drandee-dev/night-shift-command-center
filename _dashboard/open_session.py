"""Open a new Claude Code session in VS Code: this folder, this prompt ready to send.

    python open_session.py <folder> <prompt>

The extension's vscode://anthropic.claude-code/open link has no folder parameter and goes to the focused window,
and it only prefills the prompt (he presses Enter). So: `code <folder>` first (opens or focuses that folder's
window), wait for it to take focus, then open the link. Docs: code.claude.com/docs/en/vs-code.md
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.parse

CODE = shutil.which("code") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd")
FOCUS_WAIT = 4  # seconds; a cold start of VS Code is slower than focusing an open window


def uri(prompt: str) -> str:
    return "vscode://anthropic.claude-code/open?prompt=" + urllib.parse.quote(prompt, safe="")


def main(folder: str, prompt: str) -> int:
    if not os.path.isdir(folder):
        print(f"no such folder: {folder}", file=sys.stderr)
        return 2
    subprocess.run([CODE, folder], check=True, timeout=30)
    time.sleep(FOCUS_WAIT)
    os.startfile(uri(prompt))  # noqa: S606 - fixed scheme, prompt comes from the actions table
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else 2)
