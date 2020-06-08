#!/bin/sh
#mkdir private
#echo "test" > ./private/plan.txt
DIR=private.ed
tar -vcf $DIR.tar $DIR
openssl aes-256-cbc -salt -pbkdf2 -in $DIR.tar -pass env:pass -out $DIR.tar.gz && rm $DIR.tar && rm -rf $DIR && echo "okay encypted"
