# Release Checklist for Color Analysis Tool v1.0.0

This document outlines the manual steps required to complete the release process after all automated preparation has been done.

## Pre-Release Verification

- [ ] All files have been created and updated
- [ ] Version number is consistent across all files (1.0.0)
- [ ] Package builds successfully (`python -m build`)
- [ ] CLI works correctly (`color-analysis --version`)
- [ ] Python imports work (`from color_analysis_tool import ImageAnalyzer`)

## Step 1: Git Operations

```bash
# Review all changes
git status
git diff

# Stage all new and modified files
git add .

# Commit changes
git commit -m "Prepare v1.0.0 release for PyPI and Zenodo

- Add pyproject.toml with PEP 621 metadata
- Restructure as proper Python package
- Add CLI entry point (color-analysis command)
- Create CITATION.cff for academic citations
- Create .zenodo.json for DOI minting
- Update README with badges and installation instructions
- Add CHANGELOG.md
- Update .gitignore"

# Push to GitHub
git push origin main
```

## Step 2: Create GitHub Release

1. Go to https://github.com/MichailSemoglou/color-analysis-tool/releases
2. Click "Create a new release"
3. Create a new tag: `v1.0.0`
4. Release title: `v1.0.0`
5. Use the following release notes:

```markdown
# Color Analysis Tool v1.0.0

First stable release of the Color Analysis Tool.

## Features

- Comprehensive color analysis for images
- Multiple color space support (RGB, HEX, CMYK)
- Color harmony calculations (complementary, analogous, triadic, tetradic)
- Multiple sorting options (frequency, hue, saturation, brightness)
- Dominant color detection
- Batch processing with recursive directory scanning
- Support for PNG, JPG, TIFF, WebP, and PSD formats
- Command-line interface (`color-analysis` command)
- Python API for library usage

## Installation

```bash
pip install color-analysis-tool
```

## Quick Start

```bash
# Analyze a single image
color-analysis image.jpg output/

# Process all images in a directory
color-analysis images/ output/
```

See the [README](https://github.com/MichailSemoglou/color-analysis-tool#readme) for full documentation.
```

6. Click "Publish release"

## Step 3: Enable Zenodo Integration

1. Go to https://zenodo.org/
2. Log in with your GitHub account
3. Go to Settings → GitHub
4. Find `MichailSemoglou/color-analysis-tool` and enable it
5. Zenodo will automatically create a DOI when you publish the GitHub release
6. After the DOI is minted, copy the DOI badge URL

## Step 4: Update Badge URLs

After Zenodo mints the DOI, update [README.md](README.md):

1. Replace `YOUR_DOI_HERE` with the actual DOI in the badge URL:
   ```markdown
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
   ```

2. Replace `YOUR_DOI_HERE` in the citation section with the actual DOI

3. Commit and push the changes:
   ```bash
   git add README.md
   git commit -m "Update DOI badge with actual Zenodo DOI"
   git push origin main
   ```

## Step 5: Publish to PyPI

### First Time Setup (if needed)

1. Create a PyPI account at https://pypi.org/account/register/
2. Enable 2FA (required for new accounts)
3. Create an API token at https://pypi.org/manage/account/token/
4. Store the token securely

### Build and Upload

```bash
# Ensure you're in the project directory
cd /path/to/color-analysis-tool

# Create a fresh virtual environment
python3 -m venv release_venv
source release_venv/bin/activate  # On Windows: release_venv\Scripts\activate

# Install build tools
pip install build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build the package
python -m build

# Check the package
twine check dist/*

# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ color-analysis-tool

# If everything works, upload to PyPI
twine upload dist/*

# Clean up
deactivate
rm -rf release_venv
```

### Verify PyPI Upload

1. Check the package page: https://pypi.org/project/color-analysis-tool/
2. Test installation: `pip install color-analysis-tool`
3. Verify the CLI: `color-analysis --version`

## Step 6: Post-Release Tasks

- [ ] Verify DOI badge works on GitHub
- [ ] Verify PyPI badge works on GitHub
- [ ] Test `pip install color-analysis-tool` in a fresh environment
- [ ] Announce the release (if applicable)

## Troubleshooting

### PyPI Upload Issues

If you get authentication errors:
```bash
# Use API token (recommended)
twine upload dist/* -u __token__ -p pypi-YOUR_TOKEN_HERE
```

### Package Name Conflicts

If `color-analysis-tool` is taken on PyPI, consider alternatives:
- `coloranalysis`
- `image-color-analyzer`
- `color-palette-analyzer`

Then update the name in `pyproject.toml` and rebuild.

### Zenodo Not Creating DOI

1. Ensure the repository is public
2. Check that Zenodo GitHub integration is enabled
3. The release must be a "published" release (not a draft)
4. Wait a few minutes for Zenodo to process

## Files Modified/Created

### New Files
- `pyproject.toml` - Package configuration
- `CITATION.cff` - Citation metadata
- `.zenodo.json` - Zenodo metadata
- `CHANGELOG.md` - Version history
- `requirements-dev.txt` - Development dependencies
- `color_analysis_tool/__init__.py` - Package init
- `color_analysis_tool/analyzer.py` - Core analysis code
- `color_analysis_tool/cli.py` - Command-line interface
- `RELEASE_CHECKLIST.md` - This file

### Modified Files
- `README.md` - Added badges, installation, citation section
- `requirements.txt` - Added comments
- `.gitignore` - Added project-specific entries

### Files That Can Be Removed (Optional)
- `color_analysis.py` - Original standalone script (functionality now in package)
