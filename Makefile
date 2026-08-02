PACKWIZ    := $(shell which packwiz 2>/dev/null || echo ~/.gvm/pkgsets/go1.23.5/global/bin/packwiz)
PRISM      := flatpak run org.prismlauncher.PrismLauncher
VERSION    := $(shell cat version.txt | tr -d '[:space:]')
PACK_NAME  := $(shell python3 -c "import re; print(re.search(r'name\s*=\s*\"(.+?)\"', open('pack.toml').read()).group(1))")
CLIENT_ZIP := $(PACK_NAME)-$(VERSION).zip

.PHONY: up down restart logs console attach status update export release test client

# Levanta el servidor (build primero si hay cambios en el pack)
up:
	docker compose up -d
	@echo "Server starting... usa 'make logs' para ver el progreso"

# Detiene el servidor
down:
	docker compose down

# Reinicia solo el servidor de Minecraft (útil tras actualizar mods)
restart:
	docker compose restart mc

# Logs en tiempo real
logs:
	docker compose logs -f mc

# Consola interactiva del servidor (Ctrl+P Ctrl+Q para salir sin matar el server)
console:
	docker attach ssmp-mc-1

# Estado de los contenedores
status:
	docker compose ps

# Actualiza todos los mods y reinicia el servidor
update:
	$(PACKWIZ) update --all
	docker compose restart mc
	@echo "Mods actualizados. Servidor reiniciando..."

# Exporta el pack para CurseForge
export:
	$(PACKWIZ) curseforge export
	@echo "Pack exportado. Busca el .zip en el directorio actual."

# Exporta y publica client + server pack en CurseForge
release:
	@echo "==> Exportando pack v$(VERSION) -> $(CLIENT_ZIP)..."
	$(PACKWIZ) curseforge export
	@echo "==> Subiendo a CurseForge (client + server)..."
	@CF_API_KEY=$$(orbit secret get CF_API_KEY) \
	CF_PROJECT_ID=$$(orbit secret get CF_PROJECT_ID) \
	VERSION=$(VERSION) \
	CLIENT_ZIP=$(CLIENT_ZIP) \
	python3 scripts/cf_upload.py

# Corre los tests de KubeJS (requiere: cd kubejs && npm install)
test:
	cd kubejs && npm test

# Lanza el cliente (Prism Launcher, instancia PCF-SMP)
# Sirve el pack localmente para que packwiz-installer sincronice los mods
client:
	@echo "Matando cualquier packwiz serve previo..."
	@pkill -f "[p]ackwiz serve" 2>/dev/null || true
	@sleep 0.5
	@echo "Iniciando packwiz serve desde $(dir $(abspath $(lastword $(MAKEFILE_LIST))))..."
	@cd $(dir $(abspath $(lastword $(MAKEFILE_LIST)))) && $(PACKWIZ) serve &
	@sleep 1
	$(PRISM) --launch PCF-SMP --show-window; \
	pkill -f "[p]ackwiz serve" 2>/dev/null || true

# Abre una shell en el contenedor del servidor
shell:
	docker compose exec mc bash
