from typing import Union, Optional, List
from loguru import logger
from mcp import McpError, StdioServerParameters
from mcpx.client.transports.docker import DockerMCPServer
from mcp_bridge.config import config
from mcp_bridge.config.final import SSEMCPServer
from .DockerClient import DockerClient
from .SseClient import SseClient
from .StdioClient import StdioClient

client_types = Union[StdioClient, SseClient, DockerClient]

class MCPClientManager:
    clients: dict[str, client_types] = {}

    async def initialize(self):
        logger.log("DEBUG", "Initializing MCP Client Manager")
        for server_name, server_config in config.mcp_servers.items():
            self.clients[server_name] = await self.construct_client(
                server_name, server_config
            )

    async def construct_client(self, name, server_config) -> client_types:
        logger.log("DEBUG", f"Constructing client for {server_config}")
        if isinstance(server_config, StdioServerParameters):
            client = StdioClient(name, server_config)
            await client.start()
            return client
        if isinstance(server_config, SSEMCPServer):
            client = SseClient(name, server_config)
            await client.start()
            return client
        if isinstance(server_config, DockerMCPServer):
            client = DockerClient(name, server_config)
            await client.start()
            return client
        raise NotImplementedError("Client Type not supported")

    def get_client(self, server_name: str):
        return self.clients[server_name]

    def get_clients(self, model_name: Optional[str] = None):
        if model_name is None:
            return list(self.clients.items())
            
        filtered_clients = []
        for name, client in self.clients.items():
            server_config = config.mcp_servers.get(name, {})
            allowed_models = server_config.get("allowed_models")
            disallowed_models = server_config.get("disallowed_models")
            
            # Check for model conflict - same model in both allowed and disallowed lists
            if (allowed_models is not None and disallowed_models is not None and 
                model_name in allowed_models and model_name in disallowed_models):
                logger.error(f"Configuration error for server '{name}': Model '{model_name}' appears in both allowed_models and disallowed_models")
                continue
                
            # Apply filtering based on allowed_models and disallowed_models
            if ((allowed_models is None or model_name in allowed_models) and 
                (disallowed_models is None or model_name not in disallowed_models)):
                filtered_clients.append((name, client))
                
        return filtered_clients

    async def get_client_from_tool(self, tool: str, model_name: Optional[str] = None):
        for name, client in self.get_clients(model_name):
            if not client.session:
                continue
            try:
                list_tools = await client.session.list_tools()
                for client_tool in list_tools.tools:
                    if client_tool.name == tool:
                        return client
            except McpError:
                continue

    async def get_client_from_prompt(self, prompt: str, model_name: Optional[str] = None):
        for name, client in self.get_clients(model_name):
            if not client.session:
                continue
            try:
                list_prompts = await client.session.list_prompts()
                for client_prompt in list_prompts.prompts:
                    if client_prompt.name == prompt:
                        return client
            except McpError:
                continue

ClientManager = MCPClientManager()