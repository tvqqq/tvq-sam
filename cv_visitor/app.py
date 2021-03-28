import boto3
import json
import os


def lambda_handler(event, context):
    # Init DynamoDB Client
    if os.getenv("AWS_SAM_LOCAL"):
        dynamodb = boto3.resource(
            'dynamodb', endpoint_url="http://host.docker.internal:8001")
    else:
        dynamodb = boto3.resource('dynamodb')

    # Set dynamodb table name variable from env
    table = dynamodb.Table(os.getenv('META_TABLE'))

    # Atomic update item in table or add if doesn't exist
    ddbResponse = table.update_item(
        Key={'id': 'cv_visitors'},
        UpdateExpression='ADD amount :inc',
        ExpressionAttributeValues={':inc': 1},
        ReturnValues='UPDATED_NEW',
    )

    # Format dynamodb response into variable
    responseBody = json.dumps(
        {'cv_visitors': int(float(ddbResponse['Attributes']['amount']))}
    )

    # Create api response object
    apiResponse = {
        'isBase64Encoded': False,
        'statusCode': 200,
        'body': responseBody,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-requested-with',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
        },
    }

    return apiResponse
