import html
import json
import os
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

PACKAGE_NAME_REGEX = re.compile(r"package: name='([^']+)'")
VERSION_CODE_REGEX = re.compile(r"versionCode='([^']+)'")
VERSION_NAME_REGEX = re.compile(r"versionName='([^']+)'")
IS_NSFW_REGEX = re.compile(r"'tachiyomi.animeextension.nsfw' value='([^']+)'")
APPLICATION_LABEL_REGEX = re.compile(r"^application-label:'([^']+)'", re.MULTILINE)
APPLICATION_ICON_320_REGEX = re.compile(r"^application-icon-320:'([^']+)'", re.MULTILINE)
LANGUAGE_REGEX = re.compile(r"aniyomi-([^.]+)")

*_, ANDROID_BUILD_TOOLS = (Path(os.environ["ANDROID_HOME"]) / "build-tools").iterdir()
REPO_DIR = Path("anime-repo")
REPO_APK_DIR = REPO_DIR / "apk"
REPO_ICON_DIR = REPO_DIR / "icon"

REPO_ICON_DIR.mkdir(parents=True, exist_ok=True)

with open("output.json", encoding="utf-8") as f:
    inspector_data = json.load(f)

# Internal extension model
extensions = []

for apk in REPO_APK_DIR.iterdir():
    badging = subprocess.check_output(
        [
            ANDROID_BUILD_TOOLS / "aapt",
            "dump",
            "--include-meta-data",
            "badging",
            apk,
        ]
    ).decode()

    package_info = next(x for x in badging.splitlines() if x.startswith("package: "))
    package_name = PACKAGE_NAME_REGEX.search(package_info)[1]
    application_icon = APPLICATION_ICON_320_REGEX.search(badging)[1]

    with ZipFile(apk) as z, z.open(application_icon) as i, (
        REPO_ICON_DIR / f"{package_name}.png"
    ).open("wb") as f:
        f.write(i.read())

    language = LANGUAGE_REGEX.search(apk.name)[1]
    sources = inspector_data.get(package_name, [])

    if len(sources) == 1:
        source_language = sources[0]["lang"]

        if (
            source_language != language
            and source_language not in {"all", "other"}
            and language not in {"all", "other"}
        ):
            language = source_language

    extensions.append({
        "package_name": package_name,
        "apk_name": apk.name,
        "language": language,
        "sources": sources,
        "app_label": APPLICATION_LABEL_REGEX.search(badging)[1],
        "version_code": int(VERSION_CODE_REGEX.search(package_info)[1]),
        "version_name": VERSION_NAME_REGEX.search(package_info)[1],
        "is_nsfw": int(IS_NSFW_REGEX.search(badging)[1]),
    })

# Generate outputs from internal model
index_data = []
repo_extensions = []

for ext in extensions:
    min_data = {
        "name": ext["app_label"],
        "pkg": ext["package_name"],
        "apk": ext["apk_name"],
        "lang": ext["language"],
        "code": ext["version_code"],
        "version": ext["version_name"],
        "nsfw": ext["is_nsfw"],
        "sources": [],
    }

    repo_sources = []

    for source in ext["sources"]:
        min_data["sources"].append(
            {
                "name": source["name"],
                "lang": source["lang"],
                "id": source["id"],
                "baseUrl": source["baseUrl"],
                "versionId": source["versionId"],
            }
        )

        repo_sources.append(
            {
                "id": source["id"],
                "name": source["name"],
                "language": source["lang"],
                "homeUrl": source["baseUrl"],
                "mirrorUrls": [],
            }
        )

    index_data.append(min_data)

    lib_version = ext["version_name"]
    if "." in lib_version:
        lib_version = lib_version.rsplit(".", 1)[0]

    repo_extensions.append({
        "name": ext["app_label"],
        "packageName": ext["package_name"],
        "resources": {
            "apkUrl": f"apk/{ext['apk_name']}",
            "iconUrl": f"icon/{ext['package_name']}.png"
        },
        "extensionLib": lib_version,
        "versionCode": ext["version_code"],
        "versionName": ext["version_name"],
        "contentWarning": "CONTENT_WARNING_NSFW" if ext["is_nsfw"] == 1 else "CONTENT_WARNING_SAFE",
        "sources": repo_sources
    })

with REPO_DIR.joinpath("index.min.json").open("w", encoding="utf-8") as f:
    json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

with REPO_DIR.joinpath("index.json").open("w", encoding="utf-8") as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)

repo_data = {
    "name": "Animetail Extensions",
    "badgeLabel": "Animetail",
    "signingKey": "SIGNING_KEY",
    "contact": {
        "website": "https://github.com/Biplab8/anime-extensions",
        "discord": None
    },
    "extensionList": {
        "extensions": repo_extensions
    }
}

with REPO_DIR.joinpath("repo.json").open("w", encoding="utf-8") as f:
    json.dump(repo_data, f, ensure_ascii=False, indent=2)

with REPO_DIR.joinpath("index.html").open("w", encoding="utf-8") as f:
    f.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>apks</title>\n</head>\n<body>\n<pre>\n')
    for ext in index_data:
        apk_escaped = 'apk/' + html.escape(ext["apk"])
        name_escaped = html.escape(ext["name"])
        f.write(f'<a href="{apk_escaped}">{name_escaped}</a>\n')
    f.write('</pre>\n</body>\n</html>\n')
