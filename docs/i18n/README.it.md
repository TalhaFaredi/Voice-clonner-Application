# Sonora · Clonazione vocale e sintesi del parlato

[English](../../README.md) · [Lingue della documentazione](README.md)

Sonora è un’applicazione SaaS indipendente nella cartella `Voice-clonner-Application/`. Non importa codice dall’applicazione YouTube esistente e non ne richiama l’API.

## Funzioni e stato attuale

- Registrazione, accesso, reimpostazione della password, profilo e libreria vocale privata.
- Caricamento di campioni, salvataggio dei cloni vocali, sintesi da testo, ascolto, download WAV e cronologia.
- Worker separato, SQLite, prenotazione atomica dei crediti, rimborso in caso di errore e registro di utilizzo.
- Abbonamenti Stripe, Checkout, portale clienti e webhook con verifica della firma.

Clonazione e sintesi locali sono state verificate con una GPU reale. Prima del lancio pubblico occorre configurare e verificare Stripe, SMTP, HTTPS, backup e monitoraggio. I test di pagamento simulati non verificano pagamenti reali.

## Installazione e avvio — Windows / PowerShell

Servono Python 3.12, uv e una GPU NVIDIA compatibile con CUDA. I modelli vengono scaricati al primo avvio; prevedere spazio per i modelli e PyTorch.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Dalla cartella principale del progetto, aprire tre terminali PowerShell separati ed eseguire un comando per terminale:

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Aprire **http://localhost:5173** e creare il proprio account. L’API è verificabile all’indirizzo `http://localhost:8010/api/health`. Gli account gratuiti ricevono 5.000 crediti una sola volta. La sintesi costa 1 credito per carattere; la clonazione costa 1.000 crediti per voce. Usare lo stesso nome host per frontend e API.

## GPU e lingue

Il valore predefinito `TTS_DEVICE=cuda:0` utilizza la prima GPU NVIDIA. L’installazione è stata verificata su NVIDIA RTX A6000 con 48 GB di VRAM: non è un requisito minimo né una garanzia di prestazioni. Controllare la GPU con `nvidia-smi`. Per usare la CPU, impostare `TTS_DEVICE=cpu` in `backend/.env`; la generazione sarà più lenta. Riavviare il worker dopo le modifiche e attendere `worker.status: ready` in `/api/studio/options`.

Lingue vocali supportate: cinese, inglese, giapponese, coreano, tedesco, francese, russo, portoghese, spagnolo e italiano. `auto` rileva la lingua del testo. La selezione controlla la sintesi, ma non traduce il copione. L’interfaccia attuale è in inglese.

## Verifica e distribuzione

Sono stati superati 13 test backend, controlli del browser su desktop e dispositivi mobili e il flusso reale voce predefinita → clone salvato → parlato generato. Qwen3-TTS funziona localmente e non richiede una chiave API vocale esterna. Stripe e SMTP richiedono una configurazione separata. Non pubblicare `.env`, audio privato o database.

[README completa](../../README.md) · [Configurazione e distribuzione](../setup.md) · [API](../api.md) · [Verifiche](../verification.md)
