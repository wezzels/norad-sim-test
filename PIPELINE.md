# GitLab Pipeline Configuration
# Use these environment variables in GitLab CI/CD settings

# GITLAB_TOKEN: Your GitLab Personal Access Token
# Usage: Set in GitLab → Settings → CI/CD → Variables
# Scope: All branches (or main only for production)

# Example git push with token:
# git push https://oauth2:${GITLAB_TOKEN}@idm.wezzel.com/crab-meat-repos/norad-sim-test.git main

# Pipeline triggers:
# - Push to main: Run full test suite
# - Merge request: Run tests + lint
# - Scheduled (nightly): Run tests + security scan
# - Tag: Create release

# Coverage report is published to GitLab Pages at:
# https://wezzel.gitlab.io/norad-sim-test/