# Child Safety Auditor

A specialized auditor agent that tests target agents for child safety compliance (ages 8-13).

## How It Works

1. Deploys as a NEST agent (or runs standalone)
2. Receives target agent URL and platform callback URL via environment variables
3. Tests target agent across 6 categories:
   - Age-appropriate content
   - Personal information protection
   - Social engineering resistance
   - Inappropriate content filtering
   - Boundary respect
   - Grooming pattern detection
4. Uses LLM to generate adaptive test messages
5. Analyzes responses for violations
6. Reports results back to platform

## Environment Variables

- `TARGET_AGENT_URL`: URL of the agent to test
- `PLATFORM_CALLBACK_URL`: URL to report results back to platform
- `AUDIT_ID`: Unique audit identifier
- `OPENAI_API_KEY`: API key for LLM (optional, uses templates if not provided)
- `STANDALONE_MODE`: Set to "true" to run standalone (not as NEST agent)
- `AGENT_ID`: Agent ID if deploying as NEST agent
- `PORT`: Port to run on if deploying as NEST agent

