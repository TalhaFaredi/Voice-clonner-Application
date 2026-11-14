# Mellifon · Clonage vocal et synthèse vocale

[English](../../README.md) · [Langues de documentation](README.md)

Mellifon est une application SaaS autonome dans `Voice-clonner-Application/`. Elle n’importe aucun code de l’application YouTube existante et n’appelle pas son API.

## Fonctionnalités et état actuel

- Inscription, connexion, réinitialisation du mot de passe, profil et bibliothèque vocale privée.
- Import d’échantillons, sauvegarde de voix clonées, synthèse vocale, écoute, téléchargement WAV et historique.
- Worker indépendant, SQLite, réservation atomique des crédits, remboursement en cas d’échec et suivi de consommation.
- Abonnements Stripe, Checkout, portail client et webhooks avec vérification de signature.

Le clonage et la synthèse en local ont été vérifiés sur un vrai GPU. Avant une ouverture au public, il reste à configurer et tester Stripe, SMTP, HTTPS, les sauvegardes et la supervision. Des tests de paiement simulés ne valident pas de vrais paiements.

## Installation et lancement — Windows / PowerShell

Prérequis : Python 3.12, uv et un GPU NVIDIA compatible CUDA. Les modèles sont téléchargés au premier démarrage ; prévoyez de l’espace disque pour les modèles et PyTorch.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Depuis la racine du projet, ouvrez trois terminaux PowerShell séparés et exécutez une commande par terminal :

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Ouvrez **http://localhost:5173** et créez votre compte. L’API se vérifie sur `http://localhost:8010/api/health`. Un compte gratuit reçoit 5 000 crédits une seule fois. La synthèse coûte un crédit par caractère et le clonage 1 000 crédits par voix. Utilisez le même nom d’hôte pour le frontend et l’API.

## GPU et langues

Par défaut, `TTS_DEVICE=cuda:0` utilise le premier GPU NVIDIA. L’installation a été vérifiée sur une NVIDIA RTX A6000 avec 48 Go de VRAM ; ce n’est ni un minimum matériel ni une garantie de performances. Consultez `nvidia-smi` pour l’état du GPU. Pour utiliser le CPU, définissez `TTS_DEVICE=cpu` dans `backend/.env` ; la génération sera plus lente. Redémarrez le worker après toute modification et attendez `worker.status: ready` dans `/api/studio/options`.

Langues prises en charge : chinois, anglais, japonais, coréen, allemand, français, russe, portugais, espagnol et italien. `auto` détecte la langue du texte. Ce choix règle la synthèse, mais ne traduit pas le texte. L’interface est actuellement en anglais.

## Vérification et déploiement

13 tests backend, les parcours navigateur sur ordinateur et mobile, ainsi que la chaîne réelle voix prédéfinie → clone sauvegardé → synthèse ont été vérifiés. Qwen3-TTS fonctionne localement, sans clé d’API vocale externe. Stripe et SMTP demandent une configuration distincte. Ne publiez pas `.env`, les fichiers audio privés ou la base de données.

[README complète](../../README.md) · [Configuration et déploiement](../setup.md) · [API](../api.md) · [Vérifications](../verification.md)
