# Utiliser une image de base NVIDIA CUDA pour garantir la compatibilité GPU
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Définir les variables d'environnement pour éviter les questions lors de l'install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Mettre à jour et installer Python et git (git est parfois nécessaire pour certains packages pip)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements-server.txt .

# Installer les dépendances Python
# On utilise --no-cache-dir pour réduire la taille de l'image
RUN pip3 install --no-cache-dir -r requirements-server.txt

# Copier le code source
COPY src/ src/
COPY config.json .
COPY README.md .
COPY entrypoint.sh .

# Rendre le script d'entrée exécutable
RUN chmod +x /app/entrypoint.sh

# Exposer le port du serveur
EXPOSE 8000

# Utiliser le script d'entrée pour configurer l'environnement
ENTRYPOINT ["/app/entrypoint.sh"]

# Commande de démarrage par défaut
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
