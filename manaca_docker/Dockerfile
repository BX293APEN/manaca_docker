# ==========================================
# Dockerfile
#
# | 項目 | 内容 |
# | --- | --- |
# | ベースイメージ | ubuntu:25.10 |
# | 用途 | 交通系ICカードリーダー(PC/SC)とGPIO(LED)を扱うPythonアプリの実行環境 |
# | 注意 | GPIO/USBへの実機アクセスが必要なため、compose.yml側の devices / privileged 設定と対になっている |
#
# ==========================================

# FROM [イメージ] [タグ]
# Docker Hub (https://hub.docker.com/) 参照
FROM ubuntu:25.10

# ==========================================
# ビルド引数 (compose.yml から受け取る)
#
# | 引数名 | 内容 |
# | --- | --- |
# | WS | 作業ディレクトリ名 |
# | USER_NAME | コンテナ内に作成するユーザー名 |
# | PASSWORD | ユーザー/rootのパスワード |
# | ENTRY_DIR | エントリーポイントを配置するディレクトリ |
# | ENTRY_POINT | エントリーポイントのファイル名 |
# | LANG | ロケール設定 |
#
# ==========================================
ARG WS
ARG USER_NAME
ARG PASSWORD
ARG ENTRY_DIR
ARG ENTRY_POINT
ARG LANG

# 環境変数を設定
# 1000以上推奨
ENV USER_ID=1001
ENV GROUP_ID=1001

# entrypoint.sh (実行時) から参照できるように ARG を ENV へ引き継ぐ
ENV USER_NAME=${USER_NAME}
ENV ENTRY_DIR=${ENTRY_DIR}
ENV ENTRY_POINT=${ENTRY_POINT}

# gpiozeroのピン制御バックエンド
# Raspberry Pi 5 (RP1チップ) では lgpio が必要
ENV GPIOZERO_PIN_FACTORY=lgpio

# RUN 命令はなるべく1つにまとめる
# コマンドが長くなる場合は \ で改行すること
#
# | 追加パッケージ | 用途 |
# | --- | --- |
# | pcscd / pcsc-tools / libpcsclite1 / libpcsclite-dev / libccid | ICカードリーダーとのPC/SC通信 |
# | swig / gcc / make / python3-dev | pyscard のビルドに必要 |
# | python3 / python3-pip / python3-lgpio | Python本体とRaspberry Pi 5用GPIOバックエンド |
# | usbutils | USBデバイスの確認 (lsusb 等) |
RUN apt update && \
    apt upgrade -y && \
    apt install -y \
    sudo nano iproute2 iputils-ping language-pack-ja \
    python3 python3-pip python3-dev python3-lgpio \
    pcscd pcsc-tools libpcsclite1 libpcsclite-dev libccid \
    swig gcc make usbutils && \
    useradd -m -s /bin/bash -u ${USER_ID} ${USER_NAME} && \
    usermod -aG sudo,dialout,plugdev ${USER_NAME} && \
    echo "root:${PASSWORD}" | chpasswd && \
    echo "${USER_NAME}:${PASSWORD}" | chpasswd && \
    mkdir -p /home/${USER_NAME}/${ENTRY_DIR} && \
    update-locale LANG=${LANG}

# ==========================================
# GPIO制御用グループの作成
#
# | 項目 | 内容 |
# | --- | --- |
# | gpio グループ | /dev/gpiomem, /dev/gpiochip* へのアクセス許可用 |
# | 備考 | ホスト側のGID/デバイスファイルの権限に合わせて調整が必要な場合がある |
#
# ==========================================
RUN groupadd -f gpio && \
    usermod -aG gpio ${USER_NAME}

# ==========================================
# Pythonパッケージのインストール
# requirements.txt は linux_data (ビルドコンテキスト配下) に配置している
# ==========================================
COPY linux_data/requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt

COPY ${ENTRY_POINT} /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}
RUN chmod +x /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}

# ==========================================
# 起動スクリプトの配置
#
# | 項目 | 内容 |
# | --- | --- |
# | entrypoint.sh | pcscd起動 → 一般ユーザーへ降格 → Python実行 の順で処理するスクリプト |
# | 備考 | pcscd はUSB(カードリーダー)へのアクセスにroot権限が必要なため、コンテナはrootのまま起動する |
#
# ==========================================
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# USER ${USER_NAME}
# entrypoint.sh内で pcscd起動後に su コマンドを使い一般ユーザーへ降格するため、
# ここでは USER を切り替えずroot(デフォルト)のままにしておく

WORKDIR /home/${USER_NAME}/${WS}

# 起動したら実行するコマンド
# ENTRYPOINTを使うため、compose.yml側の command は不要
ENTRYPOINT ["/entrypoint.sh"]
