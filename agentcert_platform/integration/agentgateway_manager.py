"""
AgentGateway Manager - Manages agentgateway configuration and lifecycle
"""

import os
import yaml
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class AgentGatewayManager:
    """Manages agentgateway configuration and lifecycle"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AgentGatewayManager.
        
        Args:
            config_path: Path to agentgateway config file. Defaults to config/agentgateway.yaml
        """
        self.base_path = Path(__file__).parent.parent.parent
        self.config_path = Path(config_path) if config_path else self.base_path / "config" / "agentgateway.yaml"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.gateway_process: Optional[subprocess.Popen] = None
        self.a2a_base_url = "http://localhost:3000"
        self.openai_proxy_url = "http://localhost:3001/v1"
        self.admin_ui_url = "http://localhost:15000"
        
    def _load_config(self) -> Dict[str, Any]:
        """Load agentgateway config from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load agentgateway config: {e}")
                return {}
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default agentgateway configuration"""
        return {
            "config": {
                "tracing": {
                    "otlpEndpoint": "http://localhost:4317",
                    "randomSampling": True
                }
            },
            "binds": [
                {
                    "port": 3000,
                    "listeners": [{
                        "routes": [{
                            "matches": [
                                {"path": {"pathPrefix": "/agents/"}}
                            ],
                            "policies": {
                                "cors": {
                                    "allowOrigins": ["*"],
                                    "allowHeaders": ["content-type", "cache-control", "mcp-protocol-version"]
                                }
                            },
                            "backends": []
                        }]
                    }]
                },
                {
                    "port": 3001,
                    "listeners": [{
                        "routes": [{
                            "backends": [{
                                "ai": {
                                    "name": "openai",
                                    "provider": {
                                        "openAI": {}
                                    },
                                    "routes": {
                                        "/v1/chat/completions": "completions",
                                        "/v1/models": "passthrough",
                                        "*": "passthrough"
                                    }
                                }
                            }]
                        }]
                    }]
                }
            ]
        }
    
    def _save_config(self, config: Dict[str, Any]):
        """Save agentgateway config to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved agentgateway config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save agentgateway config: {e}")
            raise
    
    async def register_agent(
        self,
        agent_id: str,
        agent_url: str,
        api_key: Optional[str] = None
    ) -> bool:
        """
        Register an agent with agentgateway for A2A routing.
        
        Args:
            agent_id: Agent ID
            agent_url: Direct agent URL (e.g., http://localhost:6000/a2a)
            api_key: Optional OpenAI API key for this agent
        
        Returns:
            True if successful
        """
        logger.info(f"Registering agent {agent_id} with agentgateway")
        
        config = self._load_config()
        
        # Find the A2A route (port 3000)
        service_backend = None
        for bind in config.get("binds", []):
            if bind.get("port") == 3000:
                for listener in bind.get("listeners", []):
                    for route in listener.get("routes", []):
                        # Port 3000 route doesn't have matches, it's the default route
                        backends = route.setdefault("backends", [])
                        # Find or create service backend
                        # Extract port from agent_url (e.g., http://localhost:6000 -> 6000)
                        import re
                        port_match = re.search(r':(\d+)', agent_url)
                        agent_port = port_match.group(1) if port_match else "6000"
                        
                        # Check if service backend already exists for this port
                        for backend in backends:
                            if "service" in backend:
                                svc = backend["service"]
                                if svc.get("port") == int(agent_port) and svc.get("name") == "default/localhost":
                                    service_backend = svc
                                    break
                        
                        if not service_backend:
                            # Create new service backend
                            service_backend = {
                                "name": "default/localhost",
                                "port": int(agent_port)
                            }
                            backends.append({"service": service_backend})
                        break
        
        if not service_backend:
            logger.error("Could not find or create service backend in agentgateway config")
            return False
        
        self._save_config(config)
        
        # Reload agentgateway if running
        await self._reload_agentgateway()
        
        logger.info(f"✅ Registered agent {agent_id} with agentgateway")
        return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from agentgateway"""
        logger.info(f"Unregistering agent {agent_id} from agentgateway")
        
        config = self._load_config()
        
        # Find and remove the agent from A2A backend
        for bind in config.get("binds", []):
            if bind.get("port") == 3000:
                for listener in bind.get("listeners", []):
                    for route in listener.get("routes", []):
                        for backend in route.get("backends", []):
                            if "a2a" in backend:
                                targets = backend["a2a"].get("targets", [])
                                backend["a2a"]["targets"] = [
                                    t for t in targets if t.get("name") != agent_id
                                ]
                                break
        
        self._save_config(config)
        await self._reload_agentgateway()
        
        logger.info(f"✅ Unregistered agent {agent_id} from agentgateway")
        return True
    
    def get_agentgateway_a2a_url(self, agent_id: str) -> str:
        """Get agentgateway A2A proxy URL for an agent"""
        return f"{self.a2a_base_url}/agents/{agent_id}/a2a"
    
    def get_openai_proxy_url(self) -> str:
        """Get agentgateway OpenAI proxy URL"""
        return self.openai_proxy_url
    
    async def start_agentgateway(self) -> bool:
        """Start agentgateway process"""
        if self.gateway_process and self.gateway_process.poll() is None:
            logger.info("agentgateway is already running")
            return True
        
        # Check if agentgateway binary exists
        agentgateway_bin = self._find_agentgateway_binary()
        if not agentgateway_bin:
            logger.warning("agentgateway binary not found. Please install it first.")
            logger.warning("Install with: curl https://raw.githubusercontent.com/agentgateway/agentgateway/refs/heads/main/common/scripts/get-agentgateway | bash")
            return False
        
        logger.info(f"Starting agentgateway with config: {self.config_path}")
        
        try:
            self.gateway_process = subprocess.Popen(
                [agentgateway_bin, "-f", str(self.config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to see if it starts successfully
            await asyncio.sleep(2)
            
            if self.gateway_process.poll() is not None:
                # Process died
                stdout, stderr = self.gateway_process.communicate()
                logger.error(f"agentgateway failed to start: {stderr}")
                return False
            
            logger.info(f"✅ agentgateway started (PID: {self.gateway_process.pid})")
            logger.info(f"   A2A Proxy: {self.a2a_base_url}")
            logger.info(f"   OpenAI Proxy: {self.openai_proxy_url}")
            logger.info(f"   Admin UI: {self.admin_ui_url}/ui")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agentgateway: {e}")
            return False
    
    async def stop_agentgateway(self):
        """Stop agentgateway process"""
        if self.gateway_process:
            try:
                self.gateway_process.terminate()
                await asyncio.sleep(1)
                if self.gateway_process.poll() is None:
                    self.gateway_process.kill()
                self.gateway_process = None
                logger.info("✅ agentgateway stopped")
            except Exception as e:
                logger.error(f"Error stopping agentgateway: {e}")
    
    def _find_agentgateway_binary(self) -> Optional[str]:
        """Find agentgateway binary in PATH"""
        import shutil
        return shutil.which("agentgateway")
    
    async def _reload_agentgateway(self):
        """Reload agentgateway configuration (if supported)"""
        # agentgateway supports hot-reload via SIGHUP or API
        # For now, we'll just log that config was updated
        # In production, you might want to send SIGHUP or use admin API
        if self.gateway_process and self.gateway_process.poll() is None:
            logger.info("agentgateway config updated. Restart may be needed for changes to take effect.")
            # TODO: Implement hot-reload via SIGHUP or admin API

