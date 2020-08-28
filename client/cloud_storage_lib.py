# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python Library for access Google Cloud Storage using short lived access token
"""

import logging
import google.oauth2.credentials
import os

from google.cloud import storage

logging.basicConfig(level=20)
logger = logging.getLogger(__name__)

class GCSDownloadHandler:
    """
    Manages blob download from Google Cloud Storage.

    Takes bucket name, blob name, project id and access token as input.
    """

    def __init__(self, project_id, local_file_path=None):
        self._project_id = project_id

        if not local_file_path:
            self._local_file_path = os.getcwd()
        else:
            self._local_file_path = local_file_path

    def _get_storage_client(self, project_id, access_token):
        try:
            token_cred = google.oauth2.credentials.Credentials(token=access_token)
            storage_client = storage.Client(project=project_id, credentials=token_cred)
            return storage_client
        except Exception:
            logger.warn('Could not initialize Cloud Storage client.')
    

    def _get_bucket(self, storage_client, bucket_name):
        try:
            bucket = storage_client.bucket(bucket_name)
            return bucket
        except Exception:
            logger.warn(f'Could not access bucket: {bucket_name}.')
        
    
    def _get_blob(self, bucket, blob_name):
        try:
            blob = bucket.blob(blob_name)
            return blob
        except Exception:
            logger.warn(f'Could not access blob: {blob_name}.')
    
    def on_message(self, json_payload):
        if 'message-type' in json_payload and json_payload['message-type'] == 'FILE-DOWNLOAD':
            if not self._project_id:
                logger.warn('No valid project id provided. GCSDownloadHandler is disabled')
                return

            message = json_payload['message']
            download_fail_msg = 'Failed to download file.'

            storage_client = self._get_storage_client(self._project_id, message['access-token'])
            if not storage_client:
                logger.warn(download_fail_msg)
                return

            bucket = self._get_bucket(storage_client, message['bucket'])
            if not bucket:
                logger.warn(download_fail_msg)
                return

            blob_name = message['file']

            blob = self._get_blob(bucket, blob_name)
            if not blob:
                logger.warn(download_fail_msg)
                return

            try:
                blob.download_to_filename(f'{self._local_file_path}/{blob_name}')
            except Exception as e:
                logger.warn(f'Fail to download file: {blob}. {e}')

            logger.info(f'Successfully downloaded {self._local_file_path}/{blob_name}')


# class GCSUploadHandler:
#     """
#     Manages file upload to Google Cloud Storage.

#     Takes a Cloud IoT client as input
#     """

#     _UPLOAD_REQUEST_MESSAGE = {'message-type': 'UPLOAD-REQUEST'}

#     def __init__(self, cloud):
#         self._cloud = cloud
#         self._event = threading.Event()


