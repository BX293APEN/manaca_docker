# manaca_docker

Docker上でFelica (交通系ICカード) リーダーを認識させ、ICカードがタッチされるたびに
LEDの点灯/消灯を切り替えるプロジェクト。

## 構成ファイル

| ファイル | 内容 |
| --- | --- |
| `host.sh` | **ホスト側**でコンテナ起動前に1回実行するセットアップスクリプト |
| `compose.yml` | コンテナの定義 (GPIO/USBデバイスの受け渡し設定を含む) |
| `Dockerfile` | pcscd / PC-SC 関連パッケージ、Pythonライブラリのインストール |
| `.env` | `compose.yml` / `Dockerfile` で参照する環境変数 |
| `start.sh` | コンテナのエントリーポイント (dbus/polkitd/pcscd起動 → `start.py`実行) |
| `start.py` | カード読み取り/LED制御の本体 |

## セットアップ手順

```bash
# 1. ホスト側の準備 (root権限で1回だけ実行)
#    NFCカーネルモジュール (nfc / pn533 / pn533_usb / port100 等) が
#    ロードされている場合、Felicaリーダー(USB)をpcscdより先に横取りしてしまい、
#    `lsusb` には表示されるのに `pcsc_scan` / `SCardListReaders` からは
#    一切見えない、という現象が起きる。host.sh はこれをブラックリスト登録して回避する。
sudo ./host.sh

# 2. コンテナのビルド & 起動
docker compose up --build -d
```

## 動作確認

| 確認コマンド | 実行場所 | 期待する結果 |
| --- | --- | --- |
| `lsmod \| grep -iE 'nfc\|pn533\|port100'` | ホスト | 何も表示されない (host.sh実行後) |
| `lsusb` | ホスト / コンテナ両方 | Felicaリーダーの行が表示される |
| `pcsc_scan` | コンテナ内 (`docker exec -it manaca_checker bash`) | リーダー名が表示され、カードタッチでATRが取得できる |
| `docker compose logs -f` | ホスト | ICカードタッチのたびにIDm/ATS/LED状態が出力される |

## GPIOチップ番号について

`.env` の `GPIOCHIP` はRaspberry Piの機種/カーネルによって異なる。
40ピンヘッダに対応する番号は以下で確認できる。

```bash
gpiodetect
# "pinctrl-rp1" と表示されている行の gpiochipN を .env の GPIOCHIP に設定する
```

## トラブルシューティング

| 症状 | 想定原因 | 対処 |
| --- | --- | --- |
| `lsusb` にリーダーが出てこない (ホスト側から既にない) | 物理的な接続不良 / USBケーブル・ポート不良 | 別のUSBポート/ケーブルで確認 |
| `lsusb` には出るが `pcsc_scan` に出てこない | ホストのNFCカーネルモジュールに横取りされている | `host.sh` を実行 (未実行の場合) |
| `host.sh` 実行後も改善しない | `rmmod` に失敗し再起動が必要な状態のまま | `sudo reboot` してから再確認 |
| コンテナ内 `lsusb` にも出ない | `device_cgroup_rules` のメジャー番号不一致、または docker設定の問題 | `ls -l /dev/bus/usb/*/*` でメジャー番号を確認。切り分けのため一時的に `compose.yml` の `privileged: true` を有効化して再検証 |
| `Failed to establish context : Access denied.` | dbus/polkitdが起動していない | `start.sh` が正常に実行されているかコンテナログを確認 |
| `Another pcscd seems to be running.` | 異常終了時の `/run/pcscd` の残骸 | コンテナ再起動 (`start.sh` が起動時に自動で掃除する) |
