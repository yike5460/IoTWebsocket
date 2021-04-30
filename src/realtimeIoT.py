import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
import base64

import datetime
import time
# import simplejson

# Set up logging
logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
kinesisAction = 'kinesisFetch'
kinesisFreq = 3600

def handler(event, context):
    # Send the message to each connection
    api_client = boto3.client('apigatewaymanagementapi', endpoint_url='https://2ei2kyn7u6.execute-api.cn-northwest-1.amazonaws.com.cn/v1')
    logger.info("event record is {}".format(json.dumps(event['Records'])))
    

    dynamodb_client = boto3.client('dynamodb')
    kinesis_client = boto3.client('kinesis')
    
    table_name = 'IoTconnection' # os.environ['TableName']
    
    # Retrieve all connection IDs from the table
    try:
        response = dynamodb_client.scan(TableName=table_name,
                                        ProjectionExpression='connectionId')
    except ClientError as e:
        logger.error(e)
        raise ValueError(e)
    
    # Sending to all connected websocket
    for item in response['Items']:
        connectionId = item['connectionId']['S']
        try:
            for record in event['Records']:
                # decode data to raw string
                rawData = base64.b64decode(record['kinesis']['data'])
                logger.info("rawData is {}".format(rawData))
                
                # from client direction, depend on wss input content
                if(rawData.decode('utf8').find(kinesisAction)!=-1):
                    
                    # transform to json string
                    stringData = json.loads(rawData.decode('utf8').replace("'", '"'))
                    jsonData = json.dumps(stringData, indent=4, sort_keys=True)
                    
                    # fetch payload and connectionId
                    payload = eval(jsonData)['payload']
                    print("payload here is {}".format(payload))
                    # overwrite connectionId directly, should be same with value stored in dynamoDB
                    connectionId = eval(jsonData)['connectionId']
        
                    # transform to binary format, extract fetch frequencyTBD
                    binaryPayload = json.dumps(payload, indent=4).encode('utf-8')
                    
                    start_timestamp = int(time.time()) - kinesisFreq
                    response = kinesis_client.get_shard_iterator(
                        StreamName='IoTPython-EventStream-5V9OW0KOLAE8',
                        ShardId='shardId-000000000000',
                        ShardIteratorType='AT_TIMESTAMP',
                        Timestamp=start_timestamp # datetime.date.today()
                    )
                    print("shard is {}".format(response['ShardIterator']))
            
                    shard_iter = response['ShardIterator']
                    
                    # local debug
                    # response = kinesis_client.get_records(ShardIterator=shard_iter, Limit=10)
                    # print("historical record {}".format(response['Records']))
                    # print("historical record {}".format(response['NextShardIterator']))
                    
                    # constrain to 100 records
                    record_count = 0
                    while record_count < 100:
                        response = kinesis_client.get_records(ShardIterator=shard_iter, Limit=10)
                        shard_iter = response['NextShardIterator']
                        records = response['Records']
                        record_count += len(records)
                        for i in range(len(records)):
                            rawData = records[i]['Data']
                            logger.info("sending payload {} with connectionId {} to websocket".format(rawData, connectionId))
                            try:
                                api_client.post_to_connection(Data=rawData,
                                                              ConnectionId=connectionId)
                            except ClientError as e:
                                logger.error(e) 
                
                # from kinesis direction, display output directly
                else:
                    logger.info("sending payload {} with connectionId {} to websocket".format(rawData, connectionId))
                    try:
                        api_client.post_to_connection(Data=rawData,
                                                      ConnectionId=connectionId)
                    except ClientError as e:
                        logger.error(e)                                
        except ClientError as e:
            logger.error(e)

    # Construct response
    response = {'statusCode': 200}
    return response