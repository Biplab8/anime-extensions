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

with REMOTE_REPO.joinpath("index.json").open() as remote_index_file:
    remote_index = json.load(remote_index_file)

with LOCAL_REPO.joinpath("index.min.json").open() as local_index_file:
    local_index = json.load(local_index_file)

index = [
    item for item in remote_index
    if not any(item["pkg"].endswith(f".{module}") for module in to_delete)
]
index.extend(local_index)
index.sort(key=lambda x: x["pkg"])

with REMOTE_REPO.joinpath("index.json").open("w", encoding="utf-8") as index_file:
    json.dump(index, index_file, ensure_ascii=False, indent=2)

for item in index:
    for source in item["sources"]:
        source.pop("versionId", None)

# --- NEW ROOT FORMAT FOR INDEX.MIN.JSON ---
v2_extensions = []
for entry in index:
    v2_entry = entry.copy()
    
    # 1. Revert APK path to just the filename (Animetail automatically adds /apk/ internally)
    if "apk" in v2_entry and v2_entry["apk"].startswith("apk/"):
        v2_entry["apk"] = v2_entry["apk"].replace("apk/", "")
        
    # 2. Add REQUIRED metadata fields to prevent the Kotlin JSON parser from crashing
    v2_entry["hasReadme"] = 0
    v2_entry["hasChangelog"] = 0
    v2_entry["icon"] = f"https://raw.githubusercontent.com/Biplab8/anime-extensions/anime-repo/icon/{v2_entry['pkg']}.png"
        
    # 3. FORCE the ID into a pure integer
    if "sources" in v2_entry:
        fixed_sources = []
        for source in v2_entry["sources"]:
            source_copy = source.copy()
            if "id" in source_copy:
                source_copy["id"] = int(source_copy["id"])
            fixed_sources.append(source_copy)
        v2_entry["sources"] = fixed_sources
        
    v2_extensions.append(v2_entry)

v2_index_data = {
    "name": "Biplab8 Anime Repo",
    "badgeLabel": "Biplab8",
    "contact": {
        "website": "https://github.com/Biplab8/anime-extensions"
    },
    "signingKey": "CB6989FEEC8A90A43CC9359BC79B2CCDBF22DCBE955A6F39878C0C0BB25D6B99",
    "extensions": v2_extensions
}

with REMOTE_REPO.joinpath("index.min.json").open("w", encoding="utf-8") as index_min_file:
    json.dump(v2_index_data, index_min_file, ensure_ascii=False, separators=(",", ":"))
# ------------------------------------------

with REMOTE_REPO.joinpath("index.html").open("w", encoding="utf-8") as index_html_file:
    index_html_file.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for entry in index:
        apk_escaped = 'apk/' + html.escape(entry["apk"])
        name_escaped = html.escape(entry["name"])
        index_html_file.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    index_html_file.write('</pre>\n</body>\n</html>\n')
