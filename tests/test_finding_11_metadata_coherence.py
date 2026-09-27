import re
from pathlib import Path

def test_version_coherence():
    """Verify version 1.1.1 is coherent across pyproject.toml, config.py, and readme.md."""
    root = Path(__file__).parent.parent
    
    # 1. pyproject.toml
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
    assert pyproject_match, "version not found in pyproject.toml"
    pyproject_version = pyproject_match.group(1)
    
    # 2. config.py
    config_text = (root / "src" / "core" / "config.py").read_text(encoding="utf-8")
    config_match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', config_text)
    assert config_match, "APP_VERSION not found in config.py"
    config_version = config_match.group(1)
    
    # 3. readme.md
    readme_text = (root / "readme.md").read_text(encoding="utf-8")
    readme_match = re.search(r'(?:\*\*Version\*\*:\s*|v)(\d+\.\d+\.\d+)', readme_text)
    assert readme_match, "Version not found in readme.md"
    readme_version = readme_match.group(1)
    
    assert pyproject_version == "1.1.1"
    assert config_version == "1.1.1"
    assert readme_version == "1.1.1"
    assert pyproject_version == config_version == readme_version

def test_readme_links_and_referenced_files():
    """Verify readme.md does not reference absent files or placeholder clone URLs."""
    root = Path(__file__).parent.parent
    readme_text = (root / "readme.md").read_text(encoding="utf-8")
    
    # Clone URL should be the actual repository
    assert "https://github.com/3453-315h/Comic-Scanlation-Studio.git" in readme_text
    assert "yourusername" not in readme_text
    
    # Must not refer to absent build.bat
    assert "build.bat" not in readme_text
    
    # Must not link to absent LICENSE file
    assert "[LICENSE](LICENSE)" not in readme_text
    assert "LICENSE.md" not in readme_text
