#!/bin/bash
set -e

# Recherche dynamique des bibliothèques NVIDIA dans les dossiers de packages Python
# On cherche dans /usr/local/lib qui est le standard Docker pour les installs pip globales
NVIDIA_LIBS=$(find /usr/local/lib -name "nvidia" -type d -exec find {} -name "lib" -type d \; | paste -sd ":" -)

if [ -n "$NVIDIA_LIBS" ]; then
    echo "Adding NVIDIA libraries to LD_LIBRARY_PATH: $NVIDIA_LIBS"
    export LD_LIBRARY_PATH="$NVIDIA_LIBS:$LD_LIBRARY_PATH"
else
    echo "No NVIDIA libraries found via dynamic search."
fi

# Exécute la commande passée au conteneur (typiquement uvicorn)
exec "$@"
