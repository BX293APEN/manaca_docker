# linux_data フォルダについて

`compose.yml` の `VOLUME` 設定により、このフォルダはコンテナ内の
`/home/${USER_NAME}/${WS}` (既定値: `/home/PEN/WS`) にマウントされます。
`requirements.txt` はDockerfileのビルド時にも読み込まれるため、
ビルドコンテキスト配下 (`Dockerfile` と同じ階層) に置く必要があります。

## 構成

| ファイル | 内容 |
| --- | --- |
| requirements.txt | `start.py` 実行に必要なPythonパッケージ一覧 (ビルド時に使用) |
| README.md | このファイル |

## セットアップ手順 (Raspberry Pi 5 ホスト側)

| 手順 | 内容 |
| --- | --- |
| 1 | ホスト側でICカードリーダーをUSB接続し `lsusb` で認識を確認する |
| 2 | `ls /dev/gpiochip*` を実行し、Pi 5のGPIOチップ番号 (通常 `gpiochip4`) を確認する |
| 3 | 番号が異なる場合は `compose.yml` の `devices` を実際の値に合わせて修正する |
| 4 | `.env` の内容 (ユーザー名・パスワード・ポート番号等) を必要に応じて変更する |
| 5 | `docker compose up --build` でビルド & 起動する |
| 6 | LED (GPIO18) が消灯した状態で起動し、ICカードをタッチするたびに点灯/消灯が切り替わることを確認する |

## 注意事項

- `pcscd` (PC/SCデーモン) と Pythonスクリプト (`start.py`) はどちらもroot権限で
  動作します (`entrypoint.sh` 参照)。USB(カードリーダー)・GPIOともroot権限が
  必要なため、あえて非rootユーザーへの降格は行っていません。
- GPIOへのアクセスには `compose.yml` 側で `privileged: true` を設定しているため、
  検証環境以外でそのまま使う場合はセキュリティ要件に応じて絞り込みを検討してください。
- gpiozeroのピン制御バックエンドは `lgpio` を使用しています
  (Raspberry Pi 5のRP1チップに対応するため)。
