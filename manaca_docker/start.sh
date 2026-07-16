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
# | 1 | pcscd (PC/SCデーモン) をバックグラウンドで起動 |
# | 2 | pcscdの起動を待機 |
# | 3 | 同じディレクトリに配置されている start.py を実行 |
#
# | 備考 |
# | --- |
# | pcscd(USBアクセス)・gpiozero(GPIOアクセス)とも root権限が必要なため、 |
# | コンテナはroot権限のまま動作させている(非rootへの降格は行わない)。 |
# | 実行対象の start.py は自分自身と同じディレクトリから解決するため、 |
# | 環境変数を経由せずに済んでいる。 |
#
# ==========================================
set -e

# 自分自身が置かれているディレクトリ (= ENTRY_DIR) を取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# pcscdをバックグラウンドで起動 (USBデバイスへのアクセスにroot権限が必要)
/usr/sbin/pcscd --foreground &

# pcscdの起動を待機
sleep 2

# 同じディレクトリの start.py を実行 (rootのまま)
exec python3 "${SCRIPT_DIR}/start.py"
