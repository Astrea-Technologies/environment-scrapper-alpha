# Political Social Media Analysis Platform - Backend

## Hybrid Database Architecture

This application implements a hybrid database architecture to address diverse data requirements of social media analysis:

| Component | Technology | Purpose | Status in MVP |
|-----|---|---|---|
| Relational Database | PostgreSQL | Entity data and relationships | Active |
| Document Database | MongoDB | Social media content and engagement | Active |
| In-memory Database | Redis | Caching and real-time operations | Prepared but Inactive |
| Vector Database | Pinecone | Semantic similarity analysis | Active |

## MongoDB Component

The MongoDB component stores social media content and engagement data. Its implementation includes:

- **Collections**:
  - `posts`: Social media posts from tracked accounts
  - `comments`: User comments on tracked posts

- **Schema Structure**:
  - Pydantic models with nested subschemas
  - Cross-references to PostgreSQL entities
  - Flexible content and engagement tracking

## Redis Component

The Redis component is prepared but inactive in the MVP. Its implementation includes:

- **Key Pattern Constants**:
  - Standardized naming conventions with namespaces
  - Structured patterns for different data types

- **Data Structures**:
  - Hash maps for entity metrics
  - Sorted sets for trending topics
  - Lists for activity streams
  - Pub/Sub for real-time alerts

- **Feature Flag**:
  - `USE_REDIS` flag in settings (default: False)
  - Mock Redis client for graceful fallback

## Post-MVP Redis Implementation Plan

The Redis functionality will be activated incrementally after the MVP:

1. **Phase 1**: 
   - Enable entity metrics caching
   - Implement basic alerts

2. **Phase 2**:
   - Add trending topics functionality
   - Implement activity streams

3. **Phase 3**:
   - Full pub/sub implementation
   - Advanced caching strategies

## How to Enable Redis

To enable Redis for development or production:

1. Set `USE_REDIS=true` in your environment or .env file
2. Ensure Redis server is running and accessible
3. Verify Redis connection in logs during startup

## Performance Considerations

The MVP handles data access without Redis through:

- Optimized MongoDB queries with proper indexing
- Application-level caching where critical
- Scheduled batch processing instead of real-time
- Limited polling instead of push notifications

When performance metrics indicate a need (high latency, large data volumes), 
Redis features can be enabled incrementally. 