---
name: OpenJarvis test environment setup
description: Notes on running tests for OpenJarvis project
type: project
---

## Test Framework
- Uses pytest with async support (pytest-asyncio)
- Test configuration in pyproject.toml under [tool.pytest.ini_options]
- Tests marked with: @pytest.mark.live, @pytest.mark.cloud, @pytest.mark.nvidia, @pytest.mark.apple, @pytest.mark.slow, @pytest.mark.macos15

## Running Tests
- Use: `UV_CACHE_DIR=/private/tmp/claude-502/uv_cache uv run pytest <path> -v`
- First must sync: `UV_CACHE_DIR=/private/tmp/claude-502/uv_cache uv sync --extra dev`
- Reason: /Users/nke/.cache/uv/sdists-v9/.git has permission issues in sandbox, workaround is temp cache dir

## Test Directories
- Main tests: `/Users/nke/projects/ai/OpenJarvis/OpenJarvis/OpenJarvis/tests/`
- Engine tests: `tests/engine/`
- Config tests: `tests/core/test_config*.py`
- Model catalog tests: `tests/intelligence/test_model_catalog*.py`

## Common Test Failures
- SSL certificate permission errors in engine tests (httpx client initialization)
- Engine tests fail when trying to create HTTP clients that need SSL context

## Test Stats (as of 2026-03-15)
- Engine tests: 185 failed, 63 passed, 25 errors
- Config/Catalog tests: 125 passed, 1 failed (test_apple_silicon expects mlx but gets llamacpp)
