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
SIGNATURE_REGEX = re.compile(r"Signer #1 certificate SHA-256 digest: ([a-f0-9]+)")

*_, ANDROID_BUILD_TOOLS = (Path(os.environ["ANDROID_HOME"]) / "build-tools").iterdir()
REPO_DIR = Path("anime-repo")
REPO_APK_DIR = REPO_DIR / "apk"
REPO_ICON_DIR = REPO_DIR / "icon"

REPO_ICON_DIR.mkdir(parents=True, exist_ok=True)

with open("output.json", encoding="utf-8") as f:
    inspector_data = json.load(f)

index_min_data = []

# Assuming all apks are signed with the same key
signing_key_fingerprint = None

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

    if not signing_key_fingerprint:
        cert_info = subprocess.check_output(
            [
                ANDROID_BUILD_TOOLS / "apksigner",
                "verify",
                "--print-certs",
                apk,
            ]
        ).decode()
        match = SIGNATURE_REGEX.search(cert_info)
        if match:
            signing_key_fingerprint = match.group(1)

    package_info = next(x for x in badging.splitlines() if x.startswith("package: "))
    package_name = PACKAGE_NAME_REGEX.search(package_info)[1]
    application_icon = APPLICATION_ICON_320_REGEX.search(badging)[1]

    with ZipFile(apk) as z, z.open(application_icon) as i, (
        REPO_ICON_DIR / f"{package_name}.png"
    ).open("wb") as f:
        f.write(i.read())

    language = LANGUAGE_REGEX.search(apk.name)[1]
    sources = inspector_data[package_name]

    if len(sources) == 1:
        source_language = sources[0]["lang"]

        if (
            source_language != language
            and source_language not in {"all", "other"}
            and language not in {"all", "other"}
        ):
            language = source_language

    common_data = {
        "name": APPLICATION_LABEL_REGEX.search(badging)[1],
        "pkg": package_name,
        "apk": apk.name,
        "lang": language,
        "code": int(VERSION_CODE_REGEX.search(package_info)[1]),
        "version": VERSION_NAME_REGEX.search(package_info)[1],
        "nsfw": int(IS_NSFW_REGEX.search(badging)[1]),
    }
    min_data = {
        **common_data,
        "sources": [],
    }

    for source in sources:
        min_data["sources"].append(
            {
                "name": source["name"],
                "lang": source["lang"],
                "id": source["id"],
                "baseUrl": source["baseUrl"],
                "versionId": source["versionId"],
            }
        )

    index_min_data.append(min_data)

# Write index.min.json which contains the extension list
with REPO_DIR.joinpath("index.min.json").open("w", encoding="utf-8") as index_file:
    json.dump(index_min_data, index_file, ensure_ascii=False, separators=(",", ":"))

# Write index.json in the new NetworkLegacyExtensionRepo format
index_v2_url = "https://raw.githubusercontent.com/Biplab8/anime-extensions/anime-repo/index.min.json"
meta_name = "Biplab8 Extensions"
meta_short_name = "Biplab8"
meta_website = "https://github.com/Biplab8/anime-extensions"

index_data = {
    "index_v2": index_v2_url,
    "meta": {
        "name": meta_name,
        "shortName": meta_short_name,
        "website": meta_website,
        "signingKeyFingerprint": signing_key_fingerprint or "UNKNOWN"
    }
}

with REPO_DIR.joinpath("index.json").open("w", encoding="utf-8") as index_file:
    json.dump(index_data, index_file, indent=2, ensure_ascii=False)
