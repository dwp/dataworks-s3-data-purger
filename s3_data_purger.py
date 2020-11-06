#!/usr/bin/env python

import ast
import json
import logging
import os
from datetime import date

import boto3
import yaml
from pythonjsonlogger import jsonlogger

OLD_DATA_S3_PREFIX = "s3_prefix"
NUM_OF_DAYS = "num_of_days"


def configure_log():
    """Configure JSON logger."""
    log_level = os.environ.get("S3_DATA_PURGER_LOG_LEVEL", "INFO").upper()
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


def today():
    return str(date.today())


def get_client(service_name):
    client = boto3.client(service_name)
    return client


def get_resource(service_name):
    return boto3.resource(service_name, region_name="${aws_default_region}")


def read_env_param(param_name):
    return os.getenv(param_name)


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


def handler(event: dict = {}, context: object = None) -> dict:
    """Deletes old redundant S3 data based on s3_prefix and num_of_days parameters."""
    logger = configure_log()
    s3_bucket = read_env_param("S3_PUBLISH_BUCKET")
    data_pipeline_metdata_table = read_env_param("DATA_PIPELINE_METADATA_TABLE")
    s3_prefix = event[OLD_DATA_S3_PREFIX]
    num_of_days = event[NUM_OF_DAYS]



    return ""


if __name__ == "__main__":
    logger = configure_log()
    try:
        handler()
    except Exception as e:
        logger.error(e)
