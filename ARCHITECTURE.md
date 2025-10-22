# Elasticsearch-Snowpipe Architecture

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Elasticsearch Cluster                         │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  logs-*     │  │ metrics-*   │  │  events-*   │             │
│  │  index      │  │  index      │  │  index      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Scroll API
                            │ (Batch: 1000 docs)
                            ↓
                ┌───────────────────────┐
                │   ES-Snowpipe App     │
                │   (Docker Container)  │
                │                       │
                │  ┌─────────────────┐  │
                │  │ Config Manager  │  │
                │  └─────────────────┘  │
                │  ┌─────────────────┐  │
                │  │   ES Client     │  │
                │  └─────────────────┘  │
                │  ┌─────────────────┐  │
                │  │  SF Client      │  │
                │  └─────────────────┘  │
                └───────────┬───────────┘
                            │
                            │ MERGE (Upsert)
                            │ (Batch: 1000 rows)
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                      Snowflake Account                         │
│                                                                 │
│  Database: ES_DATA                                             │
│  Schema: PUBLIC                                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ es_logs_*                                             │     │
│  │ ┌────────────┬──────────────┬──────────┬──────────┐ │     │
│  │ │ id (PK)    │ index_name   │ document │ ingested │ │     │
│  │ │ VARCHAR    │ VARCHAR      │ VARIANT  │ at       │ │     │
│  │ └────────────┴──────────────┴──────────┴──────────┘ │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ es_metrics_*                                          │     │
│  │ ┌────────────┬──────────────┬──────────┬──────────┐ │     │
│  │ │ id (PK)    │ index_name   │ document │ ingested │ │     │
│  │ │ VARCHAR    │ VARCHAR      │ VARIANT  │ at       │ │     │
│  │ └────────────┴──────────────┴──────────┴──────────┘ │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ es_events_*                                           │     │
│  │ ┌────────────┬──────────────┬──────────┬──────────┐ │     │
│  │ │ id (PK)    │ index_name   │ document │ ingested │ │     │
│  │ │ VARCHAR    │ VARCHAR      │ VARIANT  │ at       │ │     │
│  │ └────────────┴──────────────┴──────────┴──────────┘ │     │
│  └──────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
```

## Configuration Flow

```
┌─────────────────────┐       ┌──────────────────────┐
│  .env file          │       │  config.yml          │
│                     │       │                      │
│  ES_HOST=...        │  OR   │  elasticsearch:      │
│  ES_INDEXES=...     │       │    host: ...         │
│  SF_ACCOUNT=...     │       │  snowflake:          │
│  SF_DATABASE=...    │       │    account: ...      │
└──────────┬──────────┘       └──────────┬───────────┘
           │                              │
           └──────────────┬───────────────┘
                          ↓
                  ┌───────────────┐
                  │ Config Loader │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │   AppConfig   │
                  └───────────────┘
```

## Sync Process

```
1. Connect to Elasticsearch
   └─→ Validate credentials
   └─→ Test connection

2. Connect to Snowflake
   └─→ Validate credentials
   └─→ Test connection

3. Discover Indexes
   └─→ Get matching patterns
   └─→ Filter system indexes

4. For Each Index:
   ├─→ Get mapping
   ├─→ Create/verify table
   ├─→ Count documents
   ├─→ Scroll documents
   │   ├─→ Fetch batch (1000)
   │   ├─→ Transform to records
   │   ├─→ MERGE into Snowflake
   │   └─→ Repeat until done
   └─→ Log completion

5. Wait for next cycle (300s)
   └─→ Repeat from step 3
```

## Component Responsibilities

### elasticsearch_client.py
- Connect to Elasticsearch cluster
- Search and scroll indexes
- Handle authentication (basic auth, API key)
- Batch document retrieval

### snowflake_client.py
- Connect to Snowflake
- Create tables with schema
- Batch insert/merge operations
- Handle authentication (password, private key)

### config.py
- Load from environment variables
- Load from YAML files
- Validate configuration
- Provide defaults

### main.py
- CLI argument parsing
- Application lifecycle
- Sync orchestration
- Error handling & logging
