#!/bin/bash

# Automatically fetch AWS account ID and region from AWS CLI config
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

check_env_param() {
  local env=$1
  if [[ -z "$env" ]]; then
    echo "❌ Missing environment parameter!"
    echo "Usage: make <bootstrap|deploy|destroy> env=<frontend|backend>"
    exit 1
  fi
}

bootstrap() {
  local env=$1
  check_env_param "$env"
  echo "🔹 Bootstrapping environment: $env (Account: $ACCOUNT_ID, Region: $REGION)"

  if [[ "$env" == "frontend" ]]; then
    cdk bootstrap \
      --context @aws-cdk/core:bootstrapQualifier=frontend \
      --qualifier frontend \
      --toolkit-stack-name CDKToolkit-Frontend \
      aws://$ACCOUNT_ID/$REGION

  elif [[ "$env" == "backend" ]]; then
    cdk bootstrap \
      --context @aws-cdk/core:bootstrapQualifier=backend \
      --qualifier backend \
      --toolkit-stack-name CDKToolkit-Backend \
      aws://$ACCOUNT_ID/$REGION

  else
    echo "❌ Invalid environment! Use: frontend or backend"
    exit 1
  fi
}

deploy() {
  local env=$1
  check_env_param "$env"
  echo "🚀 Deploying environment: $env (Account: $ACCOUNT_ID, Region: $REGION)"

  if [[ "$env" == "frontend" ]]; then
    cdk deploy QSRVoiceAssistantFrontendPipeline \
      --context @aws-cdk/core:bootstrapQualifier=frontend \
      --require-approval never

  elif [[ "$env" == "backend" ]]; then
    cdk deploy QSRVoiceAssistantBackendPipeline \
      --context @aws-cdk/core:bootstrapQualifier=backend \
      --require-approval never

  else
    echo "❌ Invalid environment! Use: frontend or backend"
    exit 1
  fi
}

destroy() {
  local env=$1
  check_env_param "$env"
  echo "⚠️ Destroying environment: $env (Account: $ACCOUNT_ID, Region: $REGION)"

  if [[ "$env" == "frontend" ]]; then
    cdk destroy QSRVoiceAssistantFrontendPipeline \
      --context @aws-cdk/core:bootstrapQualifier=frontend \
      --force

  elif [[ "$env" == "backend" ]]; then
    cdk destroy QSRVoiceAssistantBackendPipeline \
      --context @aws-cdk/core:bootstrapQualifier=backend \
      --force

  else
    echo "❌ Invalid environment! Use: frontend or backend"
    exit 1
  fi
}

# --- Dispatcher ---
action=$1
env=$2

if [[ "$action" == "bootstrap" ]]; then
    bootstrap "$env"
elif [[ "$action" == "deploy" ]]; then
    deploy "$env"
elif [[ "$action" == "destroy" ]]; then
    destroy "$env"
else
    echo "❌ Invalid action! Use: bootstrap, deploy, or destroy"
    exit 1
fi
