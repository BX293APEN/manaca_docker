#!/bin/bash
# ==========================================
# host.sh
#
# コンテナを起動する **前に、ホスト側で1回だけ** 実行するセットアップスクリプト。
# `docker compose up` の実行前提条件を整えるためのものであり、
# コンテナ内では実行しない (root権限が必要なため `sudo` 経由で実行すること)。
#
# | 処理順序 | 内容 |
# | --- | --- |
# | 1 | `lsmod` からNFC関連カーネルモジュール (nfc / pn533 / pn533_usb / port100 等) を検出 |
# | 2 | 検出したモジュールを `/etc/modprobe.d/blacklist-nfc.conf` に書き込み、次回起動時から自動ロードされないようにする |
# | 3 | 現在ロード中のモジュールをその場で `rmmod` し、再起動なしでUSBデバイスを解放する |
# | 4 | `update-initramfs` でinitramfsに変更を反映する |
#
# | 備考 |
# | --- |
# | Sony PaSoRi (RC-S380 等) はUSBに挿すと、pcscdより先にホストの標準NFCドライバ |
# | (`port100` 等) がインターフェースをclaimしてしまうことがある。 |
# | この場合 `lsusb` にはデバイスが表示されるが、`pcscd`/`pyscard` からは |
# | 一切見えない (`SCardListReaders` の結果が空になる)。 |
# | これはコンテナ側の権限 (`privileged` や `device_cgroup_rules`) をいくら |
# | 上げても解決しない、ホストカーネルレベルの問題であるため、 |
# | コンテナ起動前にホスト側でモジュールを外しておく必要がある。 |
#
# ==========================================
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "root権限が必要です。 sudo ./host.sh で実行してください。" >&2
    exit 1
fi

BLACKLIST_FILE="/etc/modprobe.d/blacklist-nfc.conf"

# ==========================================
# 対象となりうるNFC関連モジュール名の候補
# `lsmod` の結果に含まれるものだけを実際のブラックリスト対象とする
# ==========================================
CANDIDATE_MODULES=(nfc pn533 pn533_usb port100)

# 現在ロードされている対象モジュールのみを抽出
LOADED_MODULES=()
for module in "${CANDIDATE_MODULES[@]}"; do
    if lsmod | grep -qE "^${module}\b"; then
        LOADED_MODULES+=("${module}")
    fi
done

if [ ${#LOADED_MODULES[@]} -eq 0 ]; then
    echo "NFC関連カーネルモジュールはロードされていません。ブラックリスト登録は不要です。"
else
    echo "以下のモジュールを検出しました: ${LOADED_MODULES[*]}"

    # ==========================================
    # ブラックリストファイルへの書き込み
    # 既存の内容は上書きする (再実行しても重複登録されない)
    # ==========================================
    {
        echo "# host.sh により自動生成"
        echo "# Felicaリーダー(USB)をホストのNFCドライバに横取りされないためのブラックリスト設定"
        for module in "${LOADED_MODULES[@]}"; do
            echo "blacklist ${module}"
        done
    } | tee "${BLACKLIST_FILE}" > /dev/null

    echo "${BLACKLIST_FILE} に書き込みました。"

    # ==========================================
    # 依存関係の逆順で rmmod する (依存されている側=pn533_usb/port100 を先に外す)
    # 現在使用中でrmmodに失敗しても、blacklist自体は次回起動から有効なため処理は継続する
    # ==========================================
    for module in "${LOADED_MODULES[@]}"; do
        if rmmod "${module}" 2>/dev/null; then
            echo "モジュール ${module} をアンロードしました。"
        else
            echo "モジュール ${module} のアンロードに失敗しました (再起動後に反映されます)。" >&2
        fi
    done

    # initramfsに反映 (ディストリによってコマンドが異なるため候補を順に試す)
    if command -v update-initramfs >/dev/null 2>&1; then
        update-initramfs -u
    elif command -v dracut >/dev/null 2>&1; then
        dracut -f
    else
        echo "initramfs更新コマンドが見つかりませんでした。手動で更新してください。" >&2
    fi
fi

echo "完了しました。 'docker compose up --build -d' を実行してください。"
