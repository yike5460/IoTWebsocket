import os
import sys
import json
import csv
import re
import numpy as np
import datetime
import time
import getopt

import logging
import boto3
from botocore.exceptions import ClientError

inputFile = ''
outputFile = ''
originalFile = 'original.json'
tempJsonFile = 'originalTransformed.json'
tempCsvFile = 'utilityAdapted.csv'
finalCsvFile = 'utilityAdaptedFinal.csv'

s3 = boto3.client('s3')

def preprocess(argv):

    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=", "ofile="])
    except getopt.GetoptError:
        print('usage: python {} -i <s3 url of inputFile>, -o <s3 url of outputFile>, format like like s3://bucket/prefix/file.json'.format(__file__))
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('usage: python {} -i <s3 url of inputFile>, -o <s3 url of outputFile>, format like like s3://bucket/prefix/file.json'.format(__file__))
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputFile = arg
        elif opt in ("-o", "--ofile"):
            outputFile = arg
    # original data schema
    # {
    #     "DEVICE_NAME": "E0991000416",
    #     "LABEL": "x_Uab",
    #     "VAL": "35249.66796875",
    #     "PRODUCT_KEY": "TC-1020",
    #     "COLLECT_TIME": 1619049702000,
    #     "ARRIVAL_TIME": 1619049724755
    # }{
    #     "DEVICE_NAME": "E0991000416",
    #     "LABEL": "x_Ubc",
    #     "VAL": "35173.0703125",
    #     "PRODUCT_KEY": "TC-1020",
    #     "COLLECT_TIME": 1619049702000,
    #     "ARRIVAL_TIME": 1619049724755
    # }

    bucketName = inputFile.split("//")[1].split("/")[0]
    objectName = inputFile.split("//")[1].split("/", 1)[1]
    s3.download_file(bucketName, objectName, originalFile)

    fp1 = open(originalFile, 'r+')

    # transform to json list
    # [{
    #     "DEVICE_NAME": "E0991000416",
    #     "LABEL": "x_Uab",
    #     "VAL": "35249.66796875",
    #     "PRODUCT_KEY": "TC-1020",
    #     "COLLECT_TIME": 1619049702000,
    #     "ARRIVAL_TIME": 1619049724755
    # }, ... ]
    fp2 = open(tempJsonFile, mode='a+', encoding='utf-8')
    fp2.write('[')

    for line in fp1.readlines():
        tmp=re.sub(r'}{', r'},{', line)
        fp2.write(tmp)
    fp2.write(']')
    fp1.close()
    fp2.close()

    # transform to csv
    # LCLid,Acorn,KWH/hh (per half hour) ,stdorToU,Acorn_grouped,DateTime
    # E0991000416,x_Uab,35249.66796875,TC-1020,1619049702000,1619049724755
    with open(tempJsonFile, mode='r', encoding='utf-8') as fp2:
        data_list = json.load(fp2)
    sheet_title = ["LCLid", "Acorn", "KWH/hh (per half hour) ", "stdorToU", "Acorn_grouped", "DateTime"]
    sheet_data = []
    for data in data_list:
        sheet_data.append(data.values())
    csv_fp = open(tempCsvFile, "w", encoding='utf-8', newline='')
    writer = csv.writer(csv_fp)
    writer.writerow(sheet_title)
    writer.writerows(sheet_data)

    # clean up
    fp2.close()
    if os.path.exists(tempJsonFile):
        os.remove(tempJsonFile)
    csv_fp.close()

    # LCLid,Acorn,KWH/hh (per half hour) ,stdorToU,Acorn_grouped,DateTime
    # E0991000416,x_Uab,35249.66796875,TC-1020,1619049702000,2012-10-15 19:30:00.0000000
    all = np.loadtxt(tempCsvFile, dtype='str', delimiter=",", skiprows=1)

    # initialize unused column
    all[:, 4] = np.zeros([all[:, 4].shape[0],], dtype = int)

    # transform timestamp to readable datetime
    DataTime = all[:, 5]
    convert = lambda x: str(np.datetime64(int(x), 'ms')).replace("T", " ")
    newDataTime = np.array([convert(timeStamp) for timeStamp in DataTime])    
    
    all[:, 5] = newDataTime
    
    # newArray = np.hstack((all[:, :5], np.expand_dims(newDataTime, axis=1)))

    # shift column to final schema
    # LCLid,stdorToU,DateTime,KWH/hh (per half hour) ,Acorn,Acorn_grouped
    # E0991000416,TC-1020,2021-04-22 00:02:04.755,35249.66796875,x_Uab,1619049702000
    finalArray = np.hstack((np.expand_dims(all[:, 0], axis=1), np.expand_dims(all[:, 3], axis=1), np.expand_dims(all[:, 5], axis=1), np.expand_dims(all[:, 2], axis=1), np.expand_dims(all[:, 1], axis=1), np.expand_dims(all[:, 4], axis=1)))

    csv_final_fp = open(finalCsvFile, "w", encoding='utf-8', newline='')
    np.savetxt(csv_final_fp, finalArray, delimiter=',',  header='LCLid,stdorToU,DateTime,KWH/hh (per half hour) ,Acorn,Acorn_grouped', comments='', fmt='%s')


    bucketName = outputFile.split("//")[1].split("/")[0]
    objectName = outputFile.split("//")[1].split("/", 1)[1]
    try:
        response = s3.upload_file(finalCsvFile, bucketName, objectName)
    except ClientError as e:
        logging.error(e)
        return False

    # clean up
    csv_fp.close()
    if os.path.exists(tempCsvFile):
        os.remove(tempCsvFile)
    csv_final_fp.close()

def test_case(argv):
    pass

if __name__ == "__main__":
    preprocess(sys.argv[1:])
