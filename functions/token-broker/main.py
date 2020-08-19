import os
import google.auth.transport.requests
import requests
from google.auth.transport.requests import AuthorizedSession
from google.auth.credentials import AnonymousCredentials
from google.auth import exceptions
from google import auth
import json
import six
from six.moves import http_client

_STS_ENDPOINT = "https://sts.googleapis.com/v1beta/token"
_IAM_SA_ENDPOINT = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"

def generate_down_scoped_token(request):
    request_json = request.get_json()
    access_type = request_json['access-type']
    access_bucket = request_json['access-bucket']

    short_lived_token = generate_short_lived_token(access_type)
    return down_scope_access_token(access_type, access_bucket, short_lived_token)



def generate_short_lived_token(access_type):
    access_sa_account = get_access_account(access_type)
    
    credentials, project = auth.default()
    response = AuthorizedSession(credentials).post(
        _IAM_SA_ENDPOINT + access_sa_account + ":generateAccessToken",
        data={
            "lifetime": f"{os.environ.get('TOKEN_LIFETIME', 'Specified environment variable is not set.')}s",
            "scope" : ["https://www.googleapis.com/auth/cloud-platform"]})
                
    return json.loads(response.content.decode("utf-8"))["accessToken"]

def down_scope_access_token(access_type, access_bucket, short_lived_token):
    request = google.auth.transport.requests.Request()
    ac = AnonymousCredentials()
    authed_session = AuthorizedSession(credentials=ac)
    body = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "subject_token": short_lived_token,
        "options": json.dumps(create_downscoped_options(access_type, access_bucket))
    }

    resp = authed_session.post(_STS_ENDPOINT, data=body)
    if resp.status_code != http_client.OK:
        raise exceptions.RefreshError("Failed to acquire downscoped token")

    return resp.json()

def create_downscoped_options(access_type, access_bucket):
    if access_type.lower() == 'write':
        permission = "inRole:roles/storage.objectCreator"        
    else:
        permission = "inRole:roles/storage.objectViewer"
    
    downscoped_options = {
        "accessBoundary" : {
            "accessBoundaryRules" : [
                {
                    "availableResource" : "//storage.googleapis.com/projects/_/buckets/" + access_bucket,
                    "availablePermissions": [permission]
                }
            ]
        }
    }
    
    return downscoped_options

def get_access_account(access_type):
    if access_type.lower() == 'write':
        access_sa_account = os.environ.get('WRITE_SA', 'Specified environment variable is not set.')
    else: 
        access_sa_account = os.environ.get('READ_SA', 'Specified environment variable is not set.')
    return access_sa_account