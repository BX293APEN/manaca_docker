#!/bin/bash
# ==========================================
# entrypoint.sh
#
# | 処理順序 | 内容 |
# | --- | --- |
# | 1 | pcscd (PC/SCデーモン) をバックグラウンドで起動 |
# | 2 | pcscdの起動を待機 |
# | 3 | Pythonのエントリーポイントを実行 |
#
# | 備考 |
# | --- |
# | pcscd(USBアクセス)・gpiozero(GPIOアクセス)とも root権限が必要なため、 |
# | コンテナはroot権限のまま動作させている(非rootへの降格は行わない)。 |
#
# | 参照する環境変数 | 内容 |
# | --- | --- |
# | USER_NAME | ホームディレクトリのパス組み立てに使用 (Dockerfileで ENV 済み) |
# | ENTRY_DIR | エントリーポイントの配置ディレクトリ |
# | ENTRY_POINT | エントリーポイントのファイル名 |
#
# ==========================================
set -e

# pcscdをバックグラウンドで起動 (USBデバイスへのアクセスにroot権限が必要)
/usr/sbin/pcscd --foreground &

# pcscdの起動を待機
sleep 2

# Pythonのエントリーポイントを実行 (rootのまま)
exec python3 "/home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}"
