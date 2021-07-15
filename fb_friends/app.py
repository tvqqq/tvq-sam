import boto3
import json
import os
import urllib3
import time
import layer
from boto3.dynamodb.conditions import Attr


def lambda_handler(event, context):
    client_sns = boto3.client('sns')

    dynamodb = layer.ddb()

    # Get access token from DynamoDB
    table_meta = dynamodb.Table(os.getenv('META_TABLE'))
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
        return False

    # Get list current FB friends
    table_fb_friends = dynamodb.Table(os.getenv('FB_FRIEND_TABLE'))

    current_fb_friends = table_fb_friends.scan(
        ProjectionExpression='fb_id',
        FilterExpression="unf_at = :val",
        ExpressionAttributeValues={
            ':val': 0
        }
    )
    current_fb_friends_ids = layer.pluck(current_fb_friends['Items'], 'fb_id')

    # Call API get list updated FB friends
    new_fb_friends_response = call_fb_graph(
        access_token, 'me', 'friends', 'name,picture.width(2048){url},gender&pretty=0', 5000)

    new_fb_friends_ids = []
    for f in new_fb_friends_response['data']:
        new_fb_friends_ids.append(f['id'])
        table_fb_friends.update_item(
            Key={'fb_id': f['id']},
            UpdateExpression='SET fb_name = :fb_name, fb_gender = :fb_gender, fb_avatar = :fb_avatar, unf_at = :unf_at',
            ExpressionAttributeValues={
                ':fb_name': f['name'],
                ':fb_gender': f['gender'] if 'gender' in f else None,
                ':fb_avatar': f['picture']['data']['url'] if 'picture' in f else None,
                ':unf_at': 0
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
