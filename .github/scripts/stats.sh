#!/bin/bash
# Script pour afficher les statistiques du repository

echo "📊 Statistiques Tado X Integration"
echo "=================================="
echo ""

# Stars
STARS=$(gh api repos/exabird/ha-tado-x --jq '.stargazers_count')
echo "🌟 Stars: $STARS"

# Clones (installations HACS)
CLONES=$(gh api repos/exabird/ha-tado-x/traffic/clones --jq '.count')
UNIQUE_CLONES=$(gh api repos/exabird/ha-tado-x/traffic/clones --jq '.uniques')
echo "📥 Clones (14j): $CLONES ($UNIQUE_CLONES uniques)"

# Vues
VIEWS=$(gh api repos/exabird/ha-tado-x/traffic/views --jq '.count')
UNIQUE_VIEWS=$(gh api repos/exabird/ha-tado-x/traffic/views --jq '.uniques')
echo "👁️  Vues (14j): $VIEWS ($UNIQUE_VIEWS visiteurs)"

# Latest releases
echo ""
echo "📦 Dernières versions:"
gh release list --limit 3

echo ""
echo "✅ Génération terminée!"
