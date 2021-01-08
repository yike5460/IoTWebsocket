import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):

    # Log the values received in the event and context arguments
    logger.info('$disconnect event: ' + json.dumps(event, indent=2))
    logger.info(f'$disconnect event["requestContext"]["connectionId"]: {event["requestContext"]["connectionId"]}')

    # Retrieve the name of the DynamoDB table to store connection IDs
    table_name = 'IoTconnection' # os.environ['TableName']

    # Remove the connection ID from the table
    item = {'connectionId': {'S': event['requestContext']['connectionId']}}
    dynamodb_client = boto3.client('dynamodb')
    try:
        dynamodb_client.delete_item(TableName=table_name, Key=item)
    except ClientError as e:
        logger.error(e)
        raise ValueError(e)

    # Construct response
    response = {'statusCode': 200}
    return response