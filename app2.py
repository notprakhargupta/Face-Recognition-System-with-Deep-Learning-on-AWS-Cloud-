import time
from flask import Flask, request, render_template
import csv
import boto3
from threading import Lock
import datetime 
import uuid
from settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


s3 = boto3.client(
        service_name='s3',
        region_name='us-east-1',
        aws_access_key_id = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)
bucket_name = 'bucket_name'

sqs = boto3.client(
        service_name='sqs',
        region_name='us-east-1',
        aws_access_key_id = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)

req_queue_url = ""

resp_queue_url = ""

unprocessed_messages = {}
lock = Lock()


app = Flask(__name__)


def poll_for_messages(unique_id):
    response_timeout = datetime.datetime.now() + datetime.timedelta(seconds=100000)
    print("in call -  ", unique_id)
    while datetime.datetime.now() < response_timeout:
        print("polling")
        response = sqs.receive_message(QueueUrl=resp_queue_url, WaitTimeSeconds=20)
        if 'Messages' in response:
            for message in response['Messages']:
                print("got response -  ",message['Body'])
                classifiction_result, msg_id = message['Body'].split('|')
                if msg_id == unique_id:
                    sqs.delete_message(QueueUrl=resp_queue_url, ReceiptHandle=message['ReceiptHandle'])
                    return classifiction_result
                else:
                    print("no match for ", unique_id)
                    with lock:
                        unprocessed_messages[msg_id] = {"body": classifiction_result, "receipt_handle": message['ReceiptHandle']}


                with lock:
                    if unique_id in unprocessed_messages:
                        stored_msg = unprocessed_messages[unique_id]["body"]
                        receipt_handle = unprocessed_messages[unique_id]["receipt_handle"]
                        sqs.delete_message(QueueUrl=resp_queue_url, ReceiptHandle=receipt_handle)
                        del unprocessed_messages[unique_id]
                        return stored_msg


@app.route('/')
def index():
    return render_template('index.html')

# Route to handle POST requests
@app.route("/", methods=["POST"])
def recognize_faces_endpoint():
    # Get the input file from the request payload
    input_file = request.files["inputFile"]
    filename = input_file.filename.split(".")[0]

    unique_id = str(uuid.uuid4())

    s3_key = filename + '.jpg'
    message_body = unique_id + '_' + s3_key

    # Send message to the SQS queue
    sqs.send_message(
        QueueUrl=req_queue_url,
        MessageBody=message_body
    )

    print("before call -  ", unique_id)
    result = poll_for_messages(unique_id)
    while result is None:
        #time.sleep(1)
        result = poll_for_messages(unique_id)
    
    return result

    #s3.upload_fileobj(input_file, bucket_name, s3_key)
    
    # Return the prediction result in the specified format


if __name__ == "__main__":
    # Run the Flask app with threading enabled for handling concurrent requests
    #app.run(host='0.0.0.0', threaded=True)
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000, threads=8)