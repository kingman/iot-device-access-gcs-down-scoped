# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import requests
import json
from google import auth
from google.cloud import iot_v1
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.api_core.exceptions import FailedPrecondition
import google.auth.transport.requests
import google.oauth2.id_token

iot_client = iot_v1.DeviceManagerClient()
storage_client = storage.Client()


'''
request json data format:
{
    "device": {
        "PROJECT": "...",
        "LOCATION": "...",
        "REGISTRY": "...",
        "DEVICE_ID": "..."
    },
    "file": {
        "bucket-name": "...",
        "blob-name": "..."
    }
}
'''


def initialize_download_for_device(request):
    request_json = request.get_json()
    device_info = request_json['device']
    device_detail = get_device_detail(device_info)
    if device_detail.blocked:
        return 'Device blocked'
    device_info['num_id'] = device_detail.num_id
    download_file = request_json['file']
    file_blob = add_file_to_device_bucket(device_info, download_file)
    access_token = generate_access_token(file_blob)
    device_download_message = {
        'message-type': 'FILE-DOWNLOAD',
        'message': {
            'bucket': f'{file_blob.bucket.name}',
            'file': f'{download_file["blob-name"]}',
            'access-token': f'{access_token["access_token"]}'
        }
    }
    try:
        response = send_download_message_to_device(device_info,
        json.dumps(device_download_message).encode('utf-8'))
    except FailedPrecondition:
        return 'Device is not connected'
    return 'Download message send'


def send_download_message_to_device(device_info, message_str):
    full_path = get_device_full_path(device_info)
    return iot_client.send_command_to_device(full_path, message_str)


def get_device_detail(device_info):
    full_path = get_device_full_path(device_info)
    mask = iot_v1.types.FieldMask(paths=['num_id', 'name', 'blocked'])
    return iot_client.get_device(full_path, mask)


def get_device_full_path(device_info):
    return iot_client.device_path(
        device_info['PROJECT'],
        device_info['LOCATION'],
        device_info['REGISTRY'],
        device_info['DEVICE_ID'])


def add_file_to_device_bucket(device_info, download_file):
    download_bucket = check_create_device_download_bucket(device_info)
    return copy_blob(
        download_file['bucket-name'],
        download_file['blob-name'],
        download_bucket)


def check_create_device_download_bucket(device_info):
    bucket_name = f"{device_info['num_id']}-download"
    bucket = get_bucket(bucket_name)
    if bucket is None:
        bucket = create_bucket(device_info, bucket_name)
    return bucket


def get_bucket(bucket_name):
    bucket = None
    try:
        bucket = storage_client.get_bucket(bucket_name)
    except NotFound:
        print("Bucket {} not found".format(bucket_name))
    return bucket


def create_bucket(device_info, bucket_name):
    bucket = storage_client.bucket(bucket_name)
    bucket.location = device_info['LOCATION']
    bucket.storage_class = 'STANDARD'
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    return storage_client.create_bucket(bucket)


def copy_blob(source_bucket_name, blob_name, destination_bucket):
    source_bucket = storage_client.bucket(source_bucket_name)
    source_blob = source_bucket.blob(blob_name)
    return source_bucket.copy_blob(source_blob, destination_bucket, blob_name)


def generate_access_token(file_blob):
    token_broker_url = os.environ.get(
        'TOKEN_BROKER_URL', 'Specified environment variable is not set.')
    credentials, project = auth.default()
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(
        auth_req, token_broker_url)
    param = {
        'access-type': 'read',
        'access-bucket': f'{file_blob.bucket.name}'
    }
    function_headers = {'Authorization': f'bearer {id_token}'}
    function_response = requests.post(
        token_broker_url, headers=function_headers, json=param)
    return json.loads(function_response.content)
