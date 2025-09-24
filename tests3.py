from django.core.files.storage import default_storage

# List all files in your bucket
try:
    from storages.backends.s3boto3 import S3Boto3Storage
    storage = default_storage
    # This will show all objects in the bucket
    files = []
    for obj in storage.bucket.objects.all():
        files.append(obj.key)
    print("Files in bucket:", files)
except Exception as e:
    print(f"Error listing files: {e}")

# Or check specific file
exists = default_storage.exists('voices/test-public.mp3')
print(f"File 'voices/test-public.mp3' exists: {exists}")