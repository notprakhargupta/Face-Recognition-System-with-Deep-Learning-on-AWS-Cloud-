from settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
import boto3
from face_recognition import face_match


sqs = boto3.client(
        service_name='sqs',
        region_name='us-east-1',
        aws_access_key_id = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)

req_queue_url = ""

resp_queue_url =""



def process_image():
    while True:
        response = sqs.receive_message(QueueUrl=req_queue_url)
        if 'Messages' in response:
            for message in response['Messages']:
                filename = '_'.join(message['Body'].split('_')[1:])
                image_path = "./face_images_1000/" + filename
                msg_id = message['Body'].split('_')[0]
                result = face_match(image_path)
                msg_body = filename.split(".")[0] + ":" + result[0] + "|" + msg_id
                print(msg_body) 
                send_message_to_sqs = sqs.send_message(QueueUrl=resp_queue_url, MessageBody=msg_body)
                if send_message_to_sqs:
                    sqs.delete_message(QueueUrl=req_queue_url, ReceiptHandle=message['ReceiptHandle'])





process_image()