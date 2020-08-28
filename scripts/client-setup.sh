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

if ! command -v wget >/dev/null 2>&1; then
    echo "wget command is not available, but it's needed. Terminating..."
    exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
    echo "envsubst command is not available, but it's needed. Terminating..."
    exit 1
fi

if [ -z "${GOOGLE_CLOUD_PROJECT}" ]; then
    echo 'The GOOGLE_CLOUD_PROJECT environment variable that points to the default Google Cloud project that device client needs is not defined. Terminating...'
    exit 1
fi

if [ -z "${GOOGLE_CLOUD_REGION}" ]; then
    echo 'The GOOGLE_CLOUD_REGION environment variable that points to the default Google Cloud project that device client needs is not defined. Terminating...'
    exit 1
fi

if [ -z "${IOT_REGISTRY_ID}" ]; then
    echo 'The IOT_REGISTRY_ID environment variable that points to the default Google Cloud project that device client needs is not defined. Terminating...'
    exit 1
fi

if [ -z "${IOT_DEVICE_ID}" ]; then
    echo 'The IOT_DEVICE_ID environment variable that points to the default Google Cloud project that device client needs is not defined. Terminating...'
    exit 1
fi

ROOT_CERTIFICATE=client/roots.pem
echo "Download Google root certificate to ${ROOT_CERTIFICATE}"
if [ -f "${ROOT_CERTIFICATE}" ]; then
    echo "The ${ROOT_CERTIFICATE} file already exists."
else
    wget -O ${ROOT_CERTIFICATE} https://pki.goog/roots.pem
fi

DEVICE_CONFIG_FILE=client/cloud_config.ini
DEVICE_CONFIG_TEMPLATE_FILE=client/cloud_config_template.ini
echo "Generate device configuration file to ${DEVICE_CONFIG_FILE}"
if [ -f "${DEVICE_CONFIG_FILE}" ]; then
    echo "The ${DEVICE_CONFIG_FILE} file already exists."
else
    envsubst < ${DEVICE_CONFIG_TEMPLATE_FILE} > ${DEVICE_CONFIG_FILE}

IOT_DEVICE_PRIVATE_KEY=rsa_private.pem
IOT_DEVICE_PRIVATE_KEY_PATH=client/${IOT_DEVICE_PRIVATE_KEY}
echo "Move the generated private key for device to ${IOT_DEVICE_PRIVATE_KEY_PATH}"
if [ -f "${IOT_DEVICE_PRIVATE_KEY_PATH}" ]; then
    echo "The ${IOT_DEVICE_PRIVATE_KEY_PATH} file already exists."
else
     mv ${IOT_DEVICE_PRIVATE_KEY} ${IOT_DEVICE_PRIVATE_KEY_PATH}
