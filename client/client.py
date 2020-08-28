# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from cloud_storage_lib import GCSDownloadHandler, GCSUploadHandler
from core import CloudIot
from time import sleep

import json
import itertools
import logging

logger = logging.getLogger(__name__)

def create_callback(handlers):

    def on_message(unused_client, unused_userdata, message):
        json_payload = json.loads(str(message.payload.decode('utf-8')))
        for handler in handlers:
            try:
                handler.on_message(json_payload)
            except Exception:
                logger.warn(f'{type(handler).__name__} failed to handle message')

    return {'on_message': on_message}

def main():
    with CloudIot() as cloud:
        download_handler = GCSDownloadHandler(cloud.project_id())
        upload_handler = GCSUploadHandler(cloud)
        callbacks = create_callback({download_handler, upload_handler})
        cloud.register_message_callbacks(callbacks)

        for read_count in itertools.count():
            upload_handler.upload_file('file-to-upload.txt')
            sleep(1000)

if __name__ == '__main__':
    main()
