# rats-sentinell — reconstrução do projeto (a partir do histórico de sessões)

> Reconstruído em 2026-08-09 a partir de ~16 sessões antigas do Claude Code cujo `cwd` apontava
> para este projeto (a pasta em disco só tinha `.DS_Store` sobrando). Nada disto é 100% garantido
> — é o que sobreviveu nos transcripts — mas cobre arquitetura, endpoints, decisões de design e
> até bugs conhecidos.

## O que é o projeto

Um sistema que observa a câmera de um quarto/terrário de ratos e alerta quando um **gato** entra
numa "zona de perigo" (ex: a mesa ao lado do terrário). É um monorepo lógico com 4 serviços
independentes, cada um seu próprio repo git, orquestrados localmente por um script `tools/dev.sh`.

```
rats-sentinell/
├── camera/          # "jortan-camera-api" — bridge RTSP -> HTTP (porta 8001 / 9000 em dev)
├── cat-sentinel/     # detecção/tracking de gatos via YOLO (porta 8002 / 9001 em dev)
├── hub/              # API central que agrega e expõe pro frontend (porta 8000 / 9002 em dev)
├── hub_frontend/      # Next.js, consome o hub (porta 3000)
├── camera-hack/       # ferramentas de recon/exploit ONVIF pra essa câmera específica
├── yoosee-rtsp-stabilizer/  # notas sobre instabilidade do RTSP dessa câmera
├── docker/            # provavelmente docker-compose do Postgres
├── docs/               # README, ADRs, rats-sentinell-summary.md
└── history/            # ex: history/rats-sentinell-2026-07-29.md
```

Portas de dev (via `tools/dev.sh`): `camera=9000`, `cat-sentinel=9001`, `hub=9002` (mais recente),
mas em outra sessão os `.env` apontavam `camera=8001`, `cat-sentinel=8002`, `hub=8000`,
`hub_frontend=3000` — os dois esquemas coexistiram em momentos diferentes, confirme qual você
quer manter.

Hardware: câmera **Jortan JT-8172HJ** (chip AltoBeam / firmware tipo Yoosee/Anyka), RTSP na porta
554, ONVIF na porta 5000 (sem auth). É uma câmera fisicamente instável — precisa power-cycle
frequente, foi danificada uma vez por 43 conexões ffmpeg simultâneas.

---

## 1. `camera` (a.k.a. `jortan-camera-api`)

FastAPI, **screaming architecture** (pastas nomeadas pelo que o serviço faz, não por camada
técnica). Refatorado nesse formato num commit `ae39dc5` — "Reorganize app/ into screaming
architecture by domain".

```
app/
├── main.py, __main__.py
├── camera/       # viewer, stream, health, recording
│   router.py, schemas.py, service.py, templates/viewer.html
├── events/       # ingestão de gatilhos de detecção -> comandos de câmera
│   router.py, schemas.py, service.py, camera_command_dispatcher.py
├── webhooks/     # notificação de eventos pra fora
│   router.py, schemas.py, service.py
├── settings/     # config, logging, middleware
│   config.py, logging_config.py, middleware.py
└── core/         # decorators.py, dependencies.py, exceptions.py
```

### Endpoints

**Camera** — todos operam sobre um `RTSPCamera` (thread em background decodificando RTSP/HEVC
para um buffer de frame compartilhado):
- `GET /` — viewer HTML estático
- `GET /video` — MJPEG multipart, generator async, para quando o cliente desconecta OU quando o
  próprio `RTSPCamera.is_running()` desliga
- `GET /snapshot` — último JPEG
- `GET /status` — estado da conexão, transporte, último erro, idade do frame
- `POST /reset` — força reconectar
- `POST /recording/start|stop`, `GET /recording/status`, `GET /recordings`,
  `GET /recordings/{filename}` — grava a partir do mesmo buffer decodificado, sem competir com o
  live view

Tem um cliente RTSP/RTP feito à mão (`_RawRTSPHevcSource`) porque o libav é rígido demais pro
PLAY reply não-conforme (RFC 2326) dessa câmera específica.

**Events** (metade "in" do pipeline de detecção):
- `POST /events/trigger` — serviço externo de detecção reporta algo, mapeia pra comando de
  câmera, dispara, e faz fan-out via webhook
- `GET /events` — log recente (em memória, bounded)
- `GET/PUT/DELETE /events/commands/{event_type}` — tabela `event_type -> command` editável em
  runtime
- Dispatch atrás de um protocolo `CameraCommandDispatcher` — hoje só loga
  (`LoggingCameraCommandDispatcher`), a API de atuador real (sirene/luz/PTZ) nunca foi implementada
- Protegido por `require_api_key` (no-op a menos que `EVENTS_API_KEY` esteja setado)

**Webhooks** (metade "out"):
- `POST /webhooks` — assina URL pra receber cópia de cada evento (filtro opcional por
  `event_types`)
- `GET /webhooks`, `DELETE /webhooks/{id}`
- Fan-out best-effort, timeout 3s, nunca bloqueia/falha a request original

**Cross-cutting** (`settings/` + `core/`):
- Config via pydantic-settings (credenciais da câmera, transporte RTSP, portas, API key,
  log level/format)
- Logging estruturado correlacionado por request (`X-Request-ID` via contextvar)
- Decorators `log_call`/`log_errors` (ver seção de padrões compartilhados abaixo)
- Registry de exceção -> resposta HTTP autoregistrável

**Fora de escopo deliberadamente**: nenhum código de visão computacional/ML mora aqui — só move
vídeo e eventos. "Tem um gato na mesa?" é respondido por um microsserviço separado (`cat-sentinel`)
que consome `/video`/`/snapshot` e posta de volta em `/events/trigger`. Isso está documentado em
`docs/adr/0002-camera-api-scope-boundary.md`.

### Recording via Postgres
Numa sessão posterior, `GET /recordings` passou a ser DB-backed via Postgres (antes era
provavelmente listagem de arquivo). Tabela `recordings` criada via Alembic. Havia um scheduler
que roda a cada 300s por padrão.

---

## 2. `cat-sentinel`

FastAPI standalone (v0.1.0), também no padrão **domain-per-package**
(`app/<domínio>/{router,service,repository,schemas,models}.py`) — a mesma convenção da skill
"fastapi-builder". Detecta e rastreia gatos, alerta quando um entra numa zona de perigo.

```
app/
├── zones/, cats/, detections/, alerts/    # domínios REST
├── vision/          # detector.py (YOLOv8), tracker.py, annotator.py
├── streaming/        # client.py (RatSentinellStreamClient), frame_source.py, broadcaster.py, router.py
├── detections/pipeline.py   # DetectionPipeline — o loop principal, roda em background
├── core/             # decorators.py, dependencies.py, exceptions.py
└── settings/          # config.py, logging_config.py, middleware.py
```

### Pipeline de detecção (background task, inicia sozinho no boot)
Puxa frames do stream do `camera`, roda **YOLOv8** (classe COCO "cat"), rastreia cada gato entre
frames com ID persistente via **centroid tracker**, checa se está dentro de uma zona, persiste
cada observação, dispara webhook de alerta com cooldown anti-spam
(`AlertCooldownTracker`).

`DetectionPipeline.run_forever()` deliberadamente **não** é decorado com `@log_errors`/`@log_call`
— precisa sobreviver a exceção por frame sem matar o loop inteiro.

### Endpoints

| Domínio | Rotas | Notas |
|---|---|---|
| Meta | `GET /health` | liveness |
| Zones | `GET/POST /zones/`, `GET/PATCH/DELETE /zones/{id}` | polígono por câmera; ≥3 pontos; nome único (409); rejeita `inf`/`nan` nas coordenadas; polígono capado em 200 pontos |
| Cats | `GET /cats/`, `GET/PATCH /cats/{id}` | identidade auto-criada por gato rastreado; label (ex "Whiskers") ou `is_active=false` pra aposentar |
| Detections | `GET /detections/` | histórico paginado, read-only, filtra por `cat_id`/`in_danger_zone` |
| Alerts | `GET /alerts/` | histórico de alertas disparados + status/erro de entrega |
| Streaming | `GET /stream/annotated` | MJPEG com bounding boxes e nome do gato desenhados, colorido de vermelho se dentro da zona de perigo |
| Activities | `GET /activities/` | adicionado depois, junto com a migração pra Postgres |

Sem auth em v1 (rede interna confiável). Webhook de saída: `POST {ALERT_WEBHOOK_URL}` avisa o
`hub`/`camera` quando um gato entra numa zona.

### Componentes de streaming
- `AnnotatedFrameBroadcaster` — pub/sub em memória do último JPEG anotado; o pipeline é o único
  publisher, N clientes HTTP podem assinar sem trabalho extra do detector
- `FrameAnnotator` — desenha caixa + nome (ou `cat #<track_id>`)
- `app.state` recebe o broadcaster na criação do app (não dentro do `lifespan`), pra rota nunca
  dar 404/500 esperando o pipeline subir

### Migração pra Postgres
Originalmente SQLite. Migrado: `docker compose up -d` sobe Postgres com dois bancos
(`cat_sentinel`, `camera`) via script de init; `alembic upgrade head` roda em ambos.
`DATABASE_URL` em `cat-sentinel/.env` precisa apontar pro Postgres.

---

## 3. `hub`

FastAPI, API central que agrega `camera` + `cat-sentinel` pro frontend. Porta 8000 (ou 9002).

- `GET /trackers` — última bounding box por gato rastreado (JSON), lido do `cat-sentinel`
- `GET /stream/annotated` — faz proxy do MJPEG anotado do `cat-sentinel`, byte-a-byte, fecha a
  conexão upstream quando o cliente desconecta; retorna **502** (`UpstreamServiceError`) se o
  cat-sentinel estiver inacessível, em vez de 500 cru
- `dependencies.py`: `get_cat_sentinel_stream_client` — `httpx.AsyncClient` **sem timeout**,
  separado do client de controle normal (`CatSentinelClient`), porque um MJPEG longo não pode
  usar timeout de request

### Bug conhecido documentado (pode já estar corrigido, verificar)
`TrackerService.list_active_trackers` fazia `datetime.now(timezone.utc) - tracker.captured_at`,
mas `captured_at` vindo do `cat-sentinel` via JSON era **naive** (SQLite não guarda timezone de
verdade mesmo com `DateTime(timezone=True)`), causando `TypeError` (aware − naive) em runtime.
Os testes não pegavam isso porque o mock já gerava datas com offset. Correção sugerida: normalizar
tudo pra UTC-aware antes de comparar, ou usar `datetime.now()` naive dos dois lados.

---

## 4. `hub_frontend`

Next.js. Consome o `hub`.

- `app/api/trackers/route.ts` — proxy same-origin do `GET /trackers` do hub (JSON)
- `app/api/stream/route.ts` — proxy same-origin do `GET /stream/annotated` do hub, `force-dynamic`
  (Next não pode cachear), relay de corpo streamado em vez de JSON bufferizado
- `components/features/live-video-feed.tsx` — `LiveVideoFeed`, por padrão usa `/api/stream`;
  `NEXT_PUBLIC_STREAM_URL` vira override opcional pra outro feed
- Página `/live`

---

## 5. Padrões compartilhados entre os 3 backends FastAPI

Todos seguem a skill interna "fastapi-builder" — vale recriar esse `SKILL.md` também se quiser
manter a consistência. Pontos-chave:

### Layout por domínio (não por camada técnica)
```
app/<domínio>/
├── router.py       # fino: parseia via Pydantic, chama service, retorna schema
├── schemas.py       # Create / Update (tudo opcional) / Read (from_attributes=True)
├── models.py         # SQLAlchemy 2.0, Mapped[...]/mapped_column
├── service.py         # lógica de negócio, decorado com @log_errors
└── repository.py       # só query, sem lógica
```
`settings/` (config, logging, middleware — como o app é configurado como um todo) é separado de
`core/` (dependencies, decorators, exceptions — machinery que o código de domínio usa
diretamente).

### `core/decorators.py`
```python
def log_call(func):
    # debug em toda chamada, error+traceback + re-raise em exceção
    # detecta sync/async uma vez via inspect.iscoroutinefunction na hora da decoração
    ...

def log_errors(cls):
    # aplica log_call a todo método público (pula _private e dunder)
    ...
```
Contrato: decorators só decidem *o quê* logar (`extra={"event", "target"}`), nunca o *como*
formatar — isso é 100% responsabilidade do `logging_config.py`. Um `JsonLogFormatter` genérico
que faz passthrough de todo campo não-reservado do `record.__dict__` pega esses campos de graça.

Regra de quando pular o decorator: métodos em **hot path** (stream de frame, tick de websocket,
polling apertado — ex `RTSPCamera.get_frame()`, `RatSentinellStreamClient`, `YoloCatDetector`,
`DetectionPipeline.run_forever`) ficam sem decorator, com comentário explicando por quê.

### `core/exceptions.py`
Registry autoregistrável via decorator `@exception_handler(ExcType)`, uma chamada
`register_exception_handlers(app)` no `main.py` — nunca hand-wiring por exceção.
Exceções base: `NotFoundError`→404, `InvalidRequestError`→400, `UnauthorizedError`→401,
`ConflictError`→409 (domínios sobem subclasses locais, ex `RecordingAlreadyInProgressError`),
`FrameNotAvailableError`→503.

Bug corrigido em `cat-sentinel`: o handler default de `RequestValidationError` do FastAPI dava
500 quando o valor rejeitado era `inf`/`nan` (não serializável); registraram handler próprio que
sanitiza o valor ecoado.

### Uniqueness constraint pattern (repository)
Nunca fazer "SELECT antes de inserir" como única guarda — é racy. A constraint `unique=True` no
model é a fonte de verdade; o repository captura `sqlalchemy.exc.IntegrityError`, dá
`session.rollback()` (senão a sessão fica em estado de transação falha) e levanta `ConflictError`.

### `settings/middleware.py`
`RequestContextMiddleware` — único middleware "de verdade" (roda pra toda request, inclusive
404/erro não tratado): gera `request_id` (`X-Request-ID`), timing, log de uma linha por request.
Tudo mais (auth, paginação, feature flags) é dependency, não middleware.

### Testes
`pytest` + `httpx.AsyncClient` via `ASGITransport`. Fixture padrão `db_session`/`client` em
`conftest.py`, SQLite in-memory. MJPEG streams testados direto contra
`StreamingResponse.body_iterator` (ASGITransport não consegue dirigir stream infinito).

### Alembic
`file_template` com timestamp prefix (não o slug default), pra evitar colisão entre branches
paralelas: `%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s`.

---

## 6. `camera-hack/` — recon/ferramentas pra essa câmera específica

Ferramentas de pentest/recon voltadas à câmera Jortan/Yoosee, feitas em contexto autorizado
(o próprio dono da câmera). Pontos relevantes:

- `docs/sc-b21-recon.md` — mapeamento de portas: firmware atual já fechou 6000 (libcloudapi),
  6789 (daemon), 8192/udp (Anyka discovery), 21/23/80/2323/8080/9527. Confirmado por
  `nmap -sS -Pn` que essas portas continuam fechadas (a câmera só responde a SYN scan de verdade,
  não `connect()` normal).
- **ONVIF (porta 5000) é o caminho que funciona**, sem auth. `tools/onvif_fuzzer/` tem templates
  de comando. Comandos confirmados seguros: `ContinuousMove`, `GetProfiles`, `SystemReboot`.
  Comandos que **crasham** o processo ONVIF/IPC (evitar): `CreateUsers`, `SetHostname`,
  `GetUsers`, `GetScopes`, `GetDNS`, `GetSystemDateAndTime` (intermitente), `GetAudioSources`,
  `GetSnapshotUri`, `Stop` (PTZ, só se chamado depois de `ContinuousMove`).
- `yoosee_proxy.py` — já demonstrou controle PTZ real via ONVIF.
- `tools/intercom/intercom.py` — canal de áudio reverso (backchannel) via comando RTSP
  customizado do firmware Yoosee (`USER_CMD_SET .../onvif1`, `Content-type: AudioCtlCmd:OPEN`).
  Tem dois bugs de protocolo documentados: `Content-length` é literalmente `strlen("Content-type")`
  (bug do firmware), e o campo de tamanho do frame RTP interleaved é little-endian nesse canal
  (todo o resto do RTSP da câmera é big-endian). Áudio: PCM s16le mono, 8kHz ou 16kHz.
- `camera_hack/sdcard_hack_autorun/README.txt` — se um SD card com `debug.ini` estiver inserido,
  a câmera boota em `anyka_ipc_nostrip` (modo debug/telnet) em vez do serviço IPC normal, o que
  quebra o handshake RTSP normal (DESCRIBE retorna 400 mesmo com credenciais corretas). Fix:
  remover o SD card e reiniciar.
- O objetivo real declarado era ligar `/events/trigger` do `camera` a um
  `OnvifCameraCommandDispatcher` de verdade (trocando o `LoggingCameraCommandDispatcher` stub em
  `app/core/dependencies.py`) — isso **não chegou a ser implementado**, ficou como próximo passo.

---

## 7. Docs que existiam no projeto

- `README.md` (raiz) — com diagramas Mermaid coloridos: componente/arquitetura (external actors →
  API routes → core → services, colorido por camada), pipeline de stream (RTSP → decode →
  MJPEG/snapshot/recording), sequência de eventos (vision service → trigger → command dispatch →
  webhook fan-out)
- `.github/copilot-instructions.md`
- `docs/adr/0001-layered-fastapi-architecture.md`
- `docs/adr/0002-camera-api-scope-boundary.md` — a regra de "CV/ML não mora no `camera`"
- `docs/rats-sentinell-summary.md`
- `history/rats-sentinell-2026-07-29.md`

Nenhum desses conteúdos foi capturado literalmente nos transcripts (só resumos do que foi
mudado), então precisam ser reescritos do zero — mas a estrutura acima dá o essencial pra
reconstruir o README com os 3 diagramas.

---

## O que NÃO foi possível recuperar

- Código-fonte real (nenhuma sessão tinha o conteúdo completo dos arquivos capturado de forma
  reconstituível — só diffs/trechos)
- `docker/` compose file exato (só sei que sobe Postgres com dois bancos)
- Conteúdo literal do README/ADRs
- Se a migração Postgres do `hub` também aconteceu, ou só `camera`+`cat-sentinel`
- Se o `OnvifCameraCommandDispatcher` real chegou a ser implementado em alguma sessão mais
  recente que eu não tenha encontrado

## Sugestão de ordem pra recriar

1. `cat-sentinel` primeiro (mais documentado: todos os endpoints, pipeline, schemas)
2. `camera` (bridge RTSP, bem documentado também)
3. `core`/`settings` compartilhados — extrair pra uma skill/template já que os 3 repetem o mesmo
   padrão
4. `hub` (mais simples, é basicamente 2 endpoints de agregação/proxy)
5. `hub_frontend` (Next.js, 2 rotas de API + 1 componente)
6. Portar `camera-hack/` só se você ainda tiver a câmera física pra reconfirmar as portas —
   firmware pode ter mudado de novo
