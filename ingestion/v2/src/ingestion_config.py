"""Production Ingestion Configuration"""
from adaptive_controller import RateLimit, AdaptiveConfig
from dataclasses import dataclass


# ===== RATE LIMITING CONFIGS =====

@dataclass
class RateLimitPresets:
    """Pre-configured rate limits for different scenarios."""
    
    # Conservative: Good for initial testing, low resource servers
    CONSERVATIVE = RateLimit(
        tokens_per_second=10.0,
        max_burst=50.0,
        refill_interval=0.1
    )
    
    # Moderate: Balanced throughput and resource usage
    MODERATE = RateLimit(
        tokens_per_second=50.0,
        max_burst=250.0,
        refill_interval=0.1
    )
    
    # Aggressive: High throughput on well-resourced servers
    AGGRESSIVE = RateLimit(
        tokens_per_second=200.0,
        max_burst=1000.0,
        refill_interval=0.1
    )
    
    # Maximum: For dedicated ingestion servers
    MAXIMUM = RateLimit(
        tokens_per_second=500.0,
        max_burst=2500.0,
        refill_interval=0.05
    )


@dataclass
class AdaptiveControllerPresets:
    """Pre-configured adaptive controller profiles."""
    
    # Conservative: Minimal risk of overload
    CONSERVATIVE = AdaptiveConfig(
        base_rate_limit=RateLimitPresets.CONSERVATIVE,
        congestion_threshold=0.5,
        recovery_threshold=0.2,
        backpressure_factor=0.3,
        recovery_factor=1.1,
        max_rate_multiplier=1.5,
        min_rate_multiplier=0.1,
        feedback_window=200
    )
    
    # Balanced: Good for production
    BALANCED = AdaptiveConfig(
        base_rate_limit=RateLimitPresets.MODERATE,
        congestion_threshold=0.7,
        recovery_threshold=0.3,
        backpressure_factor=0.5,
        recovery_factor=1.2,
        max_rate_multiplier=2.0,
        min_rate_multiplier=0.2,
        feedback_window=150
    )
    
    # Aggressive: For sustained high throughput
    AGGRESSIVE = AdaptiveConfig(
        base_rate_limit=RateLimitPresets.AGGRESSIVE,
        congestion_threshold=0.8,
        recovery_threshold=0.4,
        backpressure_factor=0.6,
        recovery_factor=1.3,
        max_rate_multiplier=2.5,
        min_rate_multiplier=0.3,
        feedback_window=100
    )


# ===== WORKER POOL CONFIGS =====

@dataclass
class WorkerPoolConfig:
    """Worker pool configuration for different stages."""
    
    # Recommended worker counts based on CPU cores and task type
    # Formula: CPU-bound = cores, I/O-bound = 2-3x cores
    
    CHUNK_WORKERS_DEFAULT = 4  # CPU-bound (text parsing)
    CHUNK_WORKERS_AGGRESSIVE = 8  # 2x cores for I/O parallelism
    
    EMBED_WORKERS_DEFAULT = 4  # Depends on embedding service (network I/O)
    EMBED_WORKERS_AGGRESSIVE = 12  # High parallelism for remote embeddings
    
    STORE_WORKERS_DEFAULT = 4  # Database I/O
    STORE_WORKERS_AGGRESSIVE = 8  # Parallel DB connections
    
    # Batch sizes - larger batches reduce overhead, smaller reduce latency
    CHUNK_BATCH_SIZE_DEFAULT = 10
    CHUNK_BATCH_SIZE_AGGRESSIVE = 50
    
    EMBED_BATCH_SIZE_DEFAULT = 5
    EMBED_BATCH_SIZE_AGGRESSIVE = 20
    
    STORE_BATCH_SIZE_DEFAULT = 4
    STORE_BATCH_SIZE_AGGRESSIVE = 10


# ===== ENVIRONMENT PRESETS =====

@dataclass
class EnvironmentConfig:
    """Full configuration for different deployment environments."""
    
    class Local:
        """Local development configuration."""
        workers_chunk = 2
        workers_embed = 2
        workers_store = 2
        batch_chunk = 5
        batch_embed = 3
        batch_store = 2
        max_queue_depth = 100
        adaptive_profile = "CONSERVATIVE"
        embedding_model = "local"  # Use local embeddings
        db_connection_pool = 5
    
    class Standard:
        """Standard production configuration."""
        workers_chunk = 4
        workers_embed = 6
        workers_store = 4
        batch_chunk = 10
        batch_embed = 8
        batch_store = 4
        max_queue_depth = 1000
        adaptive_profile = "BALANCED"
        embedding_model = "ollama"  # Remote Ollama
        db_connection_pool = 20
    
    class HighThroughput:
        """High throughput production configuration."""
        workers_chunk = 8
        workers_embed = 12
        workers_store = 8
        batch_chunk = 50
        batch_embed = 20
        batch_store = 10
        max_queue_depth = 5000
        adaptive_profile = "AGGRESSIVE"
        embedding_model = "ollama"
        db_connection_pool = 50


def get_adaptive_config(profile: str) -> AdaptiveConfig:
    """
    Get adaptive controller config by name.
    
    Args:
        profile: "CONSERVATIVE", "BALANCED", or "AGGRESSIVE"
        
    Returns:
        AdaptiveConfig instance
    """
    profiles = {
        "CONSERVATIVE": AdaptiveControllerPresets.CONSERVATIVE,
        "BALANCED": AdaptiveControllerPresets.BALANCED,
        "AGGRESSIVE": AdaptiveControllerPresets.AGGRESSIVE
    }
    return profiles.get(profile, AdaptiveControllerPresets.BALANCED)


def get_environment_config(env: str) -> dict:
    """
    Get full configuration for environment.
    
    Args:
        env: "local", "standard", or "high_throughput"
        
    Returns:
        Dictionary of configuration values
    """
    configs = {
        "local": EnvironmentConfig.Local.__dict__,
        "standard": EnvironmentConfig.Standard.__dict__,
        "high_throughput": EnvironmentConfig.HighThroughput.__dict__
    }
    return configs.get(env, configs["standard"])


# ===== DATABASE CONFIGS =====

DATABASE_CONFIGS = {
    "postgresql": {
        "dialect": "postgresql",
        "driver": "psycopg2",
        "connection_string": "postgresql://user:password@localhost:5432/era_ingestion",
        "pool_size": 20,
        "max_overflow": 40,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    },
    "sqlite": {
        "dialect": "sqlite",
        "path": "./ingestion.db",
        "connection_string": "sqlite:///./ingestion.db"
    }
}


# ===== EMBEDDING SERVICE CONFIGS =====

EMBEDDING_CONFIGS = {
    "ollama_local": {
        "type": "ollama",
        "base_url": "http://localhost:11434",
        "model": "nomic-embed-text:latest",
        "embedding_dim": 768,
        "batch_size": 32,
        "timeout": 60
    },
    "ollama_remote": {
        "type": "ollama",
        "base_url": "http://embedding-service:11434",
        "model": "nomic-embed-text:latest",
        "embedding_dim": 768,
        "batch_size": 100,
        "timeout": 120
    },
    "sentence_transformers": {
        "type": "sentence_transformers",
        "model": "all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "batch_size": 128,
        "device": "cuda"  # or "cpu"
    },
    "openai": {
        "type": "openai",
        "api_key": "${OPENAI_API_KEY}",
        "model": "text-embedding-3-small",
        "embedding_dim": 1536,
        "batch_size": 100
    }
}


# ===== DOCTOR DAY RETRY CONFIGS =====

RETRY_CONFIGS = {
    "aggressive": {
        "max_retries": 5,
        "initial_delay": 1,  # seconds
        "max_delay": 30,
        "backoff_multiplier": 2.0,
        "jitter": 0.1
    },
    "moderate": {
        "max_retries": 3,
        "initial_delay": 2,
        "max_delay": 60,
        "backoff_multiplier": 2.0,
        "jitter": 0.1
    },
    "conservative": {
        "max_retries": 1,
        "initial_delay": 5,
        "max_delay": 30,
        "backoff_multiplier": 1.5,
        "jitter": 0.05
    }
}


# ===== MONITORING & LOGGING CONFIGS =====

MONITORING_CONFIGS = {
    "metrics_interval": 10,  # Log metrics every 10 seconds
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "log_file": "ingestion.log",
    "json_logs": False,  # Set True for JSON structured logging
    "prometheus_port": 8000  # For Prometheus scraping
}


# ===== HELPER FUNCTIONS =====

def create_orchestrator_config(environment: str = "standard") -> dict:
    """
    Create complete configuration for AsyncIngestionOrchestrator.
    
    Args:
        environment: "local", "standard", or "high_throughput"
        
    Returns:
        Dictionary suitable for orchestrator creation
    """
    env_config = get_environment_config(environment)
    adaptive_config = get_adaptive_config(env_config["adaptive_profile"])
    
    return {
        "chunk_workers": env_config["workers_chunk"],
        "embed_workers": env_config["workers_embed"],
        "store_workers": env_config["workers_store"],
        "max_queue_depth": env_config["max_queue_depth"],
        "adaptive_config": adaptive_config
    }


def get_full_config(environment: str = "standard") -> dict:
    """
    Get complete configuration including embedding, database, and monitoring.
    
    Args:
        environment: "local", "standard", or "high_throughput"
        
    Returns:
        Dictionary with all available configurations
    """
    env_config = get_environment_config(environment)
    adaptive_config = get_adaptive_config(env_config["adaptive_profile"])
    
    return {
        "orchestrator": {
            "chunk_workers": env_config["workers_chunk"],
            "embed_workers": env_config["workers_embed"],
            "store_workers": env_config["workers_store"],
            "max_queue_depth": env_config["max_queue_depth"],
            "adaptive_config": adaptive_config
        },
        "embedding_config": EMBEDDING_CONFIGS.get("ollama_local"),
        "database_config": DATABASE_CONFIGS.get("postgresql"),
        "retry_config": RETRY_CONFIGS.get("moderate"),
        "monitoring": MONITORING_CONFIGS,
        "environment": environment
    }


# Example: Print configs
if __name__ == "__main__":
    import json
    from dataclasses import asdict
    
    print("=== ENVIRONMENT CONFIGS ===\n")
    for env in ["local", "standard", "high_throughput"]:
        print(f"{env.upper()}:")
        config = get_environment_config(env)
        print(json.dumps(config, indent=2))
        print()
    
    print("=== SAMPLE ORCHESTRATOR CONFIG (Standard) ===\n")
    config = create_orchestrator_config("standard")
    # Convert AdaptiveConfig to dict for printing
    config_copy = config.copy()
    if hasattr(config_copy["adaptive_config"], "__dict__"):
        config_copy["adaptive_config"] = asdict(config_copy["adaptive_config"])
    print(json.dumps(config_copy, indent=2, default=str))
