# elasticsearch-snowpipe

A Python application that streams data from Elasticsearch indexes to Snowflake using Snowpipe streaming. The application is containerized with Docker and supports configurable index patterns and connection settings.

## Features

- **Configurable Elasticsearch Connection**: Connect to any Elasticsearch server with support for:
  - Basic authentication (username/password)
  - API key authentication
  - SSL/TLS with certificate verification
  - Custom index patterns

- **Snowflake Streaming**: Efficiently stream data to Snowflake with:
  - Automatic table creation
  - Upsert functionality (merge on document ID)
  - Batch processing for optimal performance
  - Support for password or private key authentication

- **Flexible Configuration**: Configure via:
  - Environment variables
  - YAML configuration file
  - Both methods can be combined

- **Docker Support**: Fully containerized application for easy deployment

- **Continuous or One-time Sync**: Run as a daemon for continuous syncing or execute once

## Quick Start

### Using Docker

1. Build the Docker image:
```bash
docker build -t elasticsearch-snowpipe .
```

2. Run with environment variables:
```bash
docker run --env-file .env elasticsearch-snowpipe
```

3. Or run with a config file:
```bash
docker run -v $(pwd)/config.yml:/config/config.yml elasticsearch-snowpipe --config /config/config.yml
```

### Local Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the application (see Configuration section)

3. Run the application:
```bash
# Continuous mode
python main.py

# One-time sync
python main.py --once

# With config file
python main.py --config config.yml
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Elasticsearch Configuration
ES_HOST=localhost
ES_PORT=9200
ES_USERNAME=elastic
ES_PASSWORD=changeme
ES_USE_SSL=true
ES_VERIFY_CERTS=true
ES_INDEXES=logs-*,metrics-*  # Comma-separated patterns

# Snowflake Configuration
SF_ACCOUNT=your_account.region
SF_USER=your_username
SF_PASSWORD=your_password
SF_DATABASE=ES_DATA
SF_SCHEMA=PUBLIC
SF_WAREHOUSE=COMPUTE_WH
SF_TABLE_PREFIX=es_

# Application Configuration
BATCH_SIZE=1000
SYNC_INTERVAL=300  # seconds
LOG_LEVEL=INFO
```

### YAML Configuration

Copy `config.example.yml` to `config.yml` and configure:

```yaml
elasticsearch:
  host: localhost
  port: 9200
  username: elastic
  password: changeme
  use_ssl: true
  verify_certs: true
  indexes:
    - logs-*
    - metrics-*

snowflake:
  account: your_account.region
  user: your_username
  password: your_password
  database: ES_DATA
  schema: PUBLIC
  warehouse: COMPUTE_WH
  table_prefix: es_

batch_size: 1000
sync_interval: 300
log_level: INFO
```

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t elasticsearch-snowpipe .

# Run in continuous mode with environment variables
docker run -d --name es-snowpipe --env-file .env elasticsearch-snowpipe

# Run once with config file
docker run --rm -v $(pwd)/config.yml:/config/config.yml elasticsearch-snowpipe --config /config/config.yml --once

# View logs
docker logs -f es-snowpipe
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  elasticsearch-snowpipe:
    build: .
    environment:
      - ES_HOST=elasticsearch
      - ES_PORT=9200
      - ES_USERNAME=elastic
      - ES_PASSWORD=changeme
      - ES_INDEXES=logs-*,metrics-*
      - SF_ACCOUNT=your_account
      - SF_USER=your_user
      - SF_PASSWORD=your_password
      - SF_DATABASE=ES_DATA
      - SYNC_INTERVAL=300
    restart: unless-stopped
```

## How It Works

1. **Connection**: The application connects to both Elasticsearch and Snowflake
2. **Index Discovery**: Finds all indexes matching the configured patterns
3. **Table Creation**: Creates corresponding tables in Snowflake (if they don't exist)
4. **Data Streaming**: 
   - Scrolls through Elasticsearch documents in batches
   - Transforms documents to JSON format
   - Merges data into Snowflake tables (upsert by document ID)
5. **Continuous Sync**: Repeats the process at the configured interval

## Table Schema

Each Elasticsearch index is mapped to a Snowflake table with the following schema:

```sql
CREATE TABLE es_<index_name> (
    id VARCHAR(256) PRIMARY KEY,      -- Elasticsearch document _id
    index_name VARCHAR(256),           -- Original index name
    document VARIANT,                  -- Full document as JSON
    ingested_at TIMESTAMP_NTZ         -- Timestamp of ingestion
)
```

## Authentication Options

### Elasticsearch

- **Basic Auth**: Set `ES_USERNAME` and `ES_PASSWORD`
- **API Key**: Set `ES_API_KEY` (preferred for production)
- **SSL/TLS**: Configure `ES_USE_SSL`, `ES_VERIFY_CERTS`, and optionally `ES_CA_CERTS`

### Snowflake

- **Password**: Set `SF_PASSWORD`
- **Private Key**: Set `SF_PRIVATE_KEY_PATH` and optionally `SF_PRIVATE_KEY_PASSPHRASE` (recommended for production)

## Command Line Options

```bash
usage: main.py [-h] [--config CONFIG] [--once] [--env-file ENV_FILE]

Stream Elasticsearch indexes to Snowflake using Snowpipe

optional arguments:
  -h, --help           show this help message and exit
  --config CONFIG      Path to configuration file (YAML)
  --once               Run once and exit (default is continuous mode)
  --env-file ENV_FILE  Path to .env file
```

## Index Patterns

The application supports Elasticsearch wildcard patterns:

- `*` - Match all indexes (excluding system indexes starting with `.`)
- `logs-*` - Match all indexes starting with "logs-"
- `metrics-*,events-*` - Match multiple patterns (comma-separated)

## Performance Tuning

- **BATCH_SIZE**: Number of documents to fetch and insert per batch (default: 1000)
  - Increase for better throughput with large documents
  - Decrease if hitting memory limits

- **SYNC_INTERVAL**: Seconds between sync cycles (default: 300)
  - Adjust based on data freshness requirements
  - Lower values increase load on both systems

## Monitoring

The application logs key metrics:
- Number of indexes found
- Document counts per index
- Progress during sync
- Errors and warnings

Monitor logs to track sync progress:
```bash
docker logs -f es-snowpipe
```

## Security Considerations

1. **Never commit credentials**: Use environment variables or mounted config files
2. **Use API keys/private keys**: Preferred over passwords for production
3. **Enable SSL/TLS**: Always use encrypted connections
4. **Verify certificates**: Set `ES_VERIFY_CERTS=true` and provide CA certs if needed
5. **Least privilege**: Use Snowflake users with minimal required permissions

## Troubleshooting

### Connection Issues
- Verify network connectivity to Elasticsearch and Snowflake
- Check credentials and authentication method
- Ensure SSL/TLS settings are correct

### Performance Issues
- Adjust `BATCH_SIZE` based on document size
- Monitor Snowflake warehouse size
- Check Elasticsearch cluster health

### Data Issues
- Verify index patterns match intended indexes
- Check table permissions in Snowflake
- Review logs for specific error messages

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

