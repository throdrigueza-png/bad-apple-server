#!/bin/bash
# Azure ya instala los requerimientos automáticamente si SCM_DO_BUILD_DURING_DEPLOYMENT está en 1.
# Solo lanzamos el servidor.
echo "--- ARRANCANDO SERVIDOR BAD APPLE EN PUERTO $WEBSITES_PORT ---"
python3 main.py
