# dataworks-s3-data-purger

## Utility Lambda for deleting old redundant S3 data

## What does it do?

This is a generic Lambda function that can be used to delete redundant S3 data.
It takes 3 parameters s3_prefix representing the location of data , num_of_retention_days and data product.
Data processed successfully and older than num_of_retention_days will be deleted from location s3_prefix.

