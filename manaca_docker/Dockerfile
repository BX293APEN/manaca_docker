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
# | dbus / polkitd (無ければ policykit-1) | pcscdがクライアントを認可する際に使うD-Bus/PolicyKit (無いと Access denied になる) |
# | swig / gcc / make / python3-dev | pyscard のビルドに必要 |
# | python3 / python3-pip / python3-lgpio | Python本体とRaspberry Pi 5用GPIOバックエンド |
# | usbutils | USBデバイスの確認 (lsusb 等) |
RUN apt update && \
    apt upgrade -y && \
    apt install -y \
    sudo nano iproute2 iputils-ping language-pack-ja \
    python3 python3-pip python3-dev liblgpio-dev \
    pcscd pcsc-tools libpcsclite1 libpcsclite-dev libccid \
    dbus opensc \
    swig gcc make usbutils && \
    (apt install -y polkitd || apt install -y policykit-1) && \
    dbus-uuidgen --ensure=/etc/machine-id && \
    useradd -m -s /bin/bash -u ${USER_ID} ${USER_NAME} && \
    usermod -aG sudo ${USER_NAME} && \
    echo "root:${PASSWORD}" | chpasswd && \
    echo "${USER_NAME}:${PASSWORD}" | chpasswd && \
    mkdir -p /home/${USER_NAME}/${ENTRY_DIR} && \
    update-locale LANG=${LANG}

RUN pip3 install --break-system-packages pyscard

COPY ./linux_data/python /home/${USER_NAME}/${WS}/python
RUN chmod +x /home/${USER_NAME}/${WS}/python/main.py

COPY ${ENTRY_POINT} /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}
RUN chmod +x /home/${USER_NAME}/${ENTRY_DIR}/${ENTRY_POINT}

WORKDIR /home/${USER_NAME}/${WS}
