#!/usr/bin/env python3
"""
Prognosticator Setup and Initialization
Run this once to set up the application environment.
"""

import sys
import subprocess
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def check_python_version():
    """Verify Python 3.10+."""
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")


def check_ollama():
    """Check if Ollama is installed."""
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
        print("✅ Ollama installed")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠️ Ollama not found. Install from https://ollama.ai")
        return False


def create_directories():
    """Create required directories."""
    dirs = [
        "data",
        "logs",
        "config",
        "sources",
        "scripts",
        "docs"
    ]
    
    for d in dirs:
        path = PROJECT_ROOT / d
        path.mkdir(exist_ok=True)
    
    print("✅ Directories created")


def create_default_config():
    """Create default configuration file."""
    config_file = PROJECT_ROOT / "prognosticator.json"
    
    if config_file.exists():
        print("✅ Configuration file exists")
        return
    
    default_config = {
        "app": {
            "name": "Prognosticator",
            "version": "2.0",
            "theme": "dark"
        },
        "ollama": {
            "host": "http://localhost",
            "port": 11434,
            "mode": "http"
        },
        "feeds": {
            "rss": [
                {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "active": True},
                {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "active": True},
                {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?best-topics=world", "active": True},
                {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "active": True},
                {"name": "Guardian", "url": "https://www.theguardian.com/world/rss", "active": True},
                {"name": "CNN", "url": "https://rss.cnn.com/rss/edition_world.rss", "active": True},
            ],
            "trending": {
                "enabled": False,
                "google_trends": False,
                "exploding_topics": False
            }
        },
        "local_threats": {
            "enabled": True,
            "min_severity": 3,
            "scrape_interval_seconds": 600
        },
        "advanced": {
            "cache_ttl_seconds": 900,
            "max_retries": 3,
            "log_level": "INFO"
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"✅ Configuration created: {config_file}")


def init_database():
    """Initialize application database."""
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    
    try:
        from forecasting.database_manager import ensure_database_ready
        
        if ensure_database_ready():
            print("✅ Database initialized")
            return True
        else:
            print("❌ Database initialization failed")
            return False
    except ImportError as e:
        print(f"❌ Cannot import database manager: {e}")
        return False


def verify_dependencies():
    """Verify all required Python packages."""
    required = {
        "streamlit": "Streamlit web framework",
        "pandas": "Data manipulation",
        "requests": "HTTP client",
        "feedparser": "RSS feed parsing",
        "beautifulsoup4": "HTML parsing",
    }
    
    optional = {
        "pytrends": "Google Trends scraping",
        "playwright": "Web scraping",
        "pyyaml": "YAML parsing",
    }
    
    missing_required = []
    missing_optional = []
    
    for package, description in required.items():
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_required.append((package, description))
            print(f"❌ {package} - {description}")
    
    for package, description in optional.items():
        try:
            __import__(package)
            print(f"✅ {package} (optional)")
        except ImportError:
            missing_optional.append((package, description))
            print(f"⚠️ {package} (optional) - {description}")
    
    if missing_required:
        print("\n❌ Missing required packages:")
        for pkg, desc in missing_required:
            print(f"   pip install {pkg}")
        return False
    
    return True


def print_summary():
    """Print setup summary."""
    print("\n" + "=" * 60)
    print("🔮 PROGNOSTICATOR SETUP COMPLETE")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("1. Install/start Ollama: https://ollama.ai")
    print("2. Pull models: ollama pull llama2")
    print("3. Launch app: streamlit run scripts/app_complete.py")
    print("\n💡 Configuration file: prognosticator.json")
    print("📊 Database: data/live.db")
    print("📝 Logs: logs/app.log")
    print("\n" + "=" * 60)


def main():
    """Run setup."""
    print("🔮 Prognosticator Setup\n")
    
    check_python_version()
    check_ollama()
    create_directories()
    create_default_config()
    
    if not verify_dependencies():
        print("\n⚠️ Install dependencies: pip install -r requirements.txt")
    
    if not init_database():
        print("⚠️ Database initialization failed - will retry on app startup")
    
    print_summary()


if __name__ == "__main__":
    main()
