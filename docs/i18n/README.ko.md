# Sonora · 음성 복제 및 음성 생성 플랫폼

[English](../../README.md) · [문서 언어 선택](README.md)

Sonora는 `Voice-clonner-Application/` 폴더 안에서 독립적으로 실행되는 음성 SaaS입니다. 기존 YouTube 앱의 코드를 가져오거나 해당 앱의 API를 호출하지 않습니다.

## 기능과 현재 상태

- 회원가입, 로그인, 비밀번호 재설정, 프로필 및 사용자별 비공개 음성 라이브러리.
- 음성 샘플 업로드, 복제 음성 저장, 텍스트 음성 변환, 미리 듣기, WAV 다운로드 및 생성 기록.
- 별도 백그라운드 worker, SQLite, 크레딧 예약 차감, 실패 시 반환 및 사용 내역.
- Stripe 구독, 결제 페이지, 고객 포털 및 서명 검증 webhook 연동.

로컬 음성 복제와 생성은 실제 GPU로 검증했습니다. 서비스 공개 전에는 Stripe, SMTP 이메일, HTTPS, 백업 및 모니터링을 설정하고 검증해야 합니다. 모의 결제 테스트는 실제 결제 검증을 대신하지 않습니다.

## 설치와 실행 — Windows / PowerShell

Python 3.12, uv, CUDA를 지원하는 NVIDIA GPU가 필요합니다. 모델은 처음 실행할 때 내려받으므로 모델과 PyTorch를 위한 디스크 공간도 확보하세요.

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

프로젝트 루트에서 PowerShell 창 세 개를 열고 각각 다음 명령 중 하나를 실행하세요.

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

**http://localhost:5173** 에 접속해 계정을 만드세요. API 상태 주소는 `http://localhost:8010/api/health`입니다. 무료 계정에는 가입 시 한 번 5,000크레딧이 제공됩니다. 음성 생성은 문자당 1크레딧, 음성 복제는 건당 1,000크레딧입니다. 프런트엔드와 API에는 같은 호스트 이름을 사용하세요.

## NVIDIA GPU와 지원 언어

기본값 `TTS_DEVICE=cuda:0`은 첫 번째 NVIDIA GPU를 사용합니다. VRAM 48GB인 NVIDIA RTX A6000에서 확인했으며, 이 사양은 최소 요구사항이나 성능 보장이 아닙니다. `nvidia-smi`로 GPU 상태를 확인할 수 있습니다. CPU를 사용하려면 `backend/.env`에 `TTS_DEVICE=cpu`를 설정하세요. 생성 속도는 느려집니다. 설정 변경 후 worker를 재시작하고 `/api/studio/options`의 `worker.status`가 `ready`가 될 때까지 기다리세요.

중국어, 영어, 일본어, 한국어, 독일어, 프랑스어, 러시아어, 포르투갈어, 스페인어, 이탈리아어를 지원합니다. `auto`는 원고의 언어를 자동으로 감지합니다. 언어 선택은 음성 생성용이며 원고를 번역하지 않습니다. 현재 앱 화면은 영어로 제공됩니다.

## 검증과 배포

백엔드 테스트 13개, 데스크톱·모바일 브라우저 검사, 실제 프리셋 음성 → 저장된 복제 음성 → 새 음성 생성 과정을 확인했습니다. 음성 엔진은 로컬 Qwen3-TTS를 사용하므로 외부 음성 API 키가 필요하지 않습니다. Stripe와 SMTP는 별도로 설정해야 합니다. `.env`, 비공개 음성 및 데이터베이스를 저장소에 올리지 마세요.

[전체 README](../../README.md) · [설정과 배포](../setup.md) · [API](../api.md) · [검증 기록](../verification.md)
