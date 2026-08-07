# Zenodo Release Checklist

No DOI is assigned yet. Do not add a placeholder DOI to the README, `CITATION.cff`, or manuscript.

1. Freeze the final manuscript and appendix values against `manifest/paper_value_crosscheck.csv`.
2. Run the package validators and privacy scan; resolve every failure.
3. Confirm the intended release commit contains the README, checksums, raw PF parts, logs, figures, and frozen selector.
4. Confirm every Git LFS object is downloadable. In GitHub repository settings, enable **Include Git LFS objects in archives** before creating the archival release; GitHub source archives otherwise contain LFS pointer files by default.
5. Validate both `CITATION.cff` and `.zenodo.json`. Zenodo uses `.zenodo.json` when both files are present, so its author, title, version, date, license, and description must be final before release.
6. Create the GitHub `v1.0.0` release from the frozen commit. Do not move or reuse that tag after publication.
7. Enable the repository in Zenodo's GitHub integration and archive the GitHub release, or upload a complete materialized archive directly to Zenodo when needed for LFS completeness.
8. Inspect the Zenodo deposit before publication: file names, byte sizes, checksums, metadata, license, authors, and version must match the release.
9. Publish the Zenodo record and record both the version DOI and concept DOI.
10. Use the version DOI as the fixed supplementary-package citation for the submitted manuscript; retain the GitHub URL as the code-update entry point.
11. Add the minted DOI to `README.md`, `README.zh-TW.md`, and `CITATION.cff`, then update the manuscript and appendix.
12. Re-run the value cross-check and package audit after the DOI-only metadata commit.

The DOI update must be a separate, traceable metadata change. It must not silently change experimental data or reported statistics.

Official references:

- https://help.zenodo.org/docs/github/enable-repository/
- https://help.zenodo.org/docs/github/archive-software/github-upload/
- https://help.zenodo.org/docs/github/describe-software/
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository
