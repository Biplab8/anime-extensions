import json
import html
import sys
from pathlib import Path

# Get arguments
delete_list = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] else []

# Fix: The Action passes 'master/repo', but we are inside 'anime-repo'. We need to step back one folder using ".."
new_repo_arg = sys.argv[2] if len(sys.argv) > 2 else "repo"
new_repo_dir = Path("..").joinpath(new_repo_arg)

REMOTE_REPO = Path(".")

# Load existing extensions
existing_index_path = REMOTE_REPO.joinpath("index.min.json")
existing_extensions = []
if existing_index_path.exists():
    try:
        with existing_index_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle both V1 (array) and V2 (dict) formats from previous runs
            existing_extensions = data.get("extensions", data) if isinstance(data, dict) else data
    except:
        pass

# Load new extensions
with new_repo_dir.joinpath("index.min.json").open("r", encoding="utf-8") as f:
    new_extensions = json.load(f)

# Merge logic
extension_dict = {ext["pkg"]: ext for ext in existing_extensions}

for ext in new_extensions:
    extension_dict[ext["pkg"]] = ext

for pkg in delete_list:
    if pkg in extension_dict:
        del extension_dict[pkg]

final_extensions = list(extension_dict.values())

# --- GENERATE V2 REPO.JSON ---
v2_repo_data = {
    "name": "Biplab8 Anime Repo",
    "badgeLabel": "Biplab8",
    "contact": {
        "website": "https://github.com/Biplab8/anime-extensions"
    },
    "signingKey": "CB6989FEEC8A90A43CC9359BC79B2CCDBF22DCBE955A6F39878C0C0BB25D6B99",
    "extensions": final_extensions
}

with REMOTE_REPO.joinpath("repo.json").open("w", encoding="utf-8") as f:
    json.dump(v2_repo_data, f, ensure_ascii=False, indent=2)

# --- GENERATE LEGACY INDEX.MIN.JSON ---
with REMOTE_REPO.joinpath("index.min.json").open("w", encoding="utf-8") as f:
    json.dump(final_extensions, f, ensure_ascii=False, separators=(",", ":"))

# --- GENERATE INDEX.HTML ---
with REMOTE_REPO.joinpath("index.html").open("w", encoding="utf-8") as f:
    f.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for entry in final_extensions:
        apk_escaped = html.escape(entry["apk"])
        name_escaped = html.escape(entry["name"])
        f.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    f.write('</pre>\n</body>\n</html>\n')
