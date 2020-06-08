#!/bin/sh
DIR="private.ed"
openssl aes-256-cbc -d -salt -pbkdf2  -in "$DIR.tar.gz" -pass env:pass -out "$DIR.tar"
tar -xvf $DIR.tar && rm "$DIR.tar" && rm "$DIR.tar.gz" && echo "decrypted okay"
