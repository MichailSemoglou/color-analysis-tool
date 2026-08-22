# Security Policy

## Supported Versions

Security fixes are applied to the latest release line. Older releases do not
receive patches.

| Version | Supported |
| ------- | --------- |
| 1.3.x   | Yes       |
| < 1.3   | No        |

## Reporting a Vulnerability

Report vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/MichailSemoglou/color-analysis-tool/security/advisories/new).
Do not open a public issue for a vulnerability.

Include the affected version, steps to reproduce, and the impact you observe.
Reports are reviewed by the maintainer. This is a volunteer-maintained
project, so there is no guaranteed response time; accepted issues are fixed
on the main branch and released with the next patch.

## Scope Notes

- The tool parses untrusted image files through Pillow. Keep Pillow current:
  the dependency floor is raised when a security fix lands, and CI runs
  `pip-audit` on every push and pull request.
- Decompression-bomb protection is configured via `Image.MAX_IMAGE_PIXELS`
  with a limit of ~179 MP (178,956,970 pixels). Images above twice that
  (~358 MP) are rejected and skipped.
- Batch processing follows filesystem symlinks. Only analyze directories
  from sources you trust.
- Filenames are sanitized before they are embedded in generated reports,
  stylesheets, and token files.
