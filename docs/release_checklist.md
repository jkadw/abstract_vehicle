# Release Checklist

Use this checklist before publishing a HACS release for `vehicle`.

## Metadata

- `custom_components/vehicle/manifest.json` has the correct version.
- `hacs.json` reflects the current minimum Home Assistant version and integration metadata.
- `README.md` matches the current behavior and setup path.
- documentation links in the manifest are valid.

## Package Structure

- `custom_components/vehicle/` contains the complete integration package.
- translation files are present.
- `services.yaml` matches the implemented service surface.
- internal planning files are not included in sync or release packaging when not intended.

## Quality

- Python files compile cleanly.
- tests are updated for any behavior change.
- adapter, normalization, and service changes remain separated by responsibility.
- no blocking calls were introduced.

## HACS Readiness

- the repository contains a tagged release for the published version.
- release notes summarize user-visible changes and limitations.
- the default branch contains the intended HACS install state.
- any known setup limitations are documented clearly in the README.

## Final Check

- confirm the integration can still be added through Home Assistant
- confirm config flow metadata is still correct
- confirm the manifest version matches the release tag
