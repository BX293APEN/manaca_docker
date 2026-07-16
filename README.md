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
  動作します (`start.sh` 参照)。USB(カードリーダー)・GPIOともroot権限が
  必要なため、あえて非rootユーザーへの降格は行っていません。
- GPIOへのアクセスは `compose.yml` の `devices` で個別デバイスのみを明示的に
  渡しています。USB(カードリーダー)は抜き差しでバス/デバイス番号が変わり
  うるため、`device_cgroup_rules` でUSBデバイスクラス(メジャー番号189)への
  読み書きのみを許可しています。`privileged: true` (ホストの全デバイス・
  全capabilityを渡す設定) は使用していません。
- gpiozeroのピン制御バックエンドは `lgpio` を使用しています
  (Raspberry Pi 5のRP1チップに対応するため)。
- 起動ラッパースクリプト (`start.sh`) のファイル名は `.env` の `ENTRY_POINT`
  で管理しています(既定値 `start.sh`)。名前を変更したい場合は、実ファイルを
  リネームした上で `ENTRY_POINT` の値を書き換えるだけでよく、`Dockerfile` /
  `compose.yml` 自体の編集は不要です。カード読み取り/LED制御を行う
  `start.py` は `start.sh` と同じディレクトリに固定ファイル名で配置されます。
