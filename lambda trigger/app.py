import json
import uuid
import random
import logging

logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

# pul-beedc0342cfc22d70b783fdc9a40e71fcbf262c6

def handler(event, context):
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event
    }
    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    res = '{} - {}'.format(
        uuid.uuid4(),
        random.randint(100000, 999999)
    )

    logger.info()

    print(res)

    return response