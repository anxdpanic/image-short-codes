#!/usr/bin/env bash

# TODO: ask for password

docker run --rm python:alpine python -c "import crypt; print(crypt.crypt('YOUR_PASSWORD'))"

# TODO: add encrypted password to .env

ssh-keygen -t ed25519 -f ./ssh/ssh_host_ed25519_key
ssh-keygen -t rsa -b 4096 -f ./ssh/ssh_host_rsa_key

mkdir data
