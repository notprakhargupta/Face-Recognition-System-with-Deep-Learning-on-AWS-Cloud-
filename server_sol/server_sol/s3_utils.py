import boto3
from settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
import os

class S3Utils:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        self.client = self.session.client('s3')
        
    def upload_to_s3(self, file_name, bucket, extra_args, object_name=None):
        '''
        Uploads the file into the s3 bucket
        '''
        if object_name is None:
            object_name = file_name.split('/')[-1]

        try:
            self.client.upload_file(file_name, bucket, object_name, ExtraArgs =extra_args)
            return {
                's3_object_key': object_name,
                'uuid': extra_args['Metadata']['uuid'],
                'file_name': os.path.basename(file_name),
                'bucket_name': bucket,
                'uploaded': True
                }
        
        except Exception as e:
            return {
                'error': str(e),
                'uploaded': False
            }