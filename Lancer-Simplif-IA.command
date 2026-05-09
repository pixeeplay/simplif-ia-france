#!/usr/bin/env bash
# ============================================================
# Simplif'IA France - Lancement local en un double-clic
# ============================================================
set -e

# Couleurs
GRN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[0;33m'; BLU='\033[0;34m'; NC='\033[0m'

# Aller dans le dossier du script (works avec espaces dans le path)
cd "$(dirname "$0")"

clear
echo -e "${BLU}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLU}║         SIMPLIF'IA FRANCE · Déploiement local        ║${NC}"
echo -e "${BLU}╚══════════════════════════════════════════════════════╝${NC}\n"

# 1. Vérifier Docker Desktop
echo -e "${YEL}[1/5]${NC} Vérification de Docker Desktop…"
if ! command -v docker &> /dev/null; then
  echo -e "${RED}❌ Docker n'est pas installé.${NC}"
  echo -e "Installez Docker Desktop : https://www.docker.com/products/docker-desktop/"
  echo "Appuyez sur Entrée pour fermer…"
  read
  exit 1
fi

if ! docker info &> /dev/null 2>&1; then
  echo -e "${YEL}⚠️  Docker Desktop n'est pas démarré. Tentative de lancement…${NC}"
  open -a "Docker"
  echo -n "Attente du démarrage de Docker"
  for i in {1..30}; do
    if docker info &> /dev/null 2>&1; then echo " ✅"; break; fi
    echo -n "."
    sleep 2
  done
  if ! docker info &> /dev/null 2>&1; then
    echo -e "\n${RED}❌ Docker n'a pas démarré. Lancez Docker Desktop manuellement et relancez ce script.${NC}"
    read
    exit 1
  fi
fi
echo -e "${GRN}✅ Docker prêt${NC}\n"

# 2. Vérifier le fichier .env
echo -e "${YEL}[2/5]${NC} Vérification du .env…"
if [ ! -f .env ]; then
  echo -e "${RED}❌ Fichier .env introuvable. Vérifiez le dossier.${NC}"
  read; exit 1
fi
echo -e "${GRN}✅ .env présent${NC}\n"

# 3. Build et lancement
echo -e "${YEL}[3/5]${NC} Construction des images Docker (1ère fois ≈ 3-5 min)…"
docker compose build
echo -e "${GRN}✅ Images construites${NC}\n"

# 4. Démarrage
echo -e "${YEL}[4/5]${NC} Démarrage de la stack (postgres + redis + backend + frontend)…"
docker compose up -d
echo -e "${GRN}✅ Conteneurs démarrés${NC}\n"

# 5. Attente readiness
echo -e "${YEL}[5/5]${NC} Attente du backend…"
for i in {1..30}; do
  if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GRN}✅ Backend prêt${NC}\n"
    break
  fi
  echo -n "."
  sleep 2
done

# Récap
echo -e "${BLU}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLU}║                   ✅ DÉPLOIEMENT OK                   ║${NC}"
echo -e "${BLU}╚══════════════════════════════════════════════════════╝${NC}\n"

# Lire l'admin password depuis .env pour l'afficher
ADMIN_EMAIL=$(grep "^ADMIN_EMAIL=" .env | cut -d= -f2)
ADMIN_PWD=$(grep "^ADMIN_PASSWORD=" .env | cut -d= -f2)

echo -e "${GRN}🌐 Frontend :${NC}    http://localhost:8080"
echo -e "${GRN}📚 API Docs :${NC}    http://localhost:8080/docs"
echo -e "${GRN}❤️  Healthcheck :${NC} http://localhost:8080/health"
echo ""
echo -e "${YEL}🔐 Compte admin :${NC}"
echo -e "   Email :    ${ADMIN_EMAIL}"
echo -e "   Password : ${ADMIN_PWD}"
echo ""
echo -e "${YEL}📋 Logs en direct :${NC} docker compose logs -f"
echo -e "${YEL}🛑 Arrêter :${NC}        docker compose down"
echo ""

# Ouvrir le navigateur
echo "Ouverture du navigateur dans 2 secondes…"
sleep 2
open http://localhost:8080

echo ""
echo "Appuyez sur Entrée pour fermer cette fenêtre (la stack continue de tourner en arrière-plan)…"
read
