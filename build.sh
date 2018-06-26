#!/bin/bash
set -e

PYVER=$(python -c 'import sys; print(sys.version_info[0])')
if [[ PYVER -ne 3 ]];then
  echo "The script should be run on python3"
  exit 1
fi

if [[ ("$1" = "test" && "$2" != "--ignore-test") || ("$1" = "build") || ("$1" = "deploy") ]]; then
  pip3 install -r requirements.txt

  if [[ "$2" != "--ignore-test" ]]; then
    python -m unittest
  fi

  if [ "$1" = "build" ] || [ "$1" = "deploy" ]; then
    pip install wheel
    rm -rf build dist *.egg-info
    python setup.py bdist_wheel

    if [ "$1" = "deploy" ]; then
      VER=$(ls dist | sed -nE 's/[^-]+-([0-9\.]+)-.*/\1/p')

      mkdir $VER
      cp dist/*$VER*.whl docs/CHANGELOG.md docs/dapp_guide.md docs/tbears_jsonrpc_api_v3.md $VER

      pip install awscli
      export AWS_ACCESS_KEY_ID=AKIAJYKHNVJS4GYQTV2Q
      export AWS_SECRET_ACCESS_KEY=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
      aws s3 cp $VER s3://tbears.icon.foundation/$VER --recursive --acl public-read

      rm -rf $VER
    fi
  fi

  rm -rf $VER
else
  echo "Usage: build.sh [test|build|deploy]"
  echo "  test: run test"
  echo "  build: run test and build"
  echo "  build --ignore-test: run build"
  echo "  deploy: run test, build and deploy to s3"
  echo "  deploy --ignore-test: run build and deploy to s3"
  exit 1
fi

