#!/bin/bash
set -e

HOST="tbears.icon.foundation"
S3_HOST="http://${HOST}.s3-website.ap-northeast-2.amazonaws.com"

function clear_build () {
  rm -rf build dist *.egg-info
}

PYVER=$(python -c 'import sys; print(sys.version_info[0])')
if [[ PYVER -ne 3 ]];then
  echo "The script should be run on python3"
  exit 1
fi

if [[ "$1" == "clear" ]]; then
  clear_build
  exit 1
fi

if [[ ("$1" = "test" && "$2" != "--ignore-test") || ("$1" = "build") || ("$1" = "deploy") ]]; then
  pip install -r requirements.txt

  WGET_VER=$(curl "${S3_HOST}/earlgrey/VERSION")
  pip install --force-reinstall "${S3_HOST}/earlgrey/earlgrey-${WGET_VER}-py3-none-any.whl"

  WGET_VER=$(curl "${S3_HOST}/iconcommons/VERSION")
  pip install --force-reinstall "${S3_HOST}/iconcommons/iconcommons-${WGET_VER}-py3-none-any.whl"

  if [[ "$2" != "--ignore-test" ]]; then
    python -m unittest
  fi

  if [ "$1" = "build" ] || [ "$1" = "deploy" ]; then
    pip install wheel
    clear_build
    python setup.py bdist_wheel

    if [ "$1" = "deploy" ]; then
      VER=$(cat VERSION)

      if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
        echo "Error: AWS keys should be in your environment"
        exit 1
      fi

      BRANCH=$(git rev-parse --abbrev-ref HEAD)
      S3_URL="s3://${HOST}/iconservice/${BRANCH}/"
      echo "$S3_URL"

      pip install awscli
      aws s3 cp VERSION "$S3_URL" --acl public-read
      aws s3 cp dist/*$VER*.whl "$S3_URL" --acl public-read

    fi
  fi

else
  echo "Usage: build.sh [test|build|deploy]"
  echo "  test: run test"
  echo "  clear: clear build and dist files"
  echo "  build: run test and build"
  echo "  build --ignore-test: run build"
  echo "  deploy: run test, build and deploy to s3"
  echo "  deploy --ignore-test: run build and deploy to s3"
  exit 1
fi

