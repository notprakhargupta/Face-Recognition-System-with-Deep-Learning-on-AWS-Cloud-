
#!/usr/bin/env python3.10

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import ast
import uuid
import datetime
from threading import Lock
from s3_utils import S3Utils
from sqs_utils import SQSUtils
from utils import is_allowed_file_format, create_directory
from settings import UPLOAD_FOLDER,S3_INPUT_BUCKET_NAME, SQS_REQUEST_QUEUE_URL, SQS_RESPONSE_QUEUE_URL, TIMEOUT

app = Flask(__name__)
CORS(app)

unprocessed_messages = {}
lock = Lock()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
upload_folder_path = os.path.join(os.getcwd(),'..',app.config['UPLOAD_FOLDER'])

s3_utils = S3Utils()
sqs_utils = SQSUtils()

# Function to check and process any messages that have arrived out of order
def process_stored_messages(unique_id):
    with lock:
        if unique_id in unprocessed_messages:
            stored_msg = unprocessed_messages.pop(unique_id)
            sqs_utils.delete_message(queue_url=SQS_RESPONSE_QUEUE_URL, receipt_handle=stored_msg['receipt_handle'])
            return stored_msg['body']

@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'GET':
        return jsonify({
            'message': 'Hello from the web-tier'
        })
    if request.method == 'POST':
        unique_id = str(uuid.uuid4())
        file = request.files.get('inputFile')
        if not file or file.filename == '':
            return jsonify({'error': 'No file provided or file selected'})

        if not is_allowed_file_format(file.filename):
            return jsonify({'error': 'Invalid file format'})
        
        file_path = os.path.join(upload_folder_path, file.filename)
        file.save(file_path)
        tag_string = f"uuid={unique_id}"
        upload_res = s3_utils.upload_to_s3(file_name=file_path, bucket=S3_INPUT_BUCKET_NAME, extra_args={
            'Metadata': {
                'uuid': unique_id
            },
            'Tagging': tag_string
        })

        if upload_res['uploaded']:
            req_queue = sqs_utils.send_message(queue_url=SQS_REQUEST_QUEUE_URL, message_body=str(upload_res))
            if req_queue['status']:
                response_timeout = datetime.datetime.now() + datetime.timedelta(seconds=TIMEOUT)
                try:
                    while datetime.datetime.now() < response_timeout:
                        # Before polling for new messages, check if the response has already been received out of order
                        stored_response = process_stored_messages(unique_id)
                        if stored_response:
                            return stored_response['classification']

                        messages = sqs_utils.receive_messages(queue_url=SQS_RESPONSE_QUEUE_URL)
                        if not messages:
                            continue
                        for msg in messages:
                            msg_body = ast.literal_eval(msg['Body'])
                            msg_uuid = msg_body.get('uuid', None)

                            if msg_uuid == unique_id:
                                sqs_utils.delete_message(queue_url=SQS_RESPONSE_QUEUE_URL, receipt_handle=msg['ReceiptHandle'])
                                return msg_body['classification']
                            else:
                                with lock:
                                    unprocessed_messages[msg_uuid] = {"body": msg_body, "receipt_handle": msg['ReceiptHandle']}
                            
                    # Final check for stored messages before concluding timeout
                    final_stored_response = process_stored_messages(unique_id)
                    if final_stored_response:
                        return final_stored_response['classification']
                        
                    return {'status': 'error', 'message': 'Timeout waiting for result'}
                except Exception as e:
                    return {'error': str(e)}
    
if __name__ == '__main__':
    create_directory(os.path.join(os.getcwd(),'..',app.config['UPLOAD_FOLDER']))
    app.run(host='0.0.0.0', port=3000, debug=True, threaded=True)