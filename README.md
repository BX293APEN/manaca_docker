# manaca_docker

FeliCa Port/PaSoRi（RC-S300 など）を USB 接続し、Docker コンテナ内から
[pyscard](https://pypi.org/project/pyscard/)（PC/SC ラッパー）経由で
manaca / Suica などの交通系 IC カードの IDm・ATS を読み取るプロジェクトです。
Raspberry Pi 5 上の Ubuntu コンテナで動かすことを想定しています。

---

## プロジェクト構成

| パス | 内容 |
| --- | --- |
| `manaca_docker/Dockerfile` | 実行環境（Ubuntu 25.10 + pcscd/pyscard 等）の定義 |
| `manaca_docker/compose.yml` | コンテナ起動設定（USBデバイスの受け渡し等） |
| `manaca_docker/.env` | `compose.yml` / `Dockerfile` で使う環境変数 |
| `manaca_docker/host.sh` | コンテナ起動前にホスト側で1回だけ実行するセットアップスクリプト |
| `manaca_docker/start.sh` | コンテナのエントリーポイント（pcscd 等を起動し `main.py` を実行） |
| `manaca_docker/linux_data/python/main.py` | 常駐して IDm/ATS を読み取り続けるエントリースクリプト |
| `manaca_docker/linux_data/python/lib/manaca_reader.py` | カードリーダー制御ライブラリ（`SmartCardReaderSetup`） |

`linux_data` ディレクトリは `compose.yml` の `volumes` 設定によりコンテナ内の
`/home/<USER_NAME>/<WS>` にそのままマウントされます。そのため `main.py` や
`lib/manaca_reader.py` を編集した場合、コンテナを再ビルドしなくても
再起動するだけで変更が反映されます。

---

## 動作確認環境

| 項目 | 内容 |
| --- | --- |
| カードリーダー | Sony FeliCa Port/PaSoRi 4.0（RC-S300 シリーズ） |
| プロトコル | PC/SC (CCID) |
| 実行環境 | Docker / Docker Compose（ホストは Raspberry Pi 5 等の Linux を想定） |
| ベースイメージ | ubuntu:25.10 |

---

## セットアップ

### 1. ホスト側の準備（初回のみ）

Sony PaSoRi はホストの標準 NFC ドライバ（`port100` など）に先に
USB インターフェースを奪われてしまうことがあり、その場合は `pcscd` から
カードリーダーが一切見えなくなります。これを防ぐため、コンテナを起動する前に
ホスト側で1回だけ `host.sh` を実行してください。

`host.sh` は `.env` の `PLATFORM` を見て処理を切り替えます。

| `PLATFORM` | 実行環境 | 処理内容 |
| --- | --- | --- |
| `linux`（デフォルト） | Raspberry Pi 等のネイティブLinux | NFC関連カーネルモジュールをブラックリスト登録（要 `sudo`） |
| `windows` | Windows + Docker Desktop (WSL2) | Linux側の処理はスキップし、[usbipd-win](https://github.com/dorssel/usbipd-win) でのUSBアタッチ手順を案内（root不要） |

```bash
# Raspberry Pi など (PLATFORM=linux のとき)
sudo ./manaca_docker/host.sh

# Windows + Docker Desktop (WSL2) で試す場合は、.env の PLATFORM を
# windows に変更してから、WSLのターミナル等で実行する
./manaca_docker/host.sh
```

`PLATFORM=windows` の場合、`host.sh` はLinuxカーネルモジュールの操作は行わず、
`usbipd bind` / `usbipd attach --wsl` を管理者権限のPowerShellで実行するよう
案内するだけで終了します。

### 2. `.env` の確認・編集

`manaca_docker/.env` にコンテナ名やユーザー名、タイムゾーンなどが
設定されています。必要に応じて書き換えてください。

| 変数名 | 内容 |
| --- | --- |
| `CONTAINER_NAME` | コンテナ名 |
| `USER_NAME` / `PASSWORD` | コンテナ内に作成するユーザーとパスワード |
| `TIME_ZONE` / `LANG` | コンテナのタイムゾーン・ロケール |
| `ENTRY_DIR` / `ENTRY_POINT` | エントリーポイントスクリプトの配置先・ファイル名 |
| `PLATFORM` | `host.sh` が参照する実行環境（`linux` / `windows`） |

### 3. コンテナのビルド・起動

```bash
cd manaca_docker
docker compose up --build -d
```

起動すると `start.sh` が `pcscd` / `dbus` / `polkitd` を立ち上げたのち、
`linux_data/python/main.py` を実行します。

### 4. ログの確認

```bash
docker compose logs -f
```

カードリーダーを検出すると「ICカードを置いてください...」と表示され、
カードが置かれるたびに自動的に IDm と ATS を取得・表示します。

```
カードリーダーを検出しました。ICカードを置いてください...
カードリーダー : SONY FeliCa RC-S300/P (XXXXXXX) 00 00
IDm            : 01 02 03 04 05 06 07 08
ATS            : XX XX XX XX ...
```

---

## `lib/manaca_reader.py` API リファレンス

`main.py` から利用しているカードリーダー制御ライブラリです。単体で
import して使うこともできます。

```python
from lib.manaca_reader import SmartCardReaderSetup

reader = SmartCardReaderSetup()
if reader.setup():
    # カードが置かれるまで自動で待機する
    cards = reader.read()
    print(cards[0]["IDm"])
```

### `SmartCardReaderSetup()`

コンストラクタ。PC/SC コンテキストを確立し、接続されているリーダーを列挙します。

---

### `setup() → bool`

初期化が成功したかどうかを返します。カードリーダーが未接続の場合は `False` になります。

```python
reader = SmartCardReaderSetup()
if not reader.setup():
    print("カードリーダーが刺さっていません")
```

---

### `card_read() → list[dict]`

カードが置かれるまで待機し、検知した時点で各リーダーの状態を返します。

カードが既に置かれている場合は即座に返ります。
カードが置かれていない場合は、挿入されるまでブロックします。

```python
states = reader.card_read()
```

戻り値の各要素：

| キー | 内容 |
| --- | --- |
| `Card Reader` | リーダー名（例: `SONY FeliCa RC-S300/P ...`） |
| `EVENT` | 状態の文字列リスト（例: `["Card present in reader", "State changed"]`） |
| `ATR` | Answer To Reset（16進文字列、カードなしは空文字） |
| `Connection` | APDU送信用の接続オブジェクト（カード挿入時のみ存在）。`read()` を使用した場合はこのキーは含まれません。`card_read()` を直接呼んだ場合のみ存在します。 |

---

### `read(out="HEX") → list[dict]`

IDm と ATS を一度に取得します（**デフォルト推奨**）。
カード未挿入の場合は挿入されるまで待機します。

```python
cards = reader.read()
card = cards[0]
print(card["IDm"])
print(card["ATS"])   # 取得できない場合は None
```

`out` パラメータの値と出力形式の対応は以下の通りです。

| `out` の値 | 出力形式 | 例 |
| --- | --- | --- |
| `"HEX"`（デフォルト） | `0x` 付き16進文字列 | `0x01 0x02 0x03` |
| `"RAW"` | 生バイトデータ（`list[int]`） | `[1, 2, 3]` |
| `"16"` | 16進文字列 | `01 02 03` |

---

### `get_IDm(conn, out="HEX") → str`

接続オブジェクトを受け取り、カードの **IDm**（FeliCa固有の8バイト識別番号）を取得します。
通常は `read()` を使えばよく、このメソッドを直接呼ぶ必要はありません。

| 項目 | 内容 |
| --- | --- |
| APDU コマンド | `FF CA 00 00 00` |
| `out` パラメータ | `read()` と同じ値（`"HEX"` / `"RAW"` / `"16"`）を受け付ける |

---

### `get_ATS(conn, out="HEX") → str \| None`

接続オブジェクトを受け取り、カードの **ATS**（Answer To Select、カード属性情報）を取得します。
通常は `read()` を使えばよく、このメソッドを直接呼ぶ必要はありません。

| 項目 | 内容 |
| --- | --- |
| APDU コマンド | `FF CA 01 00 00` |
| `out` パラメータ | `read()` と同じ値（`"HEX"` / `"RAW"` / `"16"`）を受け付ける |
| 備考 | カードの種類によっては取得できず `None` になる（例: 一部の Suica / MIFARE） |

---

### `cardReaderList() → list[str]`

接続されているリーダー名の一覧を返します。

```python
print(reader.cardReaderList())
# ['SONY FeliCa RC-S300/P (XXXXXXX) 00 00']
```

---

## 取得データについて

| データ | APDUコマンド | 内容 | 備考 |
| --- | --- | --- | --- |
| IDm | `FF CA 00 00 00` | FeliCa固有の8バイト識別番号 | 全カードで取得可能 |
| ATS | `FF CA 01 00 00` | カード属性・プロトコル情報 | カード種別により取得不可の場合あり（`None`） |
| ATR | 接続時に自動取得 | Answer To Reset（カード種別・通信情報） | `analysis_cardreader_status` で解析 |

> **PMm（Manufacturer Parameter）について**
> PMm は PC/SC 標準の GET DATA コマンドでは取得できません。
> FeliCa 独自コマンド（`FF AB ...`）が必要で、リーダーのファームウェアに依存するため本ライブラリでは非対応です。

---

## 対応カード

PC/SC 経由で動作確認が見込めるカード（IDm 取得）:

- manaca / Suica / PASMO / ICOCA などの交通系 IC カード
- Edy / nanaco / WAON などの電子マネーカード
- 社員証・学生証（FeliCa / MIFARE）

> **マイナンバーカードについて**
> 読み取るたびに IDm が変化するため、識別用途には使用できません。

---

## 今後の予定（TODO）

`Dockerfile` / `compose.yml` には GPIO(LED) 制御用のパッケージ
（`python3-lgpio` 等）や環境変数（`GPIOZERO_PIN_FACTORY=lgpio`）が
あらかじめ用意されていますが、GPIO を利用した LED 通知機能自体は
まだ実装されていません。
