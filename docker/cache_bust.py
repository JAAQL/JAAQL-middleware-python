"""Cache-bust static assets by embedding content hashes into filenames.

Run from the web root directory (e.g. $INSTALL_PATH/www).  Renames every
.js and .css file to  <name>.<hash>.<ext>  and updates all .html files
so their <script>/<link> references match the new names.

BATON.config.js gets special treatment: its hash includes a Unix timestamp
so that every container start produces a unique filename, forcing browsers
to re-fetch the configuration even when the underlying content is identical.
"""

import glob
import hashlib
import os
import time


def get_file_hash(file_path):
    with open(file_path, "rb") as fh:
        data = fh.read()
    return hashlib.sha256(data).hexdigest()[:6]


def update_html_references(html_files, old_new_map):
    for html_file in html_files:
        with open(html_file, "r", encoding="utf-8") as fh:
            content = fh.read()

        for old_name, new_name in sorted(
            old_new_map.items(), key=lambda item: len(item[0]), reverse=True
        ):
            content = content.replace(old_name, new_name)

        with open(html_file, "w", encoding="utf-8") as fh:
            fh.write(content)


def main():
    html_files = glob.glob("*.html")
    asset_files = glob.glob("**/*.css", recursive=True) + glob.glob(
        "**/*.js", recursive=True
    )

    old_new_map = {}
    for asset in asset_files:
        if "BATON.config.js".lower() in asset.lower():
            computed_hash = str(int(time.time())) + "_" + get_file_hash(asset)
        else:
            computed_hash = get_file_hash(asset)

        base, ext = os.path.splitext(asset)
        new_name = f"{base}.{computed_hash}{ext}"
        os.rename(asset, new_name)
        old_new_map[os.path.basename(asset)] = os.path.basename(new_name)

    update_html_references(html_files, old_new_map)


if __name__ == "__main__":
    main()
