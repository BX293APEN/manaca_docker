"""
交通系ICカードリーダーを制御し、カードがタッチされるたびにLEDの点灯/消灯を
切り替えるエントリーポイント。

## 必要なモジュールのインストール

```
pip install pyscard gpiozero
```

## 動作の流れ

| 手順 | 内容 |
| --- | --- |
| 1 | GPIOチップ番号を環境変数 `GPIOCHIP` から取得し、lgpioピンファクトリを初期化 |
| 2 | カードリーダーの初期化 (`SmartCardReaderSetup`) |
| 3 | カードがタッチされるまで待機 |
| 4 | タッチを検知したらLEDの状態を反転し、IDm/ATSを表示 |
| 5 | カードが取り除かれるまで待機し、手順3に戻る |

## GPIOチップ番号について

gpiozeroの `lgpio` ピンファクトリは、チップ番号を指定しない場合デフォルトで
`/dev/gpiochip0` を開こうとする。40ピンヘッダに対応するgpiochip番号は
機種/カーネルによって異なる (`gpiodetect` で `pinctrl-rp1` の番号を確認する
こと。例えば `gpiochip0` だったり `gpiochip4` だったりする)。
本ファイルでは `.env` の `GPIOCHIP` (例: `/dev/gpiochip0`) を読み取り、
末尾の数字をチップ番号として使用する。
"""

import os
import re

from smartcard import (
    scard,
    util,
    System
)

from gpiozero import Device, DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory


def get_gpio_chip_number(default=0):
    """
    環境変数 `GPIOCHIP` (例: `/dev/gpiochip0`) からチップ番号を取り出す関数。

    `.env` の `GPIOCHIP` は `compose.yml` の `devices` / `env_file` を通じて
    コンテナ内の環境変数としてもそのまま参照できる。

    | 引数 | 型 | 内容 |
    | --- | --- | --- |
    | default | int | `GPIOCHIP` が未設定、または数値を抽出できない場合に使うチップ番号 |

    | 戻り値 | 型 | 内容 |
    | --- | --- | --- |
    | chip_number | int | lgpioピンファクトリへ渡すGPIOチップ番号 |
    """
    chip_path = os.environ.get("GPIOCHIP", "")
    match = re.search(r"(\d+)$", chip_path)
    if match:
        return int(match.group(1))
    return default


class SmartCardReaderSetup:
    """
    PC/SC経由でICカードリーダーを操作するクラス。

    | メンバ変数 | 型 | 内容 |
    | --- | --- | --- |
    | readers | list | 接続されているカードリーダーの一覧 |
    | hcontext | int | PC/SCのコンテキストハンドル |
    | cardReader | bool | カードリーダーが利用可能かどうか |
    | lastStates | list | 直前に `check_card_status` で取得したリーダーの状態 |
    """

    def __init__(self):
        self.readers                = []
        self.lastStates             = []
        try:
            hresult, self.hcontext  = scard.SCardEstablishContext(scard.SCARD_SCOPE_USER)
            if hresult              != scard.SCARD_S_SUCCESS:
                raise scard.error(f"Failed to establish context : {scard.SCardGetErrorMessage(hresult)}")
            hresult, self.readers   = scard.SCardListReaders(self.hcontext, [])
            if hresult              != scard.SCARD_S_SUCCESS:
                raise scard.error(f"Failed to list readers : {scard.SCardGetErrorMessage(hresult)}")
            self.cardReader         = True

        except scard.error as e:
            print(e)
            self.cardReader         = False

    def setup(self):
        """
        カードリーダーが利用可能かどうかを返す関数。

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | cardReader | bool | 利用可能なら `True` |
        """
        return self.cardReader

    def check_card_status(self):
        """
        カードが置かれるまで待機し、検知した時点で状態を取得して返す関数。

        SCardGetStatusChange を2段階で呼ぶことでカード挿入を確実に検知する。

        | 段階 | 内容 |
        | --- | --- |
        | 1回目 | `SCARD_STATE_UNAWARE` でリーダーの現在状態を即座に取得 |
        | 2回目 | カードが存在しない場合、`SCARD_STATE_PRESENT` になるまで無限に待機 |

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | currentStates | list | 各リーダーの `(reader, eventstate, atr)` タプルの一覧 |
        """

        # ======== 1回目: 現在の状態を確認 ========
        states                      = [(reader, scard.SCARD_STATE_UNAWARE) for reader in self.readers]       # 全てのカードリーダの状態を確認
        hresult, currentStates      = scard.SCardGetStatusChange(self.hcontext, 0, states)

        if hresult                  != scard.SCARD_S_SUCCESS:
            raise scard.error(scard.SCardGetErrorMessage(hresult))

        # カードが1枚も挿入されていなければ挿入まで待機
        has_card                    = any( (eventstate & scard.SCARD_STATE_PRESENT) for _, eventstate, _ in currentStates )

        if not has_card:
            # ======== 2回目: 状態変化（カード挿入）を INFINITE で待つ ========
            # SCARD_STATE_CHANGED が立った状態を次の待機の基準にする
            wait_states             = [(reader, eventstate & ~scard.SCARD_STATE_CHANGED) for reader, eventstate, _ in currentStates]
            hresult, currentStates  = scard.SCardGetStatusChange(
                self.hcontext, scard.INFINITE, wait_states
            )

            if hresult              != scard.SCARD_S_SUCCESS:
                raise scard.error(scard.SCardGetErrorMessage(hresult))

        self.lastStates             = currentStates
        return currentStates

    def wait_for_card_removal(self):
        """
        直前の `check_card_status` の状態を基準に、カードが取り除かれるまで
        待機する関数。

        LEDを切り替えた後、同じカードを置いたままの状態で連続してトリガー
        されるのを防ぐために使用する。

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | なし | None | カードが取り除かれた時点で処理を返す |
        """
        wait_states                  = [(reader, eventstate & ~scard.SCARD_STATE_CHANGED) for reader, eventstate, _ in self.lastStates]
        hresult, _                   = scard.SCardGetStatusChange(self.hcontext, scard.INFINITE, wait_states)

        if hresult                   != scard.SCARD_S_SUCCESS:
            raise scard.error(scard.SCardGetErrorMessage(hresult))

    def card_read(self):
        """
        カード状態の取得〜カードリーダーとの接続確立までを行う関数。

        | 戻り値の要素 | 型 | 内容 |
        | --- | --- | --- |
        | Card Reader | str | カードリーダー名 |
        | EVENT | list | 検出されたイベントの説明文一覧 |
        | ATR | str | カードのATR (16進数文字列) |
        | Connection | object | APDU送信に使用する接続オブジェクト (カード検出時のみ) |
        """
        currentStates               = self.check_card_status()
        results                     = []

        # System.readers()[0].name : カードリーダの文字列名
        cardReaders                 = {
            r.name : r for r in System.readers()
        }

        for state in currentStates:
            data                    = self.analysis_cardreader_status(state)
            readerName              = data["Card Reader"]
            if (data["ATR"] != "") and (readerName in cardReaders):
                conn                = cardReaders[readerName].createConnection()
                conn.connect()
                data["Connection"]  = conn
            results.append(data)
        return results

    def analysis_cardreader_status(self, state):
        """
        カードリーダーの状態を解析して辞書形式で返す関数。

        | 引数 | 型 | 内容 |
        | --- | --- | --- |
        | state | tuple | `(reader, eventstate, atr)` のタプル |

        | 戻り値のキー | 型 | 内容 |
        | --- | --- | --- |
        | Card Reader | str | カードリーダー名 |
        | EVENT | list | 該当する状態フラグの説明文一覧 |
        | ATR | str | カードのATR (16進数文字列) |
        """
        reader, eventstate, atr = state
        flags = {
            scard.SCARD_STATE_ATRMATCH          : "Card found",
            scard.SCARD_STATE_UNAWARE           : "State unaware",
            scard.SCARD_STATE_IGNORE            : "Ignore reader",
            scard.SCARD_STATE_UNAVAILABLE       : "Reader unavailable",
            scard.SCARD_STATE_EMPTY             : "Reader empty",
            scard.SCARD_STATE_PRESENT           : "Card present in reader",
            scard.SCARD_STATE_EXCLUSIVE         : "Card allocated for exclusive use by another application",
            scard.SCARD_STATE_INUSE             : "Card in use by another application but can be shared",
            scard.SCARD_STATE_MUTE              : "Card is mute",
            scard.SCARD_STATE_CHANGED           : "State changed",
            scard.SCARD_STATE_UNKNOWN           : "State unknown",

        }

        event                       = [ev for f, ev in flags.items() if eventstate & f]
        card_atr                    = util.toHexString(atr, util.HEX)
        return {
            "Card Reader"           : reader,
            "EVENT"                 : event,
            "ATR"                   : card_atr
        }

    def get_card_data(self, conn = None, data = "IDm"):
        """
        カードへAPDUコマンドを送信しデータを取得する関数。

        | 引数 | 型 | 内容 |
        | --- | --- | --- |
        | conn | object | カードとの接続オブジェクト (`None` の場合は何もしない) |
        | data | str | 取得したいデータ種別 (`"IDm"` または `"ATS"`) |

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | recv_data, sw1, sw2 | tuple | 応答データとステータスワード (取得失敗時は `None`) |
        """
        txData                      = {
            "IDm"                               : [0xFF, 0xCA, 0x00, 0x00, 0x00],
            "ATS"                               : [0xFF, 0xCA, 0x01, 0x00, 0x00]
        }
        if conn is not None:
            recv_data, sw1, sw2     = conn.transmit(txData.get(data, [0xFF, 0xCA, 0x00, 0x00, 0x00]))
            return recv_data, sw1, sw2

        return None

    def get_IDm(self, conn, out = "HEX"):
        """
        カードのIDm (製造ID) を取得する関数。

        | 引数 | 型 | 内容 |
        | --- | --- | --- |
        | conn | object | カードとの接続オブジェクト |
        | out | str | 出力形式 (`"HEX"`: 0x付き / `"RAW"`: 生データ / その他: 16進数値のみ) |

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | IDm | str または list | 指定した形式のIDm (取得失敗時は `None`) |
        """
        data                        = self.get_card_data(conn, "IDm")
        if data is not None:
            recv_data, sw1, sw2     = data
            if out                  == "HEX":
                return util.toHexString(recv_data, util.HEX)
            elif out                  == "RAW":
                return recv_data
            else:
                return util.toHexString(recv_data)

        return None

    def get_ATS(self, conn, out = "HEX"):
        """
        カードのATS (追加情報) を取得する関数。

        | 引数 | 型 | 内容 |
        | --- | --- | --- |
        | conn | object | カードとの接続オブジェクト |
        | out | str | 出力形式 (`"HEX"`: 0x付き / `"RAW"`: 生データ / その他: 16進数値のみ) |

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | ATS | str または list | 指定した形式のATS (取得失敗、または応答が異常な場合は `None`) |
        """
        data                        = self.get_card_data(conn, "ATS")
        if data is not None:
            recv_data, sw1, sw2     = data
            if sw1 == 0x90 and sw2 == 0x00:
                if out == "HEX":
                    return util.toHexString(recv_data, util.HEX)
                elif out                  == "RAW":
                    return recv_data
                else:
                    return util.toHexString(recv_data)
        return None

    def read(self, out = "HEX"):
        """
        カードの検出からIDm/ATSの読み取りまでを行う関数。

        | 引数 | 型 | 内容 |
        | --- | --- | --- |
        | out | str | 出力形式 (`"HEX"`: 0x付き / `"RAW"`: 生データ / その他: 16進数値のみ) |

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | card_data_list | list | 各リーダーの読み取り結果 (辞書) の一覧 |
        """
        card_data_list              = self.card_read()
        for data in card_data_list:
            conn                    = data.pop("Connection", None)
            if conn is not None:
                try:
                    data["IDm"]     = self.get_IDm(conn=conn, out=out)
                    data["ATS"]     = self.get_ATS(conn=conn, out=out)
                finally:
                    conn.disconnect()

        return card_data_list

    def cardReaderList(self):
        """
        検出済みのカードリーダー一覧を返す関数。

        | 戻り値 | 型 | 内容 |
        | --- | --- | --- |
        | readers | list | カードリーダー名の一覧 |
        """
        return self.readers


if __name__ == "__main__":
    # ==========================================
    # メイン処理
    #
    # | 処理内容 |
    # | --- |
    # | GPIOチップ番号(GPIOCHIP)を指定してlgpioピンファクトリを初期化する |
    # | ICカードがタッチされるたびに、LEDの点灯/消灯を切り替える |
    # | 同じカードを置いたままでも連続でLEDが切り替わらないよう、取り除かれるまで待機する |
    #
    # ==========================================

    # デフォルト(chip=0)のままだと環境によっては40ピンヘッダのGPIOチップと
    # 一致せず `lgpio.error: 'can not open gpiochip'` になるため、
    # `.env` の GPIOCHIP (gpiodetectで確認した番号) を明示的に指定する
    Device.pin_factory             = LGPIOFactory(chip=get_gpio_chip_number())

    led_pin                          = DigitalOutputDevice(pin=18)
    led_pin.off()

    cardRead                         = SmartCardReaderSetup()

    if not cardRead.setup():
        print("カードリーダーが刺さっていません")
    else:
        print("カードリーダーを検出しました。ICカードをタッチしてください...")
        while True:
            cards                    = cardRead.read("16")
            led_pin.toggle()

            for card in cards:
                if card.get("IDm"):
                    print(f"カードリーダー  : {card['Card Reader']}")
                    print(f"IDm            : {card['IDm']}")
                    print(f"ATS            : {card.get('ATS', 'N/A')}")

            print(f"LED状態         : {'点灯' if led_pin.value else '消灯'}")

            # 同じカードによる連続トリガーを防ぐため、取り除かれるまで待機
            cardRead.wait_for_card_removal()
