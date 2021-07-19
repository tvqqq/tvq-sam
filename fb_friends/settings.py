import json
import os
import layer
from boto3.dynamodb.conditions import Attr


def get(event, context):
    dynamodb = layer.ddb()

    # Get table records
    table_meta = dynamodb.Table(os.getenv('META_TABLE'))

    # Set dynamodb table name variable from env
    # Get access token from DynamoDB
    facebook = table_meta.get_item(
        Key={'id': 'facebook'}
    )
    facebook = dict(facebook)['Item']['amount']

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': json.dumps(facebook),
        'headers': {
            'Access-Control-Allow-Origin': 'http://localhost:5000' if os.getenv("AWS_SAM_LOCAL") else 'https://react-fb-manager.vercel.app'
        },
    }


def post(event, context):
    dynamodb = layer.ddb()
    body = json.loads(event['body'])

    # Get table records
    table_meta = dynamodb.Table(os.getenv('META_TABLE'))

    # Set dynamodb table name variable from env
    result = table_meta.update_item(
        Key={'id': 'facebook'},
        UpdateExpression='SET amount.access_token = :access_token',
        ExpressionAttributeValues={
            ':access_token': body['access_token']
        },
        ReturnValues='NONE'
    )

    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {
            'Access-Control-Allow-Origin': 'http://localhost:5000' if os.getenv("AWS_SAM_LOCAL") else 'https://react-fb-manager.vercel.app'
        },
    }
