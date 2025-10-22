# Troubleshooting Guide

## Common Issues and Solutions

### Connection Issues

#### Elasticsearch Connection Failed
**Symptom**: `Failed to connect to Elasticsearch: ...`

**Solutions**:
1. Verify Elasticsearch is running and accessible:
   ```bash
   curl -k https://ES_HOST:ES_PORT
   ```

2. Check credentials:
   - Verify ES_USERNAME and ES_PASSWORD are correct
   - Or verify ES_API_KEY is valid

3. Check SSL settings:
   - If using self-signed certificates, set `ES_VERIFY_CERTS=false`
   - Or provide CA certificate path in `ES_CA_CERTS`

4. Check network connectivity:
   ```bash
   docker run --rm --env-file .env elasticsearch-snowpipe --once
   # Check if ES_HOST is reachable from container
   ```

#### Snowflake Connection Failed
**Symptom**: `Failed to connect to Snowflake: ...`

**Solutions**:
1. Verify account identifier:
   ```bash
   # Format: account.region or account.region.cloud
   SF_ACCOUNT=mycompany.us-east-1
   ```

2. Check credentials:
   - Password: Verify SF_PASSWORD is correct
   - Private key: Verify SF_PRIVATE_KEY_PATH points to valid key file

3. Verify warehouse and database exist:
   ```sql
   SHOW WAREHOUSES;
   SHOW DATABASES;
   USE DATABASE ES_DATA;
   USE WAREHOUSE COMPUTE_WH;
   ```

4. Check user permissions:
   ```sql
   SHOW GRANTS TO USER your_username;
   ```

### Index and Data Issues

#### No Indexes Found
**Symptom**: `No indexes found matching the configured patterns`

**Solutions**:
1. Check index patterns:
   ```bash
   ES_INDEXES=logs-*,metrics-*
   # Make sure patterns match existing indexes
   ```

2. List indexes in Elasticsearch:
   ```bash
   curl -u elastic:password https://ES_HOST:9200/_cat/indices
   ```

3. Verify patterns include wildcard:
   ```bash
   # Wrong: ES_INDEXES=logs
   # Right: ES_INDEXES=logs-*
   ```

#### Documents Not Syncing
**Symptom**: Documents show in ES but not in Snowflake

**Solutions**:
1. Check Snowflake table:
   ```sql
   SELECT COUNT(*) FROM es_your_index;
   SELECT * FROM es_your_index LIMIT 10;
   ```

2. Check for errors in logs:
   ```bash
   docker logs es-snowpipe | grep ERROR
   ```

3. Verify table permissions:
   ```sql
   SHOW GRANTS ON TABLE es_your_index;
   ```

4. Check batch size:
   ```bash
   # If documents are very large, reduce batch size
   BATCH_SIZE=100
   ```

### Performance Issues

#### Sync Too Slow
**Symptom**: Syncing takes too long

**Solutions**:
1. Increase batch size:
   ```bash
   BATCH_SIZE=5000  # Default is 1000
   ```

2. Increase Snowflake warehouse size:
   ```sql
   ALTER WAREHOUSE COMPUTE_WH SET WAREHOUSE_SIZE = 'LARGE';
   ```

3. Check Elasticsearch performance:
   ```bash
   # Monitor ES cluster health
   curl -u elastic:password https://ES_HOST:9200/_cluster/health
   ```

4. Reduce number of indexes:
   ```bash
   # Be more specific with patterns
   ES_INDEXES=logs-2024-*  # Instead of logs-*
   ```

#### High Memory Usage
**Symptom**: Container using too much memory

**Solutions**:
1. Reduce batch size:
   ```bash
   BATCH_SIZE=500  # Default is 1000
   ```

2. Limit Docker container memory:
   ```bash
   docker run --memory="2g" --env-file .env elasticsearch-snowpipe
   ```

3. Increase sync interval to reduce frequency:
   ```bash
   SYNC_INTERVAL=600  # Sync every 10 minutes instead of 5
   ```

### Docker Issues

#### Docker Build Fails
**Symptom**: `ERROR: failed to build`

**Solutions**:
1. Check Docker is running:
   ```bash
   docker ps
   ```

2. Clear Docker cache and rebuild:
   ```bash
   docker build --no-cache -t elasticsearch-snowpipe .
   ```

3. Check requirements.txt dependencies:
   ```bash
   # Test pip install locally
   pip install -r requirements.txt
   ```

#### Container Exits Immediately
**Symptom**: Container stops right after starting

**Solutions**:
1. Check logs:
   ```bash
   docker logs es-snowpipe
   ```

2. Verify environment variables:
   ```bash
   docker run --rm --env-file .env elasticsearch-snowpipe --once
   # Check if config is valid
   ```

3. Test configuration:
   ```bash
   # Run interactively to see errors
   docker run -it --rm --env-file .env elasticsearch-snowpipe --once
   ```

### Authentication Issues

#### SSL Certificate Error
**Symptom**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:
1. Disable certificate verification (testing only):
   ```bash
   ES_VERIFY_CERTS=false
   ```

2. Provide CA certificate:
   ```bash
   ES_CA_CERTS=/path/to/ca.crt
   # Mount in Docker:
   docker run -v /local/path/ca.crt:/certs/ca.crt \
     -e ES_CA_CERTS=/certs/ca.crt \
     --env-file .env elasticsearch-snowpipe
   ```

#### API Key Authentication Fails
**Symptom**: `Authentication failed` with API key

**Solutions**:
1. Verify API key format:
   ```bash
   # Should be base64 encoded id:api_key
   ES_API_KEY=your_base64_encoded_key
   ```

2. Check API key permissions in Elasticsearch:
   ```bash
   curl -H "Authorization: ApiKey your_api_key" \
     https://ES_HOST:9200/_security/_authenticate
   ```

#### Private Key Authentication Fails (Snowflake)
**Symptom**: `Could not load private key`

**Solutions**:
1. Verify key file exists and is readable:
   ```bash
   ls -l /path/to/private_key.p8
   ```

2. Check key format (should be PEM):
   ```bash
   head -1 /path/to/private_key.p8
   # Should show: -----BEGIN ENCRYPTED PRIVATE KEY-----
   ```

3. Verify passphrase (if encrypted):
   ```bash
   SF_PRIVATE_KEY_PASSPHRASE=your_passphrase
   ```

4. Mount key file in Docker:
   ```bash
   docker run -v /local/path/key.p8:/keys/key.p8 \
     -e SF_PRIVATE_KEY_PATH=/keys/key.p8 \
     --env-file .env elasticsearch-snowpipe
   ```

### Table and Schema Issues

#### Table Creation Fails
**Symptom**: `Error creating table`

**Solutions**:
1. Check user permissions:
   ```sql
   GRANT CREATE TABLE ON SCHEMA PUBLIC TO ROLE your_role;
   GRANT USAGE ON SCHEMA PUBLIC TO ROLE your_role;
   ```

2. Verify schema exists:
   ```sql
   SHOW SCHEMAS IN DATABASE ES_DATA;
   CREATE SCHEMA IF NOT EXISTS PUBLIC;
   ```

3. Check table name conflicts:
   ```sql
   SHOW TABLES IN SCHEMA PUBLIC;
   -- Table names are prefixed with SF_TABLE_PREFIX
   ```

#### Merge/Insert Fails
**Symptom**: `Error inserting batch` or `Error merging batch`

**Solutions**:
1. Check for large documents:
   ```bash
   # Reduce batch size for large documents
   BATCH_SIZE=100
   ```

2. Verify VARIANT column can handle data:
   ```sql
   -- Test manually
   SELECT PARSE_JSON('{"test": "data"}');
   ```

3. Check for special characters in data:
   ```sql
   -- Snowflake handles JSON automatically
   -- But verify no encoding issues
   ```

## Debugging Tips

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG
```

### Run in One-Shot Mode
```bash
# Easier to debug
python main.py --once
# or
docker run --rm --env-file .env elasticsearch-snowpipe --once
```

### Test Connections Manually

#### Test Elasticsearch
```python
from elasticsearch import Elasticsearch
es = Elasticsearch(["https://host:9200"], basic_auth=("user", "pass"))
print(es.info())
```

#### Test Snowflake
```python
import snowflake.connector
conn = snowflake.connector.connect(
    account='account',
    user='user',
    password='password',
    database='ES_DATA'
)
print(conn.cursor().execute("SELECT CURRENT_VERSION()").fetchone())
```

### Check Resource Usage
```bash
# Monitor container resources
docker stats es-snowpipe

# Check logs continuously
docker logs -f --tail 100 es-snowpipe
```

## Getting Help

1. Check logs thoroughly:
   ```bash
   docker logs es-snowpipe > logs.txt
   # Review logs.txt for ERROR messages
   ```

2. Enable debug logging:
   ```bash
   LOG_LEVEL=DEBUG
   ```

3. Test with minimal configuration:
   - Start with one index pattern
   - Use small batch size
   - Run in one-shot mode

4. Verify external services:
   - Elasticsearch cluster health
   - Snowflake warehouse status
   - Network connectivity

5. Check GitHub issues: https://github.com/abretz47/elasticsearch-snowpipe/issues
