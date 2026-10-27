-- Alternative for source 3/3: the company drive as an S3-compatible FILESTORE (MinIO from docker-compose).
-- Untested against a live Zetaris on 27/10; the default registration uses a REST table on the public repository.
CREATE LIGHTNING DATABASE BRIKK_DRIVE_S3 DESCRIBE BY "Brikk company drive"
CREATE LIGHTNING FILESTORE TABLE procedures FROM BRIKK_DRIVE_S3 FORMAT CSV OPTIONS (
  PATH "s3a://brikk-drive/procedures/procedures.csv",
  s3Endpoint "http://host.docker.internal:9000",
  useS3PathStyleAccess "true",
  AWSACCESSKEYID "osef",
  AWSSECRETACCESSKEY "osef_local_only",
  header "true",
  inferSchema "true"
)
SELECT procedure_id, department, when_to_use FROM brikk_drive_s3.procedures
