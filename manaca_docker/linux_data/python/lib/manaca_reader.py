# 必要なモジュールのインストール方法:
# pip install pyscard

from smartcard import (
    scard,
    util,
    System
)

class SmartCardReaderSetup:
    def __init__(self):
        self.readers                = []
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
        return self.cardReader
    
    def check_card_status(self):
        """
        カードが置かれるまで待機し、検知した時点で状態を取得して返す関数。

        SCardGetStatusChange を2段階で呼ぶことでカード挿入を確実に検知する。
          1回目: SCARD_STATE_UNAWARE でリーダーの現在状態を即座に取得
          2回目: カードが存在しない場合、SCARD_STATE_PRESENT になるまで無限に待機
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
        
        return currentStates

    def card_read(self):
        """
        ```
        {
            "Card Reader"   : reader, 
            "EVENT"         : event, 
            "ATR"           : card_atr,
            "Connection"    : APDU送信に使用するカードリーダとの接続オブジェクト
        }
        ```
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
        """カードリーダーの状態を解析して辞書形式で返す関数。"""
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
        txData                      = {
            "IDm"                               : [0xFF, 0xCA, 0x00, 0x00, 0x00],
            "ATS"                               : [0xFF, 0xCA, 0x01, 0x00, 0x00]
        }
        if conn is not None:
            recv_data, sw1, sw2     = conn.transmit(txData.get(data, [0xFF, 0xCA, 0x00, 0x00, 0x00]))
            return recv_data, sw1, sw2
        
        return None
    
    def get_IDm(self, conn, out = "HEX"):
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
    
    def read(self, out = "HEX"): # "HEX" : 0x付き / "RAW" : 生データ / "16" : 16進数値のみ
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
        return self.readers


if __name__ == "__main__":
    cardRead = SmartCardReaderSetup()
    if not cardRead.setup():
        print("カードリーダーが刺さっていません")
    else:
        print("カードリーダーを検出しました。ICカードを置いてください...")
        # カードが置かれるまで card_read() 内で待機する
        cards = cardRead.read("16")
        for card in cards:
            if "IDm" in card:
                print(f"カードリーダー  : {card['Card Reader']}")
                print(f"IDm            : {card['IDm']}")
                print(f"ATS            : {card.get('ATS', 'N/A')}")
    input()
