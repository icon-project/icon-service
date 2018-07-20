#!/bin/bash
set -e

PYVER=$(python -c 'import sys; print(sys.version_info[0])')
if [[ PYVER -ne 3 ]];then
  echo "The script should be run on python3"
  exit 1
fi

if [[ ("$1" = "test" && "$2" != "--ignore-test") || ("$1" = "build") || ("$1" = "deploy") ]]; then
  pip install -r requirements.txt

  EARL_VER=$(curl http://tbears.icon.foundation.s3-website.ap-northeast-2.amazonaws.com/earlgrey/VERSION)
  pip install --force-reinstall "http://tbears.icon.foundation.s3-website.ap-northeast-2.amazonaws.com/earlgrey/earlgrey-$EARL_VER-py3-none-any.whl"
  rm -rf earlgrey*

  wget "http://tbears.icon.foundation.s3-website.ap-northeast-2.amazonaws.com/iconcommons-0.9.5-py3-none-any.whl"
  pip install --force-reinstall iconcommons-0.9.5-py3-none-any.whl
  rm -rf iconcommons*

  if [[ "$2" != "--ignore-test" ]]; then
    python -m unittest
  fi

  if [ "$1" = "build" ] || [ "$1" = "deploy" ]; then
    pip install wheel
    rm -rf build dist *.egg-info
    python setup.py bdist_wheel

    if [ "$1" = "deploy" ]; then
      VER=$(ls dist | sed -nE 's/[^-]+-([0-9\.]+)-.*/\1/p')

      mkdir -p $VER
      cp VERSION dist/*$VER*.whl docs/CHANGELOG.md docs/dapp_guide.md $VER

      if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
        echo "Error: AWS keys should be in your environment"
        rm -rf $VER
        exit 1
      fi

      pip install awscli
      aws s3 cp $VER s3://tbears.icon.foundation/$VER --recursive --acl public-read

      rm -rf $VER
    fi
  fi

else
  echo "Usage: build.sh [test|build|deploy]"
  echo "  test: run test"
  echo "  build: run test and build"
  echo "  build --ignore-test: run build"
  echo "  deploy: run test, build and deploy to s3"
  echo "  deploy --ignore-test: run build and deploy to s3"
  exit 1
fi

