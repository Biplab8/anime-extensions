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

shutil.copytree(src=LOCAL_REPO.joinpath("apk"), dst=REMOTE_REPO.joinpath("apk"), dirs_exist_ok = True)
shutil.copytree(src=LOCAL_REPO.joinpath("icon"), dst=REMOTE_REPO.joinpath("icon"), dirs_exist_ok = True)

# --- FIX: Type-checking to ensure JSON structure is strictly valid ---
try:
    with REMOTE_REPO.joinpath("index.json").open() as remote_index_file:
        remote_index = json.load(remote_index_file)
        if not isinstance(remote_index, list):
            print("Warning: Remote index.json is not a valid list. Resetting to an empty list.")
            remote_index = []
except (json.JSONDecodeError, FileNotFoundError):
    print("Warning: Remote index.json is empty, corrupt, or missing. Defaulting to an empty list.")
    remote_index = []
# -------------------------------------------------------------------

with LOCAL_REPO.joinpath("index.min.json").open() as local_index_file:
    local_index = json.load(local_index_file)

# SAFELY filter the items by ensuring they are dictionaries containing the "pkg" key
index = [
    item for item in remote_index
    if isinstance(item, dict) and "pkg" in item and not any(item["pkg"].endswith(f".{module}") for module in to_delete)
]

index.extend(local_index)

# Safely sort using .get() to prevent crashes if an item is missing the pkg key
index.sort(key=lambda x: x.get("pkg", ""))

with REMOTE_REPO.joinpath("index.json").open("w", encoding="utf-8") as index_file:
    json.dump(index, index_file, ensure_ascii=False, indent=2)

for item in index:
    if "sources" in item and isinstance(item["sources"], list):
        for source in item["sources"]:
            if isinstance(source, dict):
                source.pop("versionId", None)

with REMOTE_REPO.joinpath("index.min.json").open("w", encoding="utf-8") as index_min_file:
    json.dump(index, index_min_file, ensure_ascii=False, separators=(",", ":"))

with REMOTE_REPO.joinpath("index.html").open("w", encoding="utf-8") as index_html_file:
    index_html_file.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for entry in index:
        if isinstance(entry, dict) and "apk" in entry and "name" in entry:
            apk_escaped = 'apk/' + html.escape(entry["apk"])
            name_escaped = html.escape(entry["name"])
            index_html_file.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    index_html_file.write('</pre>\n</body>\n</html>\n')
