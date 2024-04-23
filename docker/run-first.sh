#!/usr/bin/env bash

echo -n "Password for sftp user: "
read -rs PLAIN_TEXT_PASSWORD

ENCRYPTED_PASSWORD=$(docker run --rm python:alpine python -W ignore::DeprecationWarning -c "import crypt; print(crypt.crypt('$PLAIN_TEXT_PASSWORD'))")
ENV_ENTRY="SFTP_PASSWORD=${ENCRYPTED_PASSWORD//$/\$$}"

cp .env.template .env
awk -i inplace -v INPLACE_SUFFIX=.bak -v env_entry="$ENV_ENTRY" '{sub(/SFTP_PASSWORD=/,env_entry); print}' .env

ssh-keygen -t ed25519 -f ./ssh/ssh_host_ed25519_key
ssh-keygen -t rsa -b 4096 -f ./ssh/ssh_host_rsa_key

mkdir data

nano .env
