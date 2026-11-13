# Sonora · Clonación de voz y síntesis de habla

[English](../../README.md) · [Idiomas de la documentación](README.md)

Sonora es una aplicación SaaS independiente en `voice-clone-saas/`. No importa código de la aplicación de YouTube existente ni llama a su API.

## Funciones y estado actual

- Registro, inicio de sesión, recuperación de contraseña, perfil y biblioteca privada de voces.
- Carga de muestras, guardado de voces clonadas, texto a voz, reproducción, descarga WAV e historial.
- Worker independiente, SQLite, reserva atómica de créditos, devolución por fallos y seguimiento del uso.
- Suscripciones de Stripe, Checkout, portal del cliente y webhooks con firma verificada.

La clonación y la síntesis locales se han verificado con una GPU real. Antes del lanzamiento público hay que configurar y probar Stripe, SMTP, HTTPS, copias de seguridad y supervisión. Las pruebas de pagos simulados no verifican pagos reales.

## Instalación y ejecución — Windows / PowerShell

Se necesitan Python 3.12, uv y una GPU NVIDIA compatible con CUDA. Los modelos se descargan en el primer inicio; reserva espacio para los modelos y PyTorch.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application/voice-clone-saas
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Desde la raíz del proyecto, abre tres terminales PowerShell independientes y ejecuta un comando en cada una:

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Abre **http://localhost:5173** y crea tu cuenta. Puedes comprobar la API en `http://localhost:8010/api/health`. Las cuentas gratuitas reciben 5.000 créditos una sola vez. La síntesis cuesta 1 crédito por carácter y la clonación 1.000 créditos por voz. Usa el mismo nombre de host para el frontend y la API.

## GPU e idiomas

El valor predeterminado `TTS_DEVICE=cuda:0` utiliza la primera GPU NVIDIA. Se ha verificado una NVIDIA RTX A6000 con 48 GB de VRAM; no es un requisito mínimo ni una garantía de rendimiento. Comprueba la GPU con `nvidia-smi`. Para usar CPU, configura `TTS_DEVICE=cpu` en `backend/.env`; la síntesis será más lenta. Reinicia el worker tras cualquier cambio y espera `worker.status: ready` en `/api/studio/options`.

Idiomas de voz: chino, inglés, japonés, coreano, alemán, francés, ruso, portugués, español e italiano. `auto` detecta el idioma del texto. La selección controla la síntesis, pero no traduce el guion. La interfaz actual está en inglés.

## Verificación y despliegue

Se superaron 13 pruebas de backend, comprobaciones del navegador en escritorio y móvil y el flujo real voz predefinida → clon guardado → voz generada. Qwen3-TTS se ejecuta localmente y no necesita una clave de API de voz externa. Stripe y SMTP requieren configuración independiente. No publiques `.env`, audio privado ni la base de datos.

[README completa](../../README.md) · [Configuración y despliegue](../setup.md) · [API](../api.md) · [Verificaciones](../verification.md)
