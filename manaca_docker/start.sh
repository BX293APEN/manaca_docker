#!/bin/bash
# ==========================================
# start.sh (ENTRY_POINT)
#
# compose.yml の command から直接実行されるラッパースクリプト。
# .env の ENTRY_POINT にファイル名を設定しているため、
# 変更する場合は「このファイルをリネーム」+「.envのENTRY_POINTを書き換え」
# の2点だけでよい (Dockerfile / compose.yml の編集は不要)。
#
# | 処理順序 | 内容 |
# | --- | --- |
# | 1 | dbus-daemon (D-Bus システムバス) をバックグラウンドで起動 |
# | 2 | polkitd (PolicyKit) をバックグラウンドで起動 |
# | 3 | pcscdの残骸ソケット/PIDファイルを削除 |
# | 4 | pcscd (PC/SCデーモン) をバックグラウンドで起動 |
# | 5 | pcscdの起動を待機 |
# | 6 | WORKDIR (python/main.py) を実行 |
#
# | 備考 |
# | --- |
# | pcscdはクライアントの認可にpolkitを使用しており、polkitはD-Busが無いと |
# | 動作しない。コンテナにはsystemdが無くdbus/polkitが自動起動しないため、 |
# | ここで明示的に起動しておかないと |
# | `Failed to establish context : Access denied.` になる。 |
# | `restart: unless-stopped` はコンテナを再作成せず再起動するため、 |
# | 異常終了時の /run/pcscd の残骸が残ると `Another pcscd seems to be |
# | running.` となり `Failed to establish context : Service not |
# | available.` になる。そのため起動前に /run/pcscd を作り直している。 |
# | pcscd(USBアクセス)・gpiozero(GPIOアクセス)とも root権限が必要なため、 |
# | コンテナはroot権限のまま動作させている(非rootへの降格は行わない)。 |
# | 実行対象の python/main.py は Dockerfile の WORKDIR (= /home/<USER_NAME>/<WS>) |
# | からの相対パスで解決するため、環境変数を経由せずに済んでいる。 |
#
# ==========================================
set -e

# ==========================================
# D-Bus システムバスを起動
# pcscdのクライアント認可(polkit)に必要
# ==========================================
rm -rf /run/dbus
mkdir -p /run/dbus
dbus-daemon --system --fork

# ==========================================
# polkitd を起動
# インストール先はディストリのバージョンにより異なるため候補を順に探す
# ==========================================
for POLKITD_BIN in "$(command -v polkitd 2>/dev/null)" /usr/lib/policykit-1/polkitd /usr/libexec/polkitd /usr/lib/*/polkit-1/polkitd; do
    if [ -n "${POLKITD_BIN}" ] && [ -x "${POLKITD_BIN}" ]; then
        "${POLKITD_BIN}" --no-debug &
        break
    fi
done

# D-Bus / polkitd の起動を待機
sleep 10

mkdir -p /run/pcscd

# pcscdをバックグラウンドで起動 (USBデバイスへのアクセスにroot権限が必要)
/usr/sbin/pcscd --foreground &

sleep 10 # pcscdの起動を待機

# WORKDIR (/home/<USER_NAME>/<WS>) 直下の python/main.py を実行 (rootのまま)
exec python3 python/main.py
