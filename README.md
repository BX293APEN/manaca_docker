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
| 2 | `gpiodetect` (要 `sudo apt install gpiod`) を実行し、`pinctrl-rp1` と表示された行のgpiochip番号を確認する (機種/カーネルにより `gpiochip0` だったり `gpiochip4` だったりする) |
| 3 | 番号が異なる場合は `.env` の `GPIOCHIP` / `GPIOMEM` を実際の値に書き換える (`compose.yml`の編集は不要) |
| 4 | `.env` の内容 (ユーザー名・パスワード・ポート番号等) を必要に応じて変更する |
| 5 | `docker compose up --build` でビルド & 起動する |
| 6 | LED (GPIO18) が消灯した状態で起動し、ICカードをタッチするたびに点灯/消灯が切り替わることを確認する |

## 注意事項

- `pcscd` (PC/SCデーモン) と Pythonスクリプト (`start.py`) はどちらもroot権限で
  動作します (`start.sh` 参照)。USB(カードリーダー)・GPIOともroot権限が
  必要なため、あえて非rootユーザーへの降格は行っていません。
- GPIOへのアクセスは `compose.yml` の `devices` で個別デバイスのみを明示的に
  渡しています。デバイスパス自体は `.env` の `GPIOCHIP` / `GPIOMEM` で管理して
  いるため、機種やカーネルにより番号が変わっても `.env` を直すだけで済みます。
  USB(カードリーダー)は抜き差しでバス/デバイス番号が変わりうるため、
  `device_cgroup_rules` でUSBデバイスクラス(メジャー番号189)への読み書きの
  みを許可しています。`privileged: true` (ホストの全デバイス・全capabilityを
  渡す設定) は既定では使用せず、切り分け用としてコメントアウトのまま残して
  あります。
- gpiozeroのピン制御バックエンドは `lgpio` を使用しています
  (Raspberry Pi 5のRP1チップに対応するため)。
- 起動ラッパースクリプト (`start.sh`) のファイル名は `.env` の `ENTRY_POINT`
  で管理しています(既定値 `start.sh`)。名前を変更したい場合は、実ファイルを
  リネームした上で `ENTRY_POINT` の値を書き換えるだけでよく、`Dockerfile` /
  `compose.yml` 自体の編集は不要です。カード読み取り/LED制御を行う
  `start.py` は `start.sh` と同じディレクトリに固定ファイル名で配置されます。
