import boto3
import os


def ddb():
    if os.getenv("AWS_SAM_LOCAL"):
        dynamodb = boto3.resource(
            'dynamodb', endpoint_url="http://host.docker.internal:8001")
    else:
        dynamodb = boto3.resource('dynamodb')
    return dynamodb


def pluck(lst, key):
    return [x.get(key) for x in lst]


def logger(val):
    print('\x1b[6;30;42m' + str(val) + '\x1b[0m')
