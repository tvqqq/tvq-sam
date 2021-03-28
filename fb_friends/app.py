import boto3
import json
import os
import urllib3
import time
from boto3.dynamodb.conditions import Attr


def lambda_handler(event, context):
    client_sns = boto3.client('sns')

    if os.getenv('AWS_SAM_LOCAL'):
        dynamodb = boto3.resource(
            'dynamodb', endpoint_url='http://host.docker.internal:8001')
    else:
        dynamodb = boto3.resource('dynamodb')

    # Get access token from DynamoDB
    table_meta = dynamodb.Table(os.getenv('TABLE_NAME'))
    facebook = table_meta.get_item(
        Key={'id': 'facebook'}
    )
    facebook = dict(facebook)['Item']['amount']
    access_token = facebook['access_token']

    # If access token is revoked, send an email alert
    me = call_fb_graph(access_token, 'me')
    if 'name' not in me:
        client_sns.publish(
            TopicArn=os.getenv('SNS_TOPIC'),
            Subject='#TVQSAM x FB_Friend: Expired access token',
            Message='🔥 ALERT: Your Facebook access token is expired!'
        )

    # Get list current FB friends
    table_fb_friends = dynamodb.Table(os.getenv('FB_FRIEND_TABLE'))

    current_fb_friends = table_fb_friends.scan(
        ProjectionExpression='fb_id',
        FilterExpression="attribute_not_exists(unf_at)"
    )
    current_fb_friends_ids = pluck(current_fb_friends['Items'], 'fb_id')

    # Call API get list updated FB friends
    new_fb_friends_response = call_fb_graph(
        access_token, 'me', 'friends', 'name,picture.width(2048){url},gender&pretty=0', 5)

    new_fb_friends_ids = []
    for f in new_fb_friends_response['data']:
        new_fb_friends_ids.append(f['id'])
        table_fb_friends.update_item(
            Key={'fb_id': f['id']},
            UpdateExpression='SET fb_name = :fb_name, fb_gender = :fb_gender, fb_avatar = :fb_avatar',
            ExpressionAttributeValues={
                ':fb_name': f['name'],
                ':fb_gender': f['gender'] if 'gender' in f else None,
                ':fb_avatar': f['picture']['data']['url'] if 'picture' in f else None
            },
            ReturnValues='NONE'
        )

    # Compare and detect unfriended
    # Existed in current but not in new
    compare_diff_ids = list(
        set(current_fb_friends_ids) - set(new_fb_friends_ids))
    unfriend_str = ''
    for diff_id in compare_diff_ids:
        check_unf = call_fb_graph(access_token, diff_id)
        if 'name' in check_unf:
            # Query db get information
            unf_info = table_fb_friends.update_item(
                Key={'fb_id': diff_id},
                UpdateExpression='SET unf_at = :unf_at',
                ExpressionAttributeValues={
                    ':unf_at': int(time.time())
                },
                ReturnValues='ALL_NEW',
            )
            unf_info = unf_info['Attributes']
            unfriend_str += '❌ ' + \
                unf_info['fb_name'] + ' (' + unf_info['fb_id'] + ')\n'

    # Send email about unfriended
    # Trigger SNS
    if unfriend_str:
        client_sns.publish(
            TopicArn=os.getenv('SNS_TOPIC'),
            Subject='#TVQSAM x FB_Friend: Unfriend',
            Message='🔥 ALERT: There are some unfriends today\n' + unfriend_str
        )

    return True


def call_fb_graph(access_token, node, edges='', fields='', limit=1):
    http = urllib3.PoolManager()
    url = 'https://graph.facebook.com/v10.0/' + node + '/' + edges + \
        '?access_token=' + access_token + '&fields=' + \
        fields + '&limit=' + str(limit)
    request = http.request('GET', url)
    return json.loads(request.data)


# TODO: Move to file common function
def pluck(lst, key):
    return [x.get(key) for x in lst]