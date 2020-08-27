import base64
import google.auth.transport.requests
import google.oauth2.id_token
import json
import os
import requests

from google import auth
from google.cloud import iot_v1
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.api_core.exceptions import FailedPrecondition

iot_client = iot_v1.DeviceManagerClient()
storage_client = storage.Client()

def on_iot_event(event, context):
    message_str = base64.b64decode(event['data']).decode('utf-8')
    message_obj = json.loads(message_str)
    if message_obj['message-type'] == 'UPLOAD-REQUEST':
        device_info = get_device_info(event)
        bucket = check_create_device_upload_bucket(device_info)
        access_token = generate_access_token(bucket.name)
        device_upload_message = {
            'message-type': 'FILE-UPLOAD',
            'message': {
                'bucket': f'{bucket.name}',
                'access-token': f'{access_token["access_token"]}'
            }
        }
    try:
        response = send_message_to_device(device_info,
        json.dumps(device_upload_message).encode('utf-8'))
    except FailedPrecondition:
        return 'Device is not connected'
    return 'Download message send'

def get_device_info(event):
    return {
        "PROJECT": f"{event['attributes']['projectId']}",
        "LOCATION": f"{event['attributes']['deviceRegistryLocation']}",
        "REGISTRY": f"{event['attributes']['deviceRegistryId']}",
        "DEVICE_ID": f"{event['attributes']['deviceId']}",
        "NUM_ID": f"{event['attributes']['deviceNumId']}"
    }

def check_create_device_upload_bucket(device_info):
    bucket_name = f"{device_info['NUM_ID']}-upload"
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

def generate_access_token(bucket_name):
    token_broker_url = os.environ.get(
        'TOKEN_BROKER_URL', 'Specified environment variable is not set.')
    credentials, project = auth.default()
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(
        auth_req, token_broker_url)
    param = {
        'access-type': 'write',
        'access-bucket': f'{bucket_name}'
    }
    function_headers = {'Authorization': f'bearer {id_token}'}
    function_response = requests.post(
        token_broker_url, headers=function_headers, json=param)
    return json.loads(function_response.content)

def send_message_to_device(device_info, message_str):
    full_path = get_device_full_path(device_info)
    return iot_client.send_command_to_device(full_path, message_str)

def get_device_full_path(device_info):
    return iot_client.device_path(
        device_info['PROJECT'],
        device_info['LOCATION'],
        device_info['REGISTRY'],
        device_info['DEVICE_ID'])