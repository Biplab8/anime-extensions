import html
import sys
import json
from pathlib import Path
import shutil

REMOTE_REPO: Path = Path.cwd()
LOCAL_REPO: Path = REMOTE_REPO.parent.joinpath(sys.argv[2])

to_delete: list[str] = json.loads(sys.argv[1])

for module in to_delete:
    apk_name = f"aniyomi-{module}-v*.*.apk"
    icon_name = f"eu.kanade.tachiyomi.animeextension.{module}.png"
    for file in REMOTE_REPO.joinpath("apk").glob(apk_name):
        print(file.name)
        file.unlink(missing_ok=True)
    for file in REMOTE_REPO.joinpath("icon").glob(icon_name):
        print(file.name)
        file.unlink(missing_ok=True)

shutil.copytree(src=LOCAL_REPO.joinpath("apk"), dst=REMOTE_REPO.joinpath("apk"), dirs_exist_ok=True)
shutil.copytree(src=LOCAL_REPO.joinpath("icon"), dst=REMOTE_REPO.joinpath("icon"), dirs_exist_ok=True)

# Merge index.json and index.min.json
# Load existing index.json if it exists
remote_index_path = REMOTE_REPO.joinpath("index.json")

if remote_index_path.exists():
    with remote_index_path.open(encoding="utf-8") as remote_index_file:
        remote_index = json.load(remote_index_file)

    # If the file isn't a list (e.g. legacy repo.json accidentally present), ignore it
    if not isinstance(remote_index, list):
        remote_index = []
else:
    remote_index = []

# Load newly generated index.json
with LOCAL_REPO.joinpath("index.json").open(encoding="utf-8") as local_index_file:
    local_index = json.load(local_index_file)

if not isinstance(local_index, list):
    raise RuntimeError("Generated index.json is invalid (expected a JSON array).")

index = [
    item
    for item in remote_index
    if not any(item["pkg"].endswith(f".{module}") for module in to_delete)
]

index.extend(local_index)

# Remove duplicate packages (keep newest)
index = {item["pkg"]: item for item in index}
index = list(index.values())

index.sort(key=lambda x: x["pkg"])

with REMOTE_REPO.joinpath("index.json").open("w", encoding="utf-8") as index_file:
    json.dump(index, index_file, ensure_ascii=False, indent=2)

# Merge index.min.json
remote_min_path = REMOTE_REPO.joinpath("index.min.json")

if remote_min_path.exists():
    with remote_min_path.open(encoding="utf-8") as f:
        remote_min = json.load(f)

    # Ignore old/invalid format
    if not isinstance(remote_min, list):
        remote_min = []
else:
    remote_min = []

with LOCAL_REPO.joinpath("index.min.json").open(encoding="utf-8") as f:
    local_min = json.load(f)

if not isinstance(local_min, list):
    raise RuntimeError("Generated index.min.json is invalid (expected a JSON array).")

merged_min = [
    item
    for item in remote_min
    if not any(item["pkg"].endswith(f".{module}") for module in to_delete)
]

merged_min.extend(local_min)

# Remove duplicate packages (keep newest build)
merged_min = {item["pkg"]: item for item in merged_min}
merged_min = list(merged_min.values())

merged_min.sort(key=lambda x: x["pkg"])

with remote_min_path.open("w", encoding="utf-8") as f:
    json.dump(merged_min, f, ensure_ascii=False, separators=(",", ":"))
# Replace repo.json with the newly generated Animetail repo.json
shutil.copy2(
    LOCAL_REPO.joinpath("repo.json"),
    REMOTE_REPO.joinpath("repo.json"),
)
# Generate index.html
with REMOTE_REPO.joinpath("index.html").open("w", encoding="utf-8") as index_html_file:
    index_html_file.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for entry in index:
        apk_escaped = 'apk/' + html.escape(entry["apk"])
        name_escaped = html.escape(entry["name"])
        index_html_file.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    index_html_file.write('</pre>\n</body>\n</html>\n')
