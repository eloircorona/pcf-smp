PACKWIZ  := $(shell which packwiz 2>/dev/null || echo ~/.gvm/pkgsets/go1.23.5/global/bin/packwiz)
VERSION  := $(shell cat version.txt | tr -d '[:space:]')

.PHONY: up down restart logs console attach status update export release

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
	docker attach msmp-mc-1

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
	@echo "==> Exportando pack v$(VERSION)..."
	$(PACKWIZ) curseforge export
	@CLIENT_ZIP=$$(ls *.zip | grep -v server | head -1); \
	echo "==> Subiendo a CurseForge (client + server)..."; \
	CF_API_KEY=$$(orbit secret get CF_API_KEY) \
	CF_PROJECT_ID=$$(orbit secret get CF_PROJECT_ID) \
	VERSION=$(VERSION) \
	CLIENT_ZIP=$$CLIENT_ZIP \
	python3 scripts/cf_upload.py

# Abre una shell en el contenedor del servidor
shell:
	docker compose exec mc bash
