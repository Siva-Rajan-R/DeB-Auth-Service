import os
from minio import Minio
from minio.error import S3Error
from icecream import ic

# Load configs
endpoint = os.getenv("MINIO_ENDPOINT", "")
access_key = os.getenv("MINIO_ACCESS_KEY", "")
secret_key = os.getenv("MINIO_SECRET_KEY", "")
secure = os.getenv("MINIO_SECURE", "").lower() == "true"
bucket_name = os.getenv("MINIO_BUCKET_NAME", "")

# Initialize Client
try:
    minio_client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )
    ic("MinIO Client Initialized successfully")
except Exception as e:
    ic(f"Failed to initialize MinIO Client: {e}")
    minio_client = None

def upload_logo_to_minio(file_data, file_name: str, content_type: str) -> str:
    """
    Uploads logo file bytes to MinIO and returns a publicly viewable GET URL.
    """
    if not minio_client:
        raise RuntimeError("MinIO client is not initialized")
        
    try:
        # Create bucket if it doesn't exist
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            ic(f"Created MinIO Bucket: {bucket_name}")

            
            # Set public read-only policy so uploaded logos can be loaded by frontend
            policy = f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Sid": "PublicRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{bucket_name}/*"]
                    }}
                ]
            }}'''
            minio_client.set_bucket_policy(bucket_name, policy)

        # Upload file bytes
        length = len(file_data)
        import io
        stream = io.BytesIO(file_data)
        minio_client.put_object(
            bucket_name,
            file_name,
            stream,
            length,
            content_type=content_type
        )
        
        # Build direct access URL
        protocol = "https" if secure else "http"
        return f"{protocol}://{endpoint}/{bucket_name}/{file_name}"
    except S3Error as e:
        ic(f"MinIO S3 error during upload: {e}")
        raise RuntimeError(f"Storage upload failed: {e}")
    except Exception as e:
        ic(f"MinIO unexpected error during upload: {e}")
        raise RuntimeError(f"Storage upload failed: {e}")

def delete_logo_from_minio(url: str):
    """
    Deletes a logo from MinIO given its public URL.
    """
    if not minio_client or not url:
        return
        
    try:
        # Extract the file name from the URL (everything after the last slash)
        file_name = url.split('/')[-1]
        
        # We only delete if it looks like one of our generated logos
        if file_name and file_name.startswith('logo_'):
            minio_client.remove_object(bucket_name, file_name)
            ic(f"Deleted old logo from MinIO: {file_name}")
    except Exception as e:
        ic(f"Failed to delete old logo from MinIO: {e}")
