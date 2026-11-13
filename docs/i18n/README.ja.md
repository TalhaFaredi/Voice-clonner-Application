# Sonora · 音声クローンと音声生成プラットフォーム

[English](../../README.md) · [ドキュメントの言語](README.md)

Sonora は `Voice-clonner-Application/` 内で独立して動作する音声 SaaS です。既存の YouTube アプリのコードをインポートしたり、その API を呼び出したりしません。

## 機能と現在の状態

- アカウント登録、ログイン、パスワード再設定、プロフィール、非公開の音声ライブラリ。
- 参照音声のアップロード、クローンの保存、テキスト読み上げ、試聴、WAV ダウンロード、生成履歴。
- 独立したバックグラウンド worker、SQLite、クレジットの予約、失敗時の返還、利用記録。
- Stripe のサブスクリプション、Checkout、Customer Portal、署名検証付き webhook。

ローカルでの音声クローンと生成は実際の GPU で確認済みです。公開運用には Stripe、SMTP メール、HTTPS、バックアップ、監視の設定と検証が必要です。模擬決済テストは実際の決済確認ではありません。

## インストールと起動（Windows / PowerShell）

Python 3.12、uv、CUDA 対応 NVIDIA GPU を用意してください。初回起動時にモデルをダウンロードするため、モデルと PyTorch 用のディスク容量も必要です。

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

プロジェクトのルートで PowerShell を三つ開き、それぞれ一つずつ実行します。

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

**http://localhost:5173** を開き、自分のアカウントを登録します。API の確認先は `http://localhost:8010/api/health` です。無料アカウントには初回のみ 5,000 クレジットが付与されます。読み上げは 1 文字につき 1、クローン作成は 1 回につき 1,000 クレジットです。フロントエンドと API には同じホスト名を使用してください。

## GPU と対応言語

既定の `TTS_DEVICE=cuda:0` は最初の NVIDIA GPU を使用します。48 GB VRAM の NVIDIA RTX A6000 で確認済みですが、これは最小要件や処理速度の保証ではありません。`nvidia-smi` で状態を確認できます。CPU を使う場合は `backend/.env` に `TTS_DEVICE=cpu` を指定しますが、処理は遅くなります。設定後は worker を再起動し、`/api/studio/options` の `worker.status` が `ready` になるまで待ちます。

中国語、英語、日本語、韓国語、ドイツ語、フランス語、ロシア語、ポルトガル語、スペイン語、イタリア語に対応します。`auto` は原稿の言語を自動判定します。言語選択は読み上げ用であり、原稿を翻訳する機能ではありません。現在の UI は英語です。

## 検証と公開運用

13 件のバックエンドテスト、デスクトップ／モバイルのブラウザ確認、実際のプリセット音声 → 保存したクローン → 音声生成を実施しました。音声エンジンはローカルの Qwen3-TTS を使用し、外部の音声 API キーは不要です。Stripe と SMTP の設定は別途必要です。`.env`、非公開音声、データベースをコミットしないでください。

[完全版 README](../../README.md) · [設定とデプロイ](../setup.md) · [API](../api.md) · [検証記録](../verification.md)
