# ==========================================
# Dockerfile
#
# | 項目 | 内容 |
# | --- | --- |
# | ベースイメージ | ubuntu:25.10 |
# | 用途 | 交通系ICカードリーダー(PC/SC)とGPIO(LED)を扱うPythonアプリの実行環境 |
# | 注意 | GPIO/USBへの実機アクセスが必要なため、compose.yml側の devices / device_cgroup_rules 設定と対になっている |
#
# ==========================================

# FROM [イメージ] [タグ]
# Docker Hub (https://hub.docker.com/) 参照
FROM ubuntu:24.10

# ==========================================
# ビルド引数 (compose.yml から受け取る)
#
# | 引数名 | 内容 |
# | --- | --- |
# | WS | 作業ディレクトリ名 |
# | USER_NAME | コンテナ内に作成するユーザー名 |
# | PASSWORD | ユーザー/rootのパスワード |
# | ENTRY_DIR | エントリーポイントを配置するディレクトリ |
# | ENTRY_POINT | エントリーポイントのファイル名 (start.sh) |
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

# ビルド時に使用したユーザー/ディレクトリ情報をイメージに残しておく (参照用)
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
    python3 python3-pip python3-dev \
    pcscd pcsc-tools libpcsclite1 libpcsclite-dev libccid \
    swig gcc make usbutils && \
    useradd -m -s /bin/bash -u ${USER_ID} ${USER_NAME} && \
    usermod -aG sudo ${USER_NAME} && \
    echo "root:${PASSWORD}" | chpasswd && \
    echo "${USER_NAME}:${PASSWORD}" | chpasswd && \
    mkdir -p /home/${USER_NAME}/${ENTRY_DIR} && \
    update-locale LANG=${LANG}

# ==========================================
# Pythonパッケージのインストール
# requirements.txt は linux_data (ビルドコンテキスト配下) に配置している
# ==========================================
COPY linux_data/requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt

# ==========================================
# アプリ本体の配置
#
# | ファイル | 配置先 | 備考 |
# | --- | --- | --- |
# | start.py | /home/${USER_NAME}/${ENTRY_DIR}/start.py | カード読み取り/LED制御のPython本体 (固定ファイル名) |
# | ${ENTRY_POINT} | /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT} | pcscd起動 → start.py実行 を行うラッパースクリプト |
#
# ENTRY_POINT (既定値 start.sh) は compose.yml の command から直接実行される。
# ファイル名を変更する場合は、実ファイルをリネームし .env の ENTRY_POINT を
# 書き換えるだけでよい (Dockerfile / compose.yml の編集は不要)。
#
# ==========================================
COPY start.py /home/${USER_NAME}/${ENTRY_DIR}/start.py
RUN chmod +x /home/${USER_NAME}/${ENTRY_DIR}/start.py

COPY ${ENTRY_POINT} /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}
RUN chmod +x /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}

WORKDIR /home/${USER_NAME}/${WS}
