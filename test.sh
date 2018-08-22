#!/bin/bash
set -e

if [ $# -ne 1 ]
then
	echo "Usage: test.sh <branch>"
	exit 1
fi

HOST=tbears.icon.foundation
S3_HOST="$HOST.s3-website.ap-northeast-2.amazonaws.com"
DEPS="earlgrey icon-commons"
BRANCH=$1

for PKG in $DEPS
do
	URL="http://$S3_HOST/$BRANCH/$PKG"
	VERSION=$(curl "$URL/VERSION")
	FILE="$PKG-$VERSION-py3-none-any.whl"
	pip install --force-reinstall "$URL/$FILE"
done

pip3 install -r requirements.txt

python -m unittest
