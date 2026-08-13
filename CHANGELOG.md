# Changelog

## [Unreleased]

- Corrige a gravação MP4: usa os valores lowercase do enum PostgreSQL, finaliza o contêiner com `moov`, encerra gravações quando o encoder falha e recupera registros abertos órfãos.
- Executa as migrações Alembic do `cat-sentinel` antes de iniciar a API no Docker Compose.
- Corrige a inicialização do `hub` para permitir a rota `DELETE /zones/{zone_id}` com status 204.
- Salva um snapshot JPEG por entrada de gato e registra seu caminho em `detections.snapshot_path`.
- Aumenta o tamanho de `activities.kind` para suportar `ENTERED_FRAME`.
- Exibe snapshots, nomes, caixas, confiança e idade dos gatos rastreados no live do hub.
- Adiciona proxy seguro de snapshots entre `cat-sentinel`, hub e frontend.
- Separa identidades detectadas (`detected_cats`) dos perfis cadastrados (`registered_cats`).
- Adiciona cadastro manual de gato com nome, nascimento, sexo e descrição.
- Permite várias imagens de referência por gato cadastrado e associa novas detecções por similaridade visual.
- Mantém o snapshot da nova entrada em `detections` mesmo quando a identidade é associada a um gato cadastrado.
- Reduz o MJPEG ao vivo para qualidade JPEG 60 e cerca de 10 fps, sem alterar a qualidade das gravações RTSP.
- Faz o hub consumir o MJPEG diretamente da API da câmera; o detector passa a expor somente métricas, tracking, alertas e snapshots.
- Corrige a tela live para remover o overlay após o primeiro frame MJPEG e libera o endereço LAN configurável no Next em desenvolvimento.
- Armazena, em cada nova entrada, o frame completo, horário UTC exato, `track_id` e bounding box no registro de detecção para reconstruir a seleção.
