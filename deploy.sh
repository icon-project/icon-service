#!/bin/bash
set -e

HOST="tbears.icon.foundation"
PRODUCT="iconservice"

# Check arguments
if [ $# -eq 1 ]; then
    BRANCH=$1
elif [ $# -eq 2 ]; then
    BRANCH=$1
    VERSION=$2
else
    echo "Usage: deploy.sh <branch> [version]"
    echo "- <branch>: (required) git branch"
    echo "- [version]: (optional) Package version"
    echo "- ex) ./deploy.sh master 0.9.6"
    exit 1
fi

# Check python version >= 3.0
PYVER=$(python -c 'import sys; print(sys.version_info[0])')
if [[ PYVER -ne 3 ]];then
    echo "The script should be run on python3"
    exit 2
fi

# Get default version from VERSION file
if [ -z $VERSION ]; then
    VERSION=$(cat VERSION)
fi

echo "$PRODUCT $BRANCH $VERSION"

if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
    echo "Error: AWS keys should be in your environment"
    exit 1
fi

S3_URL="s3://${HOST}/${BRANCH}/${PRODUCT}"
echo "$S3_URL"

pip install awscli
aws s3 cp dist/*$VERSION*.whl "$S3_URL/" --acl public-read

if [ -z $VERSION ]
then
    aws s3 cp VERSION "$S3_URL/" --acl public-read
else
    echo "$VERSION" > .VERSION
    aws s3 cp .VERSION "$S3_URL/VERSION" --acl public-read
    rm -f .VERSION
fi
