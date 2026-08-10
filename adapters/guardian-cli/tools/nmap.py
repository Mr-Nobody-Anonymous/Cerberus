"""
Nmap tool wrapper for port scanning and service detection
"""

import re
import json
from typing import Dict, Any, List

from tools.base_tool import BaseTool


class NmapTool(BaseTool):
    """Nmap port scanner wrapper"""
    
    def get_command(self, target: str, **kwargs) -> List[str]:
        """Build nmap command"""
        # Get config defaults
        config = self.config.get("tools", {}).get("nmap", {})
        
        # Workflow parameters override config
        # Priority: kwargs (workflow) > config > hardcoded defaults
        
        # Base command
        command = ["nmap"]
        
        # Default args - workflow parameter or config or default
        default_args = kwargs.get("default_args", config.get("default_args", "-sV -sC"))
        if default_args:
            command.extend(default_args.split())
        
        # Timing template - workflow parameter or config or default
        timing = kwargs.get("timing", config.get("timing", "T4"))
        command.append(f"-{timing}")
        
        # XML output for parsing
        command.extend(["-oX", "-"])
        
        # Ports - workflow parameter overrides
        if "ports" in kwargs:
            command.extend(["-p", kwargs["ports"]])
        elif "ports" in config:
            command.extend(["-p", config["ports"]])
        
        # Scan type - workflow parameter overrides
        if "scan_type" in kwargs:
            command.append(kwargs["scan_type"])
        elif "scan_type" in config:
            command.append(config["scan_type"])
        
        # Target
        command.append(target)
        
        return command
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse nmap XML output"""
        results = {
            "open_ports": [],
            "services": [],
            "os_detection": None,
            "vulnerabilities": []
        }
        
        # Simple regex parsing (in production, use proper XML parser)
        # Extract open ports
        port_pattern = r'portid="(\d+)".*?service name="([^"]*)".*?product="([^"]*)"'
        for match in re.finditer(port_pattern, output, re.DOTALL):
            port = match.group(1)
            service = match.group(2)
            product = match.group(3) if match.group(3) else "unknown"
            
            results["open_ports"].append(int(port))
            results["services"].append({
                "port": int(port),
                "service": service,
                "product": product
            })
        
        # Extract OS if available
        os_match = re.search(r'osclass type="([^"]*)".*?osfamily="([^"]*)"', output)
        if os_match:
            results["os_detection"] = {
                "type": os_match.group(1),
                "family": os_match.group(2)
            }
        
        return results
