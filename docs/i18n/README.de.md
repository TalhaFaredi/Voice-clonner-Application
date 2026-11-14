# Mellifon · Plattform für Stimmklonen und Sprachsynthese

[English](../../README.md) · [Weitere Dokumentationssprachen](README.md)

Mellifon ist eine eigenständige Sprach-SaaS im Ordner `Voice-clonner-Application/`. Sie importiert keinen Anwendungscode aus der bestehenden YouTube-App und ruft deren API nicht auf.

## Funktionen und aktueller Stand

- Registrierung, Anmeldung, Passwortzurücksetzung, Profile und private Stimmenbibliotheken.
- Sprachproben hochladen, geklonte Stimmen speichern, Text vorlesen lassen, Audio anhören, WAV herunterladen und den Verlauf aufrufen.
- Separater Hintergrund-Worker, SQLite, atomare Kreditreservierungen, Rückerstattung bei Fehlern und Nutzungsprotokolle.
- Stripe-Abonnements, Checkout, Kundenportal und signaturgeprüfte Webhooks.

Lokales Stimmklonen und die Sprachsynthese wurden mit einer echten GPU geprüft. Vor einer öffentlichen Bereitstellung müssen Stripe, SMTP, HTTPS, Sicherungen und Überwachung eingerichtet und getestet werden. Simulierte Zahlungstests bestätigen keine echten Zahlungen.

## Installation und Start — Windows / PowerShell

Voraussetzungen: Python 3.12, uv und eine NVIDIA-GPU mit CUDA-Unterstützung. Modelle werden beim ersten Start heruntergeladen; planen Sie Speicherplatz für Modelle und PyTorch ein.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Öffnen Sie im Projektverzeichnis drei getrennte PowerShell-Terminals und führen Sie jeweils einen Befehl aus:

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Öffnen Sie **http://localhost:5173** und registrieren Sie ein eigenes Konto. Die API ist unter `http://localhost:8010/api/health` prüfbar. Kostenlose Konten erhalten einmalig 5.000 Credits. Sprachsynthese kostet einen Credit pro Zeichen, ein Stimmklon 1.000 Credits. Verwenden Sie für Frontend und API denselben Hostnamen.

## GPU und Sprachen

`TTS_DEVICE=cuda:0` verwendet standardmäßig die erste NVIDIA-GPU. Geprüft wurde eine NVIDIA RTX A6000 mit 48 GB VRAM; dies ist weder eine Mindestanforderung noch eine Leistungsgarantie. Prüfen Sie die GPU mit `nvidia-smi`. Für CPU-Betrieb setzen Sie `TTS_DEVICE=cpu` in `backend/.env`; die Verarbeitung ist langsamer. Starten Sie den Worker nach Änderungen neu und warten Sie unter `/api/studio/options` auf `worker.status: ready`.

Unterstützt werden Chinesisch, Englisch, Japanisch, Koreanisch, Deutsch, Französisch, Russisch, Portugiesisch, Spanisch und Italienisch. `auto` erkennt die Sprache des Textes. Die Auswahl steuert die Sprachausgabe, übersetzt aber keinen Text. Die Benutzeroberfläche ist derzeit auf Englisch.

## Prüfung und Bereitstellung

13 Backend-Tests, Desktop-/Mobilbrowser-Prüfungen sowie echte GPU-Durchläufe von einer Preset-Stimme über einen gespeicherten Klon bis zur Sprachausgabe wurden durchgeführt. Qwen3-TTS läuft lokal und benötigt keinen externen Sprach-API-Schlüssel. Stripe und SMTP müssen separat konfiguriert werden. Veröffentlichen Sie keine `.env`, privaten Audiodateien oder Datenbanken.

[Vollständige README](../../README.md) · [Einrichtung und Deployment](../setup.md) · [API](../api.md) · [Prüfhinweise](../verification.md)
