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
with REMOTE_REPO.joinpath("index.json").open(encoding="utf-8") as remote_index_file:
    remote_index = json.load(remote_index_file)

with LOCAL_REPO.joinpath("index.json").open(encoding="utf-8") as local_index_file:
    local_index = json.load(local_index_file)

index = [
    item for item in remote_index
    if not any(item["pkg"].endswith(f".{module}") for module in to_delete)
]
index.extend(local_index)
index.sort(key=lambda x: x["pkg"])

with REMOTE_REPO.joinpath("index.json").open("w", encoding="utf-8") as index_file:
    json.dump(index, index_file, ensure_ascii=False, indent=2)

with REMOTE_REPO.joinpath("index.min.json").open("w", encoding="utf-8") as index_min_file:
    json.dump(index, index_min_file, ensure_ascii=False, separators=(",", ":"))

# Merge repo.json
repo_json_path = REMOTE_REPO.joinpath("repo.json")
if repo_json_path.exists():
    with repo_json_path.open(encoding="utf-8") as remote_repo_file:
        remote_repo_data = json.load(remote_repo_file)
else:
    remote_repo_data = {
        "name": "Animetail Extensions",
        "badgeLabel": "Animetail",
        "signingKey": "SIGNING_KEY",
        "contact": {
            "website": "https://github.com/Biplab8/anime-extensions",
            "discord": None
        },
        "extensionList": {
            "extensions": []
        }
    }

with LOCAL_REPO.joinpath("repo.json").open(encoding="utf-8") as local_repo_file:
    local_repo_data = json.load(local_repo_file)

# Ensure remote repo.json is in the expected format
if "extensionList" not in remote_repo_data:
    remote_repo_data = {
        "name": local_repo_data.get("name", "Animetail Extensions"),
        "badgeLabel": local_repo_data.get("badgeLabel", "Animetail"),
        "signingKey": local_repo_data.get("signingKey", "NO_SIGNING_KEY"),
        "contact": local_repo_data.get(
            "contact",
            {
                "website": "https://github.com/Biplab8/anime-extensions",
                "discord": None,
            },
        ),
        "extensionList": {
            "extensions": [],
        },
    }

remote_repo_exts = remote_repo_data["extensionList"].get("extensions", [])
local_repo_exts = local_repo_data["extensionList"].get("extensions", [])

repo_exts = [
    item
    for item in remote_repo_exts
    if not any(item["packageName"].endswith(f".{module}") for module in to_delete)
]

repo_exts.extend(local_repo_exts)
repo_exts.sort(key=lambda x: x["packageName"])

remote_repo_data["extensionList"]["extensions"] = repo_exts

with repo_json_path.open("w", encoding="utf-8") as repo_file:
    json.dump(remote_repo_data, repo_file, ensure_ascii=False, indent=2)

# Generate index.html
with REMOTE_REPO.joinpath("index.html").open("w", encoding="utf-8") as index_html_file:
    index_html_file.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for entry in index:
        apk_escaped = 'apk/' + html.escape(entry["apk"])
        name_escaped = html.escape(entry["name"])
        index_html_file.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    index_html_file.write('</pre>\n</body>\n</html>\n')
