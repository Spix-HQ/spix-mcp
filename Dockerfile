FROM python:3.12-slim

WORKDIR /app

# Install spix-mcp from PyPI
RUN pip install --no-cache-dir spix-mcp

# The server reads SPIX_API_KEY from environment
ENV SPIX_API_KEY=""

# Run the MCP server over stdio
ENTRYPOINT ["spix-mcp"]

