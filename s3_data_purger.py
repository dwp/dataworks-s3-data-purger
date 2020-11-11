#!/usr/bin/env python
import ast
import json
import logging
import argparse
import os
from boto3.dynamodb.conditions import Key, Attr
import boto3
from pythonjsonlogger import jsonlogger

S3_PREFIX = "s3_prefix"
NUM_OF_RETENTION_DAYS = "num_of_retention_days"
DATA_PRODUCT_NAME = "data_product"


def configure_log():
    """Configure JSON logger."""
    log_level = args.log_level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % log_level)
    if len(logging.getLogger().handlers) > 0:
        logging.getLogger().setLevel(log_level)
    else:
        logging.basicConfig(level=log_level)
    logger = logging.getLogger()
    logger.propagate = False
    console_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

def get_client(service_name):
    client = boto3.client(service_name)
    return client

def get_resource(service_name):
    return boto3.resource(service_name, region_name=args.aws_region)

def get_list_keys_for_prefix(s3_client, s3_publish_bucket, s3_prefix):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_publish_bucket, Prefix=s3_prefix)
    for page in pages:
        for obj in page["Contents"]:
            keys.append(obj["Key"])
    if s3_prefix in keys:
        keys.remove(s3_prefix)
    return keys


def scan_table(dynamodb_resource,data_pipeline_metdata_table,data_product_name):
    table = dynamodb_resource.Table(data_pipeline_metdata_table)
    response = table.scan(FilterExpression=Attr('DataProduct').eq(data_product_name) & Attr('Status').eq('Completed'),
                          ProjectionExpression="#Date",
                          ExpressionAttributeNames = {"#Date": "Date"})
    list_dates_dict = response['Items']
    return list_dates_dict


def get_parameters():
    """Define and parse command line args."""
    parser = argparse.ArgumentParser(
        description="Send arguments for the S3 data purger."
    )

    # Parse command line inputs and set defaults
    parser.add_argument("--aws-region", default="eu-west-2")
    parser.add_argument("--s3_publish_bucket", default="NOT_SET")
    parser.add_argument("--data_pipeline_metdata_table", default="NOT_SET")
    parser.add_argument("--s3_data_purger_log_level", default="INFO")

    _args = parser.parse_args()

    # Override arguments with environment variables where set
    if "S3_PUBLISH_BUCKET" in os.environ:
        _args.s3_publish_bucket = os.environ.get("S3_PUBLISH_BUCKET")

    if "DATA_PIPELINE_METADATA_TABLE" in os.environ:
        _args.data_pipeline_metdata_table = os.environ.get("DATA_PIPELINE_METADATA_TABLE")

    if "S3_DATA_PURGER_LOG_LEVEL" in os.environ:
        _args.log_level = os.environ.get("S3_DATA_PURGER_LOG_LEVEL").upper()

    if "AWS_REGION" in os.environ:
        _args.aws_region = os.environ["AWS_REGION"]

    return _args

args = get_parameters()


def handler(event: dict = {}, context: object = None) -> dict:
    """Deletes old S3 files based on s3_publish_bucket,s3_prefix ,data_pipeline_metdata_table, DataProduct and num_of_retention_days parameters."""
    logger = configure_log()

    s3_publish_bucket = args.s3_publish_bucket
    data_pipeline_metdata_table = args.data_pipeline_metdata_table

    if S3_PREFIX in event and NUM_OF_RETENTION_DAYS in event and  DATA_PRODUCT_NAME in event:
        s3_prefix = event[S3_PREFIX]
        num_of_retention_days = event[NUM_OF_RETENTION_DAYS]
        data_product_name = event[DATA_PRODUCT_NAME]
    elif "Records" in event:
        sns_message = event["Records"][0]["Sns"]
        payload = json.loads(sns_message["Message"])
        s3_prefix = payload[S3_PREFIX]
        num_of_retention_days = payload[NUM_OF_RETENTION_DAYS]
        data_product_name = payload[DATA_PRODUCT_NAME]

    s3_client = get_client("s3")
    dynamodb_resource = get_resource("dynamodb")
    list_dates_dict = scan_table(dynamodb_resource,data_pipeline_metdata_table,data_product_name)
    #Remove duplicates if its runs multiple times in a day
    unique_dict = [dict(t) for t in {tuple(d.items()) for d in list_dates_dict}]

    list_of_dates = []
    #Convert List of Dict to List of list
    for idx, sub in enumerate(unique_dict, start = 0):
        print(list(sub.values()))
        list_of_dates.append(list(sub.values()))
    list_of_dates.sort()
    purge_list = list_of_dates[:len(list_of_dates)-num_of_retention_days]
    logging.info("List of Dates to purge the s3 files :" + purge_list  )
    #Get the S3 prefix keys
    s3_keys = get_list_keys_for_prefix(s3_client, s3_publish_bucket, s3_prefix)

    for purge_sublist in purge_list:
        for date in purge_sublist:
            for s3_prefix in s3_keys:
                if date in s3_prefix:
                    print(s3_prefix)
                    try:
                        response = s3_client.delete_object(Bucket=s3_publish_bucket,Key=s3_prefix)
                        logging.info("Deleted S3 object of S3_BUCKET:" + s3_publish_bucket + "S3_PREFIX:" + s3_prefix )
                    except Exception as e:
                        print(e, "S3_BUCKET=", s3_publish_bucket,"S3_PREFIX=",s3_prefix )
                        logger.error(e + "S3_BUCKET=" + s3_publish_bucket +"S3_PREFIX=" + s3_prefix)

if __name__ == "__main__":
    logger = configure_log()
    try:
        handler()
    except Exception as e:
        logger.error(e)

