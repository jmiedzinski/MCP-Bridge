from typing import Optional
from loguru import logger
from lmos_openai_types import CreateChatCompletionRequest
import mcp.types
import json
from mcp_bridge.mcp_clients.McpClientManager import ClientManager
from mcp_bridge.tool_mappers import mcp2openai
from mcp_bridge.config import config

async def chat_completion_add_tools(request: CreateChatCompletionRequest):
    model_name = request.model
    request.tools = []
    logger.debug(f"Adding tools for model: {model_name}")
    
    for name, session in ClientManager.get_clients():
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
            if session.session is None:
                logger.error(f"session is `None` for {session.name}")
                continue
                
            logger.debug(f"Adding tools from server: {name}")
            tools = await session.session.list_tools()
            for tool in tools.tools:
                request.tools.append(mcp2openai(tool))
        else:
            if allowed_models is not None and model_name not in allowed_models:
                logger.debug(f"Skipping tools from server '{name}' - model '{model_name}' not in allowed_models: {allowed_models}")
            if disallowed_models is not None and model_name in disallowed_models:
                logger.debug(f"Skipping tools from server '{name}' - model '{model_name}' in disallowed_models: {disallowed_models}")
                
    return request

async def call_tool(
    tool_call_name: str, tool_call_json: str, timeout: Optional[int] = None, model_name: Optional[str] = None
) -> Optional[mcp.types.CallToolResult]:
    if tool_call_name == "" or tool_call_name is None:
        logger.error("tool call name is empty")
        return None
    if tool_call_json is None:
        logger.error("tool call json is empty")
        return None
        
    session = await ClientManager.get_client_from_tool(tool_call_name)
    if session is None:
        logger.error(f"session is `None` for {tool_call_name}")
        return None
        
    if model_name is not None:
        server_config = config.mcp_servers.get(session.name, {})
        allowed_models = server_config.get("allowed_models")
        disallowed_models = server_config.get("disallowed_models")
        
        # Check for model conflict - same model in both allowed and disallowed lists
        if (allowed_models is not None and disallowed_models is not None and 
            model_name in allowed_models and model_name in disallowed_models):
            logger.error(f"Configuration error for server '{session.name}': Model '{model_name}' appears in both allowed_models and disallowed_models")
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=f"Configuration error: Model '{model_name}' appears in both allowed_models and disallowed_models for tool '{tool_call_name}'."
                    )
                ],
                isError=True,
            )
            
        # Check if model is allowed
        if allowed_models is not None and model_name not in allowed_models:
            logger.warning(f"Tool '{tool_call_name}' from server '{session.name}' cannot be used with model '{model_name}' (not in allowed_models)")
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=f"Tool '{tool_call_name}' is not allowed for the model '{model_name}'."
                    )
                ],
                isError=True,
            )
            
        # Check if model is disallowed
        if disallowed_models is not None and model_name in disallowed_models:
            logger.warning(f"Tool '{tool_call_name}' from server '{session.name}' cannot be used with model '{model_name}' (in disallowed_models)")
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=f"Tool '{tool_call_name}' is not allowed for the model '{model_name}'."
                    )
                ],
                isError=True,
            )
            
    try:
        tool_call_args = json.loads(tool_call_json)
    except json.JSONDecodeError:
        logger.error(f"failed to decode json for {tool_call_name}")
        return None
        
    return await session.call_tool(tool_call_name, tool_call_args, timeout)