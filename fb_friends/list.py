import json
import os
import layer
from boto3.dynamodb.conditions import Attr
import decimal
import urllib.parse


def lambda_handler(event, context):
    LIMIT = 20
    dynamodb = layer.ddb()

    # Get table records
    table_fb_friends = dynamodb.Table(os.getenv('FB_FRIEND_TABLE'))

    # There is a next record
    query = event['queryStringParameters']
    if query is not None and 'next' in query:
        exclusiveStartKey = json.loads(urllib.parse.unquote(query['next']))
        response = table_fb_friends.query(**{
            'Limit': LIMIT,
            'KeyConditionExpression': 'unf_at = :unf_at',
            'ExpressionAttributeValues': {
                ':unf_at': 0,
            },
            'IndexName': 'unf_at-created_at-index',
            'ScanIndexForward': False,
            'ExclusiveStartKey': {
                'unf_at': 0,
                'fb_id': exclusiveStartKey['fb_id'],
                'created_at': int(exclusiveStartKey['created_at'])
            }
        })
    elif query is not None and 'unf' in query:
        response = table_fb_friends.scan(
            FilterExpression=Attr("unf_at").ne(0))
    elif query is not None and 'search' in query:
        search = query['search']
        kwargs = {
            'FilterExpression': 'contains(#fb_name, :val) or contains(#fb_id, :val)',
            'ExpressionAttributeNames': {
                '#fb_name': 'fb_name',
                '#fb_id': 'fb_id',
            },
            'ExpressionAttributeValues': {
                ':val': search,
            },
        }
        response = table_fb_friends.scan(**kwargs)

    else:
        # Initial request
        response = table_fb_friends.query(**{
            'Limit': LIMIT,
            'KeyConditionExpression': 'unf_at = :unf_at',
            'ExpressionAttributeValues': {
                ':unf_at': 0,
            },
            'IndexName': 'unf_at-created_at-index',
            'ScanIndexForward': False,
        })

    result = {
        'data': response['Items'],
        'next': response.get('LastEvaluatedKey', {}).get('fb_id')
    }

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': json.dumps(result, cls=DecimalEncoder),
        'headers': {
            'Access-Control-Allow-Origin': 'http://localhost:3001' if os.getenv("AWS_SAM_LOCAL") else 'https://react-fb-manager.vercel.app'
        },
    }


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
