# See: https://bugreports.qt.io/browse/PYSIDE-2215?gerritIssueType=IssueOnly
# script dependencies:
#   requests
#   sphobjinv

import re
from pathlib import Path
from subprocess import run

import requests

here = Path(__file__).parent
original_inv = here / "objects.inv"
original_txt = here / "objects.txt"
fixed_txt = here / "fixed.txt"
fixed_inv = here / "PySide6.inv"

url = "https://doc.qt.io/qtforpython-6/objects.inv"
response = requests.get(url, allow_redirects=True)
original_inv.write_bytes(response.content)

run(["sphobjinv", "convert", "plain", original_inv, original_txt], check=True)


with fixed_txt.open("w", encoding="UTF-8") as stream:
    for line in original_txt.open(encoding="UTF-8"):
        if match := re.match(r"^(PySide6\..*)\.(\1)\.(.*)$", line):
            stream.write(f"{match.group(1)}.{match.group(3)}\n")
        else:
            stream.write(line)

run(["sphobjinv", "convert", "zlib", fixed_txt, fixed_inv], check=True)
