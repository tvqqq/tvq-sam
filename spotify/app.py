import boto3
import json
import os
import urllib3
import time


def lambda_handler(event, context):
    http = urllib3.PoolManager()

    # Get access token from DDB Meta table
    # TODO: make a common helper for DDB
    if os.getenv('AWS_SAM_LOCAL'):
        dynamodb = boto3.resource(
            'dynamodb', endpoint_url='http://host.docker.internal:8001')
    else:
        dynamodb = boto3.resource('dynamodb')

    # Set dynamodb table name variable from env
    table = dynamodb.Table(os.getenv('META_TABLE'))
    # Check access token is expired
    spotify = table.get_item(
        Key={'id': 'spotify'}
    )
    spotify = dict(spotify)['Item']['amount']

    # Check access_token_expired
    if 'access_token_expired' not in spotify or spotify['access_token_expired'] <= int(time.time()):
        # Get new access_token
        headers = {
            'Authorization': 'Basic ' + spotify['basic_authorization'],
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        fields = {
            'grant_type': 'refresh_token',
            'refresh_token': spotify['refresh_token']
        }
        request_token = http.request_encode_url(
            'POST', 'https://accounts.spotify.com/api/token', fields=fields, headers=headers)
        response_token = json.loads(request_token.data)

        access_token_expired = int(time.time()) + \
            response_token['expires_in'] - 1
        access_token = response_token['access_token']

        # Update access_token_expired into DDB
        table.update_item(
            Key={'id': 'spotify'},
            UpdateExpression='SET amount.access_token_expired = :access_token_expired, amount.access_token = :access_token',
            ExpressionAttributeValues={
                ':access_token_expired': access_token_expired,
                ':access_token': access_token
            },
            ReturnValues="ALL_NEW"
        )
    else:
        access_token = spotify['access_token']

    # Call API current-playing
    request_current_playing = http.request('GET', 'https://api.spotify.com/v1/me/player/currently-playing?market=VN',
                                           headers={
                                               'Authorization': 'Bearer ' + access_token
                                           })
    response_current_playing = json.loads(request_current_playing.data)

    # Return result
    result = {
        'playing': response_current_playing['is_playing'],
        'song': None,
        'artist': None,
        'url': None
    }
    if response_current_playing['is_playing']:
        item = response_current_playing['item']
        result.update({
            'song': item['name'],
            'artist': item['artists'][0]['name'],
            'url': item['external_urls']['spotify']
        })

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {
            # TODO: only one origin domain is allow, set it by env
            'Access-Control-Allow-Origin': 'https://tatviquyen.name.vn'
        },
    }
