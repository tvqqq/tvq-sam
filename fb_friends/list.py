import json
import os
import layer
from boto3.dynamodb.conditions import Attr
import decimal


def lambda_handler(event, context):
    LIMIT = 20
    dynamodb = layer.ddb()

    # Get table records
    table_fb_friends = dynamodb.Table(os.getenv('FB_FRIEND_TABLE'))

    # There is a next record
    query = event['queryStringParameters']
    if query is not None and 'next' in query:
        exclusiveStartKey = json.loads(
            '{"fb_id": "' + query['next'] + '"}')
        response = table_fb_friends.scan(
            Limit=LIMIT, ExclusiveStartKey=exclusiveStartKey)
    else:
        # Initial request
        response = table_fb_friends.scan(Limit=LIMIT)

    result = {
        'data': response['Items'],
        'next': response.get('LastEvaluatedKey', {}).get('fb_id')
    }

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': json.dumps(result, cls=DecimalEncoder),
        'headers': {
            'Access-Control-Allow-Origin': 'http://localhost:5000' if os.getenv("AWS_SAM_LOCAL") else 'https://react-fb-manager.vercel.app'
        },
    }


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
