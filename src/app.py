import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
import base64
# import simplejson

# Set up logging
logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    # Send the message to each connection
    api_client = boto3.client('apigatewaymanagementapi', endpoint_url='https://oxa9mefe9i.execute-api.cn-northwest-1.amazonaws.com.cn/v1')
    print(json.dumps(event['Records']))
    for record in event['Records']:
        # decode data to raw string
        rawData = base64.b64decode(record['kinesis']['data'])

        # transform to json string
        stringData = json.loads(rawData.decode('utf8').replace("'", '"'))
        jsonData = json.dumps(stringData, indent=4, sort_keys=True)
        
        # fetch payload and connectionId
        payload = eval(jsonData)['payload']
        connectionId = eval(jsonData)['connectionId']

        # transform to binary format
        binaryPayload = json.dumps(payload, indent=4).encode('utf-8')

        logger.info("sending payload {} with connectionId {} to websocket".format(binaryPayload, connectionId))
        
        try:
            api_client.post_to_connection(Data=binaryPayload,
                                          ConnectionId=connectionId)
        except ClientError as e:
            logger.error(e)

    # Construct response
    response = {'statusCode': 200}
    return response