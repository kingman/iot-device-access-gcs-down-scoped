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

    def __init__(self, project_id, access_token, bucket_name, blob_name, local_file_path=None, local_file_name=None):
        if not project_id:
            logger.warn('No valid project id provided. GCSDownloadHandler is disabled')
            self._enabled = False
            return

        storage_client = self._get_storage_client(project_id, access_token)

        if not storage_client:
            logger.warn('Could not initialize Cloud Storage client. GCSDownloadHandler is disabled')
            self._enabled = False
            return
        
        bucket = self._get_bucket(storage_client, bucket_name)

        if not bucket:
            logger.warn('Could not access bucket. GCSDownloadHandler is disabled')
            self._enabled = False
            return

        blob = self._get_blob(bucket, blob_name)

        if not blob:
            logger.warn('Could not access blob. GCSDownloadHandler is disabled')
            self._enabled = False
            return
        
        self._blob = blob

        if not local_file_path:
            self._local_file_path = os.getcwd()
        else:
            self._local_file_path = local_file_path

        if not local_file_name:
            self._local_file_name = blob_name
        else:
            self._local_file_name = local_file_name
        
        self._enabled = True
    

    def _get_storage_client(self, project_id, access_token):
        try:
            token_cred = google.oauth2.credentials.Credentials(token=access_token)
            storage_client = storage.Client(project=project_id, credentials=token_cred)
            return storage_client
        except Exception:
            logger.warn('Got invalid access token.')
    

    def _get_bucket(self, storage_client, bucket_name):
        try:
            bucket = storage_client.bucket(bucket_name)
            return bucket
        except Exception:
            logger.warn(f'Got invalid bucket: {bucket_name}.')
        
    
    def _get_blob(self, bucket, blob_name):
        try:
            blob = bucket.blob(blob_name)
            return blob
        except Exception:
            logger.warn(f'Got invalid blob: {blob_name}.')
        
    
    def download(self):
        if not self._enabled:
            return
        try:
            self._blob.download_to_filename(f'{self._local_file_path}/{self._local_file_name}')
        except Exception as e:
            logger.warn(f'Fail to download file: {self._blob}. {e}')
        logger.info(f'Successfully downloaded {self._local_file_path}/{self._local_file_name}')
