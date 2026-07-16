#!/bin/bash
# ==========================================
# entrypoint.sh
#
# | 処理順序 | 内容 |
# | --- | --- |
# | 1 | pcscd (PC/SCデーモン) をバックグラウンドで起動 (root権限が必要) |
# | 2 | pcscdの起動を待機 |
# | 3 | 一般ユーザーに降格してPythonのエントリーポイントを実行 |
#
# | 参照する環境変数 | 内容 |
# | --- | --- |
# | USER_NAME | 実行ユーザー名 (Dockerfileで ENV 済み) |
# | ENTRY_DIR | エントリーポイントの配置ディレクトリ |
# | ENTRY_POINT | エントリーポイントのファイル名 |
#
# ==========================================
set -e

# pcscdをバックグラウンドで起動 (USBデバイスへのアクセスにroot権限が必要)
/usr/sbin/pcscd --foreground &

# pcscdの起動を待機
sleep 2

# 一般ユーザー権限でPythonのエントリーポイントを実行
exec su "${USER_NAME}" -c "python3 '/home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}'"
