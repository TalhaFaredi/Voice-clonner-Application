# Mellifon · Clonagem de voz e síntese de fala

[English](../../README.md) · [Idiomas da documentação](README.md)

Mellifon é uma aplicação SaaS independente na pasta `Voice-clonner-Application/`. Não importa código da aplicação YouTube existente nem utiliza a API dessa aplicação.

## Recursos e estado atual

- Cadastro, login, recuperação de senha, perfil e biblioteca privada de vozes.
- Envio de amostras, vozes clonadas salvas, conversão de texto em fala, reprodução, download WAV e histórico.
- Worker independente, SQLite, reserva atômica de créditos, reembolso em caso de falha e registro de uso.
- Assinaturas Stripe, Checkout, portal do cliente e webhooks com assinatura verificada.

A clonagem e a geração local foram verificadas com GPU real. Antes do lançamento público, é necessário configurar e testar Stripe, SMTP, HTTPS, backups e monitoramento. Testes simulados não comprovam pagamentos reais.

## Instalação e execução — Windows / PowerShell

Requer Python 3.12, uv e GPU NVIDIA compatível com CUDA. Os modelos são baixados na primeira execução; reserve espaço para os modelos e o PyTorch.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Na raiz do projeto, abra três terminais PowerShell separados e execute um comando em cada um:

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

Acesse **http://localhost:5173** e crie sua conta. A API pode ser verificada em `http://localhost:8010/api/health`. Contas gratuitas recebem 5.000 créditos uma única vez. A síntese custa 1 crédito por caractere; a clonagem custa 1.000 créditos por voz. Use o mesmo nome de host no frontend e na API.

## GPU e idiomas

O padrão `TTS_DEVICE=cuda:0` utiliza a primeira GPU NVIDIA. A instalação foi verificada em uma NVIDIA RTX A6000 com 48 GB de VRAM; isso não representa requisito mínimo nem garantia de desempenho. Verifique a GPU com `nvidia-smi`. Para usar CPU, defina `TTS_DEVICE=cpu` em `backend/.env`; a geração será mais lenta. Reinicie o worker após alterações e aguarde `worker.status: ready` em `/api/studio/options`.

Idiomas de fala: chinês, inglês, japonês, coreano, alemão, francês, russo, português, espanhol e italiano. `auto` detecta o idioma do texto. A seleção controla a síntese, mas não traduz o roteiro. A interface atual está em inglês.

## Verificação e implantação

Passaram 13 testes de backend, verificações de navegador em computador e celular e a sequência real voz predefinida → clone salvo → fala gerada. Qwen3-TTS roda localmente, sem chave de API externa de voz. Stripe e SMTP precisam de configuração separada. Não publique `.env`, áudios privados ou o banco de dados.

[README completa](../../README.md) · [Configuração e implantação](../setup.md) · [API](../api.md) · [Verificações](../verification.md)
