# ==========================================
# main.py
#
# | 項目 | 内容 |
# | --- | --- |
# | 役割 | コンテナのエントリーポイント (start.sh) から起動される常駐スクリプト |
# | 処理内容 | カードリーダーを初期化し、ICカードが置かれるたびに IDm / ATS を取得してログ出力する |
# | 依存 | lib/manaca_reader.py の `SmartCardReaderSetup` |
#
# ==========================================

import sys
import time

from lib.manaca_reader import SmartCardReaderSetup


def main() -> int:
    """
    カードリーダーを初期化し、ICカードが置かれるたびに IDm / ATS を
    表示し続けるメインループ。

    | 戻り値 | 内容 |
    | --- | --- |
    | `0` | 正常終了（通常はループを抜けないため到達しない） |
    | `1` | カードリーダーが検出できず初期化に失敗した場合 |
    """
    reader = SmartCardReaderSetup()

    if not reader.setup():
        print("カードリーダーが刺さっていません", file=sys.stderr)
        return 1

    print("カードリーダーを検出しました。ICカードを置いてください...")

    # ==========================================
    # メインループ
    #
    # | 処理 | 内容 |
    # | --- | --- |
    # | `reader.read("16")` | カードが置かれるまでブロックし、置かれたら IDm / ATS を取得する |
    # | ループ | 1回読み取ったら再度待機状態に戻り、常駐し続ける |
    # ==========================================
    while True:
        try:
            cards = reader.read(out="16")
        except Exception as error:  # noqa: BLE001 - 常駐プロセスなので握りつぶして継続する
            print(f"読み取り中にエラーが発生しました: {error}", file=sys.stderr)
            time.sleep(1)
            continue

        for card in cards:
            if "IDm" in card and card["IDm"] is not None:
                print(f"カードリーダー : {card['Card Reader']}")
                print(f"IDm            : {card['IDm']}")
                print(f"ATS            : {card.get('ATS', 'N/A')}")

    return 0  # pragma: no cover - while True のため通常到達しない


if __name__ == "__main__":
    sys.exit(main())
