# sqs_utils.py

import boto3
from settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
import pdb

class SQSUtils:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        self.client = self.session.client('sqs')

    def send_message(self, queue_url, message_body):
        """Send a message to the given SQS queue."""
        try:
            response = self.client.send_message(QueueUrl=queue_url, MessageBody=message_body)
            return {
                'status': True,
                'message_id': response['MessageId']
            }
        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }

    def receive_messages(self, queue_url, max_messages=2, wait_time=20):
        """Receive messages from the given SQS queue."""
        try:
            response = self.client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time
            )
            # pdb.set_trace()
            return response.get('Messages')
        
        except Exception as e:
            # pdb.set_trace()
            print(f'Error receiving messages: {e}')
            return None

    def delete_message(self, queue_url, receipt_handle):
        """Delete a message from the given SQS queue using its receipt handle."""
        try:
            self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            return True
        except Exception as e:
            print(f'Error deleting message: {e}')
            return False