import os
import json
import urllib.request
import urllib.parse

def main():
    cf_api_key = os.environ.get("CF_API_KEY")
    if not cf_api_key:
        print("Error: CF_API_KEY env var is not set!")
        return

    # Determinamos la versión de Minecraft de pack.toml
    minecraft_ver = "26.2"
    if os.path.exists("pack.toml"):
        with open("pack.toml", "r") as f:
            for line in f:
                if "minecraft =" in line:
                    minecraft_ver = line.split("=")[1].strip().strip('"').strip("'")

    print(f"Buscando mods para Minecraft {minecraft_ver}...")

    # 1. Obtener tipos de versiones para filtrar plataformas incompatibles
    req_types = urllib.request.Request(
        'https://minecraft.curseforge.com/api/game/version-types',
        headers={'X-Api-Token': cf_api_key}
    )
    try:
        with urllib.request.urlopen(req_types) as response:
            version_types = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error al consultar tipos en CurseForge: {e}")
        version_types = []

    valid_type_ids = set()
    for vt in version_types:
        t_id = vt.get('id')
        t_name = vt.get('name', '').lower()
        exclude_keywords = ['bukkit', 'spigot', 'paper', 'bedrock', 'pocket', 'xbox', 'ps4', 'switch', 'ios', 'android', 'purpur', 'velocity', 'bungeecord']
        if not any(k in t_name for k in exclude_keywords):
            valid_type_ids.add(t_id)

    # Slugs overrides para mapear de Modrinth a CurseForge si difieren
    slug_overrides = {
        "ferrite-core": "ferritecore",
        "security-craft": "securitycraft",
    }

    mods_dir = "mods"
    if not os.path.exists(mods_dir):
        print(f"Error: No se encontró la carpeta {mods_dir}")
        return

    for filename in os.listdir(mods_dir):
        if not filename.endswith(".pw.toml"):
            continue

        file_path = os.path.join(mods_dir, filename)
        with open(file_path, "r") as f:
            content = f.read()

        # Solo convertimos si tiene Modrinth y NO CurseForge
        if "update.modrinth" not in content or "update.curseforge" in content:
            continue

        # Obtener el slug base del nombre de archivo
        base_slug = filename[:-8] # eliminar '.pw.toml'
        cf_slug = slug_overrides.get(base_slug, base_slug)

        print(f"Convirtiendo {base_slug} (Slug CurseForge: {cf_slug})...")

        # 2. Buscar el mod en CurseForge para obtener su ID de proyecto
        search_url = f"https://api.curseforge.com/v1/mods/search?gameId=432&classId=6&slug={cf_slug}"
        req_search = urllib.request.Request(search_url, headers={'x-api-key': cf_api_key})
        try:
            with urllib.request.urlopen(req_search) as response:
                search_data = json.loads(response.read().decode())
        except Exception as e:
            print(f"  Error buscando mod {cf_slug}: {e}")
            continue

        projects = search_data.get("data", [])
        if not projects:
            print(f"  No se encontró el mod con slug '{cf_slug}' en CurseForge")
            continue

        project = projects[0]
        project_id = project.get("id")
        project_name = project.get("name")

        # 3. Obtener los archivos del proyecto para encontrar el correcto para NeoForge 26.2/26.1.x
        files_url = f"https://api.curseforge.com/v1/mods/{project_id}/files"
        req_files = urllib.request.Request(files_url, headers={'x-api-key': cf_api_key})
        try:
            with urllib.request.urlopen(req_files) as response:
                files_data = json.loads(response.read().decode())
        except Exception as e:
            print(f"  Error obteniendo archivos para ID {project_id}: {e}")
            continue

        cf_files = files_data.get("data", [])
        target_file = None

        # Buscamos un archivo compatible con nuestra versión de Minecraft y NeoForge
        # Priorizamos orden descendente de fecha (los más nuevos primero)
        cf_files.sort(key=lambda x: v.get('fileDate', '') if (v := x) else '', reverse=True)

        # Buscamos coincidencia exacta o compatible
        acceptable_versions = [minecraft_ver, "26.1.2", "26.1.1", "26.1"]
        for f_info in cf_files:
            game_versions = f_info.get("gameVersions", [])
            
            # Verificamos si es para NeoForge
            is_neoforge = "NeoForge" in game_versions or "neoforge" in [g.lower() for f_g in game_versions if (g := f_g)]
            
            # Verificamos si la versión de Minecraft es compatible
            has_mc_version = any(v in game_versions for v in acceptable_versions)

            if is_neoforge and has_mc_version:
                target_file = f_info
                break

        if not target_file:
            # Fallback a buscar cualquier archivo compatible con la versión de Minecraft
            for f_info in cf_files:
                game_versions = f_info.get("gameVersions", [])
                has_mc_version = any(v in game_versions for v in acceptable_versions)
                if has_mc_version:
                    target_file = f_info
                    break

        if not target_file:
            print(f"  No se encontró un archivo compatible para {project_name} en CurseForge")
            continue

        file_id = target_file.get("id")
        file_name = target_file.get("fileName")
        
        # Obtener el hash SHA1
        sha1_hash = None
        for h in target_file.get("hashes", []):
            if h.get("algo") == 1: # algo 1 = SHA1
                sha1_hash = h.get("value")
                break

        if not sha1_hash:
            print(f"  No se pudo encontrar el hash SHA1 para el archivo de {project_name}")
            continue

        # 4. Escribir el nuevo archivo .pw.toml formateado para CurseForge
        new_content = f"""name = "{project_name}"
filename = "{file_name}"
side = "both"

[download]
hash-format = "sha1"
hash = "{sha1_hash}"
mode = "metadata:curseforge"

[update]
[update.curseforge]
file-id = {file_id}
project-id = {project_id}
"""

        with open(file_path, "w") as f:
            f.write(new_content)

        print(f"  Mod {project_name} convertido con éxito! (ID Proyecto: {project_id}, ID Archivo: {file_id})")

if __name__ == "__main__":
    main()
