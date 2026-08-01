#!/usr/bin/env python3
"""Upload client and server packs to CurseForge."""
import json, os, sys, urllib.request, zipfile

CF_API_KEY  = os.environ["CF_API_KEY"]
CF_PROJECT_ID = os.environ["CF_PROJECT_ID"]
VERSION     = os.environ["VERSION"]
CLIENT_ZIP  = os.environ["CLIENT_ZIP"]
SERVER_ZIP  = CLIENT_ZIP.replace(".zip", "-server.zip")


def cf_get(path):
    req = urllib.request.Request(
        f"https://minecraft.curseforge.com/api/{path}",
        headers={"X-Api-Token": CF_API_KEY},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def resolve_game_versions(minecraft_ver):
    exclude = {"bukkit","spigot","paper","bedrock","pocket","xbox","ps4",
               "switch","ios","android","purpur","velocity","bungeecord"}
    vtypes = cf_get("game/version-types")
    valid = {vt["id"] for vt in vtypes
             if not any(k in vt.get("name","").lower() for k in exclude)}
    versions = cf_get("game/versions")
    mc_id = neo_id = None
    for v in versions:
        if v.get("gameVersionTypeID") not in valid:
            continue
        if v.get("name") == minecraft_ver:
            mc_id = v["id"]
        if v.get("slug") == "neoforge" or v.get("name") == "NeoForge":
            neo_id = v["id"]
    return [x for x in [mc_id, neo_id] if x]


def build_server_zip():
    client_ids = set()
    for fname in os.listdir("mods"):
        if not fname.endswith(".pw.toml"):
            continue
        content = open(f"mods/{fname}").read()
        if 'side = "client"' not in content:
            continue
        import re
        m = re.search(r"project-id\s*=\s*(\d+)", content)
        if m:
            client_ids.add(int(m.group(1)))

    print(f"  Client-only project IDs excluidos del server pack: {client_ids}")

    with zipfile.ZipFile(CLIENT_ZIP, "r") as zin, \
         zipfile.ZipFile(SERVER_ZIP, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "manifest.json":
                manifest = json.loads(data)
                manifest["files"] = [
                    f for f in manifest["files"]
                    if f.get("projectID") not in client_ids
                ]
                manifest["name"] = manifest.get("name", "PCF-SMP") + " Server"
                data = json.dumps(manifest, indent=2).encode()
            zout.writestr(item, data)
    print(f"  Server pack: {SERVER_ZIP}")


def cf_upload(zip_path, display_name, game_versions, changelog):
    meta = json.dumps({
        "changelog": changelog,
        "changelogType": "markdown",
        "displayName": display_name,
        "releaseType": "release",
        "gameVersions": game_versions,
    })
    boundary = "----CurseFormBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="metadata"\r\n'
        f"Content-Type: application/json\r\n\r\n"
        f"{meta}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(zip_path)}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + open(zip_path, "rb").read() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://minecraft.curseforge.com/api/projects/{CF_PROJECT_ID}/upload-file",
        data=body,
        headers={
            "X-Api-Token": CF_API_KEY,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode())
            print(f"  OK — file ID: {resp.get('id')}")
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    minecraft_ver = "26.2"
    if os.path.exists("pack.toml"):
        for line in open("pack.toml"):
            if "minecraft =" in line:
                minecraft_ver = line.split("=")[1].strip().strip("\"'")

    changelog = open("CHANGELOG.md").read() if os.path.exists("CHANGELOG.md") else ""
    game_versions = resolve_game_versions(minecraft_ver)
    print(f"Game versions resueltos: {game_versions}")

    print(f"\n[1/3] Generando server pack...")
    build_server_zip()

    print(f"\n[2/3] Subiendo client pack ({CLIENT_ZIP})...")
    cf_upload(CLIENT_ZIP, f"PCF-SMP v{VERSION}", game_versions, changelog)

    print(f"\n[3/3] Subiendo server pack ({SERVER_ZIP})...")
    cf_upload(SERVER_ZIP, f"PCF-SMP Server v{VERSION}", game_versions, changelog)

    print("\nDone.")


if __name__ == "__main__":
    main()
