# Воспроизведение контрольной точки

Рабочий каталог пустой. Нужны Linux x86_64, Git, Python 3.12, Node.js, npm, curl, OpenSSL и PostgreSQL 16 с btree_gist. Команды выполняются в одном сетевом пространстве. Все сервисы слушают 127.0.0.1. В архиве есть исходный синтетический дамп; для нового независимого прогона генератор создаст другие UUID и временные метки.

```bash
mkdir -p runtime/prisma evidence
git init fresh
git -C fresh fetch --depth=1 https://github.com/stvelikiy-star/resort-os.git refs/heads/main refs/heads/design/marina-fl2-final-verified-delta-20261116
git -C fresh worktree add --detach ../old 984d17546dc9d7b6443cdcc376b03c62cdd64bd5
git -C fresh worktree add --detach ../new a6e368971ec1024e6c9cabf2fc8ffb0ff006443d
# В проведённом прогоне PG 16.10 собран из postgresql-16.10.tar.bz2:
# ./configure --prefix=<абсолютный путь>/runtime/pg16 --without-icu --without-readline --without-zlib
# make -j8 && make install && make -C contrib/btree_gist install
export PATH="$PWD/runtime/pg16/bin:$PATH"
python -m venv runtime/venv
runtime/venv/bin/pip install -r new/services/api/requirements.txt
cp old/packages/database/package*.json runtime/prisma/
(cd runtime/prisma && npm ci --no-audit --no-fund)
bash scripts/start-db.sh
export A=postgresql://audit@127.0.0.1:55431/marina_fixture
export B=postgresql://audit@127.0.0.1:55432/marina_fixture
DATABASE_URL=$A runtime/prisma/node_modules/.bin/prisma migrate deploy --schema old/packages/database/prisma/schema.prisma
runtime/venv/bin/python scripts/fixture.py
bash scripts/api.sh old >runtime/old-api.log 2>&1 & old_api=$!
# Дождаться GET http://127.0.0.1:18001/health = 200.
bash scripts/upgrade.sh
bash scripts/api.sh new >runtime/new-api.log 2>&1 & new_api=$!
# Дождаться готовности второго API.
for pair in 'old 18001' 'new 18002'; do
  set -- $pair
  curl --noproxy '*' -fsS "http://127.0.0.1:$2/openapi.json" >"evidence/openapi-$1.json"
done
psql "$B" -v ON_ERROR_STOP=1 -f scripts/new-roles.sql
py=runtime/venv/bin/python
$py scripts/matrix.py
$py scripts/readback.py ALPHA
$py scripts/site-modes.py old
$py scripts/site-modes.py new
$py scripts/staff-lifecycle.py
```

Для снимков браузера скопировать apps/admin, apps/staff, apps/web каждой версии в runtime/ui/{old,new}/{admin,staff,web}, выполнить npm ci в каждой копии. Запустить bash scripts/ui-start.sh в фоне. Установить python-пакет playwright и chromium-headless-shell той же версии, что chromium-common. Путь исполняемого файла в browser.py и edge-browser.py относится к распакованному Debian-пакету в runtime/headless. Общие файлы Chromium, в том числе icudtl.dat, должны находиться рядом с бинарным файлом. Затем выполнить python scripts/browser.py.

```bash
kill -TERM "$new_api"
wait "$new_api" || true
bash scripts/profiles.sh
bash scripts/api.sh new true ALPHA >runtime/edge-api.log 2>&1 & edge_api=$!
# Распаковать Caddy 2.11.2 для Linux в runtime/caddy.
bash scripts/edge.sh >runtime/edge.log 2>&1 & edge=$!
python scripts/edge-browser.py
$py scripts/concierge.py ALPHA
kill -TERM "$edge_api"
wait "$edge_api" || true
bash scripts/rollback-api.sh >runtime/rollback-api.log 2>&1 & rollback_api=$!
# После готовности сверить SHA-256 OpenAPI с old, /auth/me с исходной cookie.
curl --noproxy '*' -fsSb runtime/owner.jar http://127.0.0.1:18002/api/v1/auth/me
curl --noproxy '*' -fsS http://127.0.0.1:18002/openapi.json | sha256sum
kill -TERM "$rollback_api"
wait "$rollback_api" || true
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -keyout runtime/localhost.key -out runtime/localhost.crt -subj /CN=localhost -addext subjectAltName=IP:127.0.0.1
bash scripts/guest-tls.sh >runtime/tls-api.log 2>&1 & tls_api=$!
# После готовности этой локальной HTTPS-точки:
$py scripts/concierge.py BETA
python scripts/summarize.py
python scripts/inventory.py
```

Для независимого повтора использовать свежий каталог. После снимков B новые роли, агентская привязка, отключение/возврат тестового сотрудника, QR, PIN и EN-публикация служат только этапам 2–3. Для смены версии на месте импортировать исходный дамп в пустую БД и запустить OLD против неё, как в upgrade.sh и rollback-api.sh. Старый и новый кластеры и исходный дамп остаются раздельными. При завершении остановить только запущенные тестовые процессы и оба созданных кластера посредством pg_ctl -D с их путями. В архиве отсутствуют сырые cookie, PIN и TLS-ключи.
