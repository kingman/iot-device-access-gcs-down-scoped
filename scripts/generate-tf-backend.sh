#!/usr/bin/env sh

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Check if the necessary dependencies are available

if ! command -v gsutil >/dev/null 2>&1; then
    echo "gsutil command is not available, but it's needed. Terminating..."
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl command is not available, but it's needed. Terminating..."
    exit 1
fi

if [ -z "${TF_SERVICE_ACCOUNT_NAME}" ]; then
    echo 'The TF_SERVICE_ACCOUNT_NAME environment variable that points to the Google Cloud service account that Terraform will use is not defined. Terminating...'
    exit 1
fi

if [ -z "${TF_STATE_PROJECT}" ]; then
    echo 'The TF_STATE_PROJECT environment variable that points to the Google Cloud project to store the Terraform state is not defined. Terminating...'
    exit 1
fi

if [ -z "${TF_STATE_BUCKET}" ]; then
    echo 'The TF_STATE_BUCKET environment variable that points to the Google Cloud Storage bucket to store the Terraform state is not defined. Terminating...'
    exit 1
fi

if [ -z "${GOOGLE_CLOUD_PROJECT}" ]; then
    echo 'The GOOGLE_CLOUD_PROJECT environment variable that points to the default Google Cloud project that Terraform will provision the resources in is not defined. Terminating...'
    exit 1
fi

if [ -z "${GOOGLE_CLOUD_REGION}" ]; then
    echo 'The GOOGLE_CLOUD_REGION environment variable that points to the default Google Cloud region that Terraform will provision the resources in is not defined. Terminating...'
    exit 1
fi

if [ -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]; then
    echo 'The GOOGLE_APPLICATION_CREDENTIALS environment variable that points to the default Google Cloud application credentials that Terraform will use is not defined. Terminating...'
    exit 1
fi

if [ -z "${IOT_REGISTRY_ID}" ]; then
    echo 'The IOT_REGISTRY_ID environment variable that states the IoT Core registry id that Terraform will use is not defined. Terminating...'
    exit 1
fi

if [ -z "${IOT_DEVICE_ID}" ]; then
    echo 'The IOT_DEVICE_ID environment variable that states the IoT Core device id that Terraform will use is not defined. Terminating...'
    exit 1
fi

echo "Setting the default Google Cloud project to ${TF_STATE_PROJECT}"
gcloud config set project "${TF_STATE_PROJECT}"

echo "Creating the service account for Terraform"
if gcloud iam service-accounts describe "${TF_SERVICE_ACCOUNT_NAME}"@"${TF_STATE_PROJECT}".iam.gserviceaccount.com >/dev/null 2>&1; then
    echo "The ${TF_SERVICE_ACCOUNT_NAME} service account already exists."
else
    gcloud iam service-accounts create "${TF_SERVICE_ACCOUNT_NAME}" \
        --display-name "Terraform admin account"
fi

echo "Granting the service account permission to view the Admin Project"
gcloud projects add-iam-policy-binding "${TF_STATE_PROJECT}" \
    --member serviceAccount:"${TF_SERVICE_ACCOUNT_NAME}"@"${TF_STATE_PROJECT}".iam.gserviceaccount.com \
    --role roles/viewer

echo "Granting the service account permission to manage Cloud Storage"
gcloud projects add-iam-policy-binding "${TF_STATE_PROJECT}" \
    --member serviceAccount:"${TF_SERVICE_ACCOUNT_NAME}"@"${TF_STATE_PROJECT}".iam.gserviceaccount.com \
    --role roles/storage.admin

echo "Enable the Cloud Resource Manager API with"
gcloud services enable cloudresourcemanager.googleapis.com

echo "Creating a new Google Cloud Storage bucket to store the Terraform state in ${TF_STATE_PROJECT} project, bucket: ${TF_STATE_BUCKET}"
if gsutil ls -b gs://"${TF_STATE_BUCKET}" >/dev/null 2>&1; then
    echo "The ${TF_STATE_BUCKET} Google Cloud Storage bucket already exists."
else
    gsutil mb -p "${TF_STATE_PROJECT}" gs://"${TF_STATE_BUCKET}"
    gsutil versioning set on gs://"${TF_STATE_BUCKET}"
fi

TERRAFORM_BACKEND_DESCRIPTOR_PATH=terraform/backend.tf
echo "Generating the descriptor to hold backend data in ${TERRAFORM_BACKEND_DESCRIPTOR_PATH}"
if [ -f "${TERRAFORM_BACKEND_DESCRIPTOR_PATH}" ]; then
    echo "The ${TERRAFORM_BACKEND_DESCRIPTOR_PATH} file already exists."
else
    tee "${TERRAFORM_BACKEND_DESCRIPTOR_PATH}" <<EOF
terraform {
    backend "gcs" {
        bucket  = "${TF_STATE_BUCKET}"
        prefix  = "terraform/state"
    }
}
EOF
fi

IOT_DEVICE_PUB_KEY=rsa_public.pem
IOT_DEVICE_KEY_PATH=terraform/${IOT_DEVICE_PUB_KEY}
echo "Create IoT Core device credential and put public key in ${IOT_DEVICE_KEY_PATH}"
if [ -f "${IOT_DEVICE_KEY_PATH}" ]; then
    echo "The ${IOT_DEVICE_KEY_PATH} file already exists."
else
    openssl genpkey -algorithm RSA -out rsa_private.pem -pkeyopt rsa_keygen_bits:2048 && openssl rsa -in rsa_private.pem -pubout -out ${IOT_DEVICE_KEY_PATH}
fi

TERRAFORM_VARIABEL_FILE_PATH=terraform/terraform.tfvars
echo "Generate the terraform variables in ${TERRAFORM_VARIABEL_FILE_PATH}"
if [ -f "${TERRAFORM_VARIABEL_FILE_PATH}" ]; then
    echo "The ${TERRAFORM_VARIABEL_FILE_PATH} file already exists."
else
    tee "${TERRAFORM_VARIABEL_FILE_PATH}" <<EOF
google_project_id="${GOOGLE_CLOUD_PROJECT}"
google_default_region="${GOOGLE_CLOUD_REGION}"
google_iot_registry_id="${IOT_REGISTRY_ID}"
google_iot_device_id="${IOT_DEVICE_ID}"
google_iot_device_key_path="${IOT_DEVICE_PUB_KEY}"
EOF
fi