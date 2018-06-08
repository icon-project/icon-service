[[ -z "$1" ]] && { echo "Version should be not empty" ; exit 1; }

pip install awscli

export  AWS_ACCESS_KEY_ID=AKIAJYKHNVJS4GYQTV2Q
export AWS_SECRET_ACCESS_KEY=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

mkdir $1
cp dist/*$1*.whl docs/CHANGELOG.md docs/dapp_guide.md docs/tbears_jsonrpc_api_v3.md $1
aws s3 cp $1 s3://unchain.icon.foundation/$1 --recursive --acl public-read
rm -rf $1