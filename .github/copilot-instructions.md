# Copilot Instructions for QStash Pipeline Automation

## Core Principles

- **Follow design.md strictly** - All implementations must adhere to the architecture, interfaces, and specifications defined in `.kiro/specs/qstash-pipeline-automation/design.md`
- **Never hard-code secrets** - Read all sensitive values from environment variables as defined in the `.env` file
- **Use filenames and folders exactly as in tasks.md** - Follow the precise file structure and naming conventions specified in the implementation plan

## Implementation Guidelines

### Security Requirements
- All API keys, tokens, and secrets MUST be read from environment variables
- Never commit secrets to version control
- Use `.env` file for local development (git-ignored)
- Validate environment variables at service startup

### Architecture Compliance
- Follow the microservices pattern with Docker containers
- Use the exact service interfaces defined in design.md
- Implement proper error handling and fallback mechanisms
- Maintain service isolation through Docker networking

### Code Quality Standards
- Use async/await patterns for non-blocking operations
- Implement comprehensive error handling with proper logging
- Follow Python typing conventions with msgspec for data validation
- Write tests for all critical functionality

### Service-Specific Requirements
- **Edge Worker**: Use Cloudflare Workers KV API exactly as documented
- **Crawler**: Use httpx.AsyncClient with QStash delay headers
- **Parser**: Output Arrow IPC format with size constraints (<1MB)
- **Orchestrator**: Verify JWT signatures using PyJWT with EdDSA
- **Validator**: Implement GPU detection with CPU fallback using cupy.cuda.runtime

### Testing Requirements
- Use FastAPI TestClient for API testing
- Mock external services (httpx, QStash) in unit tests
- Skip GPU tests when hardware is unavailable
- Maintain test coverage for all critical paths