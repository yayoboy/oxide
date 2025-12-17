"""
Configuration loading and validation for Oxide.
"""
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from pydantic import BaseModel, Field, field_validator

from ..utils.exceptions import ConfigError


class ServiceType(str, Enum):
    """Type of service adapter."""
    CLI = "cli"
    HTTP = "http"


class APIType(str, Enum):
    """API type for HTTP services."""
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class ServiceConfig(BaseModel):
    """Configuration for a single LLM service."""
    type: ServiceType
    enabled: bool = True

    # CLI-specific fields
    executable: Optional[str] = None

    # HTTP-specific fields
    base_url: Optional[str] = None
    api_type: Optional[APIType] = None
    default_model: Optional[str] = None

    # Common fields
    max_context_tokens: Optional[int] = None
    models: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None

    @field_validator("executable")
    @classmethod
    def validate_cli_executable(cls, v, info):
        """Validate that CLI services have executable defined."""
        if info.data.get("type") == ServiceType.CLI and not v:
            raise ValueError("CLI services must specify 'executable'")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_http_base_url(cls, v, info):
        """Validate that HTTP services have base_url defined."""
        if info.data.get("type") == ServiceType.HTTP and not v:
            raise ValueError("HTTP services must specify 'base_url'")
        return v


class RoutingRuleConfig(BaseModel):
    """Routing rules for a specific task type."""
    primary: str
    fallback: List[str] = Field(default_factory=list)
    parallel_threshold_files: Optional[int] = None
    timeout_seconds: Optional[int] = None


class ExecutionConfig(BaseModel):
    """Execution settings."""
    max_parallel_workers: int = 3
    timeout_seconds: int = 120
    streaming: bool = True
    retry_on_failure: bool = True
    max_retries: int = 2


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: Optional[str] = None
    console: bool = True


class Config(BaseModel):
    """Main configuration object."""
    services: Dict[str, ServiceConfig]
    routing_rules: Dict[str, RoutingRuleConfig]
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("services")
    @classmethod
    def validate_services(cls, v):
        """Validate that at least one service is enabled."""
        if not any(service.enabled for service in v.values()):
            raise ValueError("At least one service must be enabled")
        return v

    @field_validator("routing_rules")
    @classmethod
    def validate_routing_rules(cls, v, info):
        """Validate that routing rules reference valid services."""
        services = info.data.get("services", {})
        service_names = set(services.keys())

        for task_type, rule in v.items():
            # Check primary service exists
            if rule.primary not in service_names:
                raise ValueError(
                    f"Routing rule for '{task_type}' references unknown primary service: {rule.primary}"
                )

            # Check fallback services exist
            for fallback in rule.fallback:
                if fallback not in service_names:
                    raise ValueError(
                        f"Routing rule for '{task_type}' references unknown fallback service: {fallback}"
                    )

        return v

    def get_enabled_services(self) -> List[str]:
        """Get list of enabled service names."""
        return [name for name, config in self.services.items() if config.enabled]

    def get_service_config(self, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service."""
        if service_name not in self.services:
            raise ConfigError(f"Unknown service: {service_name}")
        return self.services[service_name]

    def get_routing_rule(self, task_type: str) -> Optional[RoutingRuleConfig]:
        """Get routing rule for a specific task type."""
        return self.routing_rules.get(task_type)


class ModelCapability(BaseModel):
    """Model capability profile."""
    name: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    optimal_for: List[str] = Field(default_factory=list)


class ModelProfiles(BaseModel):
    """Model capability profiles."""
    model_profiles: Dict[str, ModelCapability]


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        ConfigError: If file doesn't exist or is invalid
    """
    if not file_path.exists():
        raise ConfigError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {file_path}: {e}")
    except Exception as e:
        raise ConfigError(f"Error reading {file_path}: {e}")


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load Oxide configuration from YAML file.

    Args:
        config_path: Path to config file (default: config/default.yaml)

    Returns:
        Validated Config object

    Raises:
        ConfigError: If configuration is invalid
    """
    if config_path is None:
        # Default to config/default.yaml relative to project root
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"

    data = load_yaml_file(config_path)

    try:
        config = Config(**data)
        return config
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}")


def load_model_profiles(profiles_path: Optional[Path] = None) -> ModelProfiles:
    """
    Load model capability profiles from YAML file.

    Args:
        profiles_path: Path to profiles file (default: config/models.yaml)

    Returns:
        ModelProfiles object

    Raises:
        ConfigError: If profiles file is invalid
    """
    if profiles_path is None:
        profiles_path = Path(__file__).parent.parent.parent.parent / "config" / "models.yaml"

    data = load_yaml_file(profiles_path)

    try:
        profiles = ModelProfiles(**data)
        return profiles
    except Exception as e:
        raise ConfigError(f"Invalid model profiles: {e}")


def save_config(config: Config, config_path: Path) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Config object to save
        config_path: Path to save configuration

    Raises:
        ConfigError: If unable to save configuration
    """
    try:
        # Convert to dict
        config_dict = config.model_dump(mode="json", exclude_none=True)

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    except Exception as e:
        raise ConfigError(f"Error saving configuration: {e}")
