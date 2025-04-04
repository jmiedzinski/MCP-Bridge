# Config

The config file is a json file that contains all the information needed to run the application.

## Writing a config file

| Section          | Description                                                                                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| inference_server | The inference server configuration. This should point to openai/vllm/ollama etc. Any OpenAI compatible base url should work.                                                   |
| sampling         | Sampling model preferences. You must have at least one sampling model configured, and you can configure the same model with different intelligence, cost, and speed many times |
| mcp_servers      | MCP server connection info/configuration. Each server should use the new structure with a `server` field containing the actual server configuration, plus metadata fields.     |
| network          | uvicorn network configuration. Only used outside of docker environment                                                                                                         |
| logging          | The logging configuration. Set to DEBUG for debug logging                                                                                                                      |

## MCP Servers Configuration

The `mcp_servers` section follows a new structure where each server configuration is split into:

1. `server` - The actual server configuration (command/args, url, or image-based)
2. Metadata fields:
   - `allowed_models` - Optional list of models allowed to use this server
   - `disallowed_models` - Optional list of models not allowed to use this server
   - `disabled` - Optional flag to disable the server (default: false)

### Server Configuration Types

Depending on the server type, you need to provide different configuration inside the `server` field:

1. **StdioServerParameters** (Command-based):
   ```json
   "server": {
     "command": "uvx",
     "args": ["mcp-server-fetch"],
     "env": { "VAR1": "value1" }
   }
   ```

2. **SSEMCPServer** (URL-based):
   ```json
   "server": {
     "url": "http://localhost:8000/mcp-server/sse"
   }
   ```

3. **DockerMCPServer** (Docker image-based):
   ```json
   "server": {
     "image": "example-server:latest"
   }
   ```

### Model and Tool Access Control

You can control which models can use certain MCP servers and which tools are available:

- If neither `allowed_models` nor `disallowed_models` is specified, all models can use the server.
- If `allowed_models` is specified, only listed models can use the server.
- If `disallowed_models` is specified, all models except those listed can use the server.

Similarly for tools:
- If neither `allowed_tools` nor `disallowed_tools` is specified, all tools from the server are available.
- If `allowed_tools` is specified, only listed tools from the server are available.
- If `disallowed_tools` is specified, all tools except those listed are available.

Specifying the same model in both `allowed_models` and `disallowed_models` or the same tool in both `allowed_tools` and `disallowed_tools` will result in a configuration error.

## Example Configuration

Here is an example config.json file with the new structure:

```json
{
    "inference_server": {
        "base_url": "http://localhost:8000/v1",
        "api_key": "None"
    },
    "sampling": {
        "timeout": 10,
        "models": [
            {
                "model": "gpt-4o",
                "intelligence": 0.8,
                "cost": 0.9,
                "speed": 0.3
            },
            {
                "model": "gpt-4o-mini",
                "intelligence": 0.4,
                "cost": 0.1,
                "speed": 0.7
            }
        ]
    },
    "mcp_servers": {
        "fetch": {
            "server": {
                "command": "uvx",
                "args": ["mcp-server-fetch"]
            },
            "allowed_models": ["gpt-4o", "gpt-4o-mini"]
        },
        "search": {
            "server": {
                "url": "http://localhost:8000/mcp-server/sse"
            },
            "allowed_models": ["gpt-4o"]
        },
        "code-review": {
            "server": {
                "command": "uvx",
                "args": ["mcp-server-code-review"]
            },
            "disallowed_models": ["gpt-3.5-turbo"]
        },
        "docker-example-server": {
            "server": {
                "image": "example-server:latest"
            }
        },
        "disabled-server": {
            "server": {
                "command": "uvx",
                "args": ["mcp-server-disabled"]
            },
            "disabled": true
        }
    },
    "network": {
        "host": "0.0.0.0",
        "port": 9090
    },
    "logging": {
        "log_level": "DEBUG"
    }
}
```

## Loading a config file

### Docker

When using docker you will need to add a reference to the config.json file in the `compose.yml` file. Pick any of:

- Add the `config.json` file to the same directory as the compose.yml file and use a volume mount (you will need to add the volume manually)
  ```bash
  environment:
    - MCP_BRIDGE__CONFIG__FILE=config.json # mount the config file for this to work
  ```
  
  The mount point for using the config file would look like:
  ```yaml
    volumes:
      - ./config.json:/mcp_bridge/config.json
  ```

- Add a http url to the environment variables to download the config.json file from a url
  ```bash
  environment:
    - MCP_BRIDGE__CONFIG__HTTP_URL=http://10.88.100.170:8888/config.json
  ```

- Add the config json directly as an environment variable
  ```bash
  environment:
    - MCP_BRIDGE__CONFIG__JSON={"inference_server":{"base_url":"http://example.com/v1","api_key":"None"},"mcp_servers":{"fetch":{"server":{"command":"uvx","args":["mcp-server-fetch"]}}}}
  ```

### Non Docker

For non-docker, the system will look for a `config.json` file in the current directory. This means that there is no special configuration needed. You can still use the advanced loading mechanisms if you want to, but you will need to modify the environment variables for your system as in the docker section.

## Migrating from the Old Configuration Format

If you're using the old format:

```json
"mcp_servers": {
    "fetch": {
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "allowed_models": ["gpt-4o", "gpt-4o-mini"]
    }
}
```

You need to move the server configuration into a nested `server` object:

```json
"mcp_servers": {
    "fetch": {
        "server": {
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "allowed_models": ["gpt-4o", "gpt-4o-mini"]
    }
}
```

The metadata fields (`allowed_models`, `disallowed_models`, and `disabled`) remain at the server configuration level, not inside the `server` object.