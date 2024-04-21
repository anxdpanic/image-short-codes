#!/usr/bin/env bash

echo -n "Password for sftp user: "
read -rs PLAIN_TEXT_PASSWORD

ENCRYPTED_PASSWORD=$(docker run --rm python:alpine python -W ignore::DeprecationWarning -c "import crypt; print(crypt.crypt('$PLAIN_TEXT_PASSWORD'))")
ENCRYPTED_PASSWORD=${ENCRYPTED_PASSWORD//$/\$$}
# awk -v password="$ENCRYPTED_PASSWORD" '{sub(/SFTP_PASSWORD=/,SFTP_PASSWORD=password); print}' .env
# TODO: add encrypted password to .env

ssh-keygen -t ed25519 -f ./ssh/ssh_host_ed25519_key
ssh-keygen -t rsa -b 4096 -f ./ssh/ssh_host_rsa_key

mkdir data
