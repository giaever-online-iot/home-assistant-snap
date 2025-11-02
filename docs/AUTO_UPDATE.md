# Automated Update Workflow

This repository includes an automated workflow that monitors the [Home Assistant Core repository](https://github.com/home-assistant/core) for new releases and automatically updates the snap.

## How It Works

The workflow (`.github/workflows/auto-update.yml`) performs the following steps:

1. **Check for New Releases** (every Friday at 23:00 UTC)
   - Fetches the latest tags from home-assistant/core
   - Filters out beta versions (tags ending in `b<number>`)
   - Compares with the current version in `snap/snapcraft.yaml`
   - Checks if a PR already exists for the new version

2. **Build and Test** (only if new version found and no PR exists)
   - Updates the `version` field in `snapcraft.yaml`
   - Builds the snap using `snapcore/action-build`
   - Reviews the snap using `diddlesnaps/snapcraft-review-action`
   - Uploads the built snap as an artifact (available for 30 days)

3. **Create Pull Request**
   - Creates a pull request with the version update and build results
   - Assigns the PR to the repository owner for review
   - Adds labels: `auto-update` and `version-update`
   - Includes links to the built snap artifact

## Manual Trigger

You can manually trigger the workflow for a specific version:

```bash
# Using GitHub CLI
gh workflow run auto-update.yml -f tag=2025.11.1

# Or through the GitHub UI
# Actions → Auto Update from Home Assistant Core → Run workflow
```

## Pull Request Review Process

When a new version is found, the workflow builds the snap and creates a pull request for manual review. The PR includes:

- **Version update** in `snapcraft.yaml`
- **Build status** showing the snap was successfully built and tested
- **Build artifact** attached to the workflow run (downloadable snap file, retained for 30 days)
- **Links** to Home Assistant release notes and workflow run
- **Review checklist** to help with the review process
- **Labels**: `auto-update` and `version-update`

The snap is built and tested **before** the PR is created, ensuring only successful builds result in a PR.

### Reviewing a PR

1. **Check the PR details**: Review the version number and changelog link
2. **Verify build passed**: The snap was already built and tested in the workflow
3. **Download and test** (optional): Download the pre-built snap artifact from the workflow run
4. **Review the changes**: Verify only the version field changed in `snapcraft.yaml`
5. **Check for breaking changes**: Review Home Assistant's release notes
6. **Merge when ready**: Merge the PR to accept the update

Note: The snap build and review already completed successfully before the PR was created.

### After Merging

After merging the PR:

1. **Optional**: Create a GitHub release manually:
   ```bash
   gh release create 2025.11.1 --title "Home Assistant 2025.11.1" --notes "See [Home Assistant Release Notes](https://github.com/home-assistant/core/releases/tag/2025.11.1)"
   ```

2. **Build for snap store** (if you publish to snap store):
   ```bash
   snapcraft
   snapcraft upload home-assistant-snap_*.snap --release=stable
   ```

3. **Update channels** as needed for major version changes

## Workflow Configuration

### Schedule

The workflow runs every Friday at 23:00 UTC. You can adjust this in the workflow file:

```yaml
schedule:
  - cron: '0 23 * * 5'  # Friday at 23:00 UTC
```

### Duplicate PR Prevention

The workflow checks if a PR already exists for a version before building:
- If a PR for the version already exists, the workflow skips building and PR creation
- This prevents duplicate PRs and wasted CI resources
- You can see existing PRs in the workflow logs

### Filtering Beta Versions

The workflow filters out beta versions using this pattern:

```bash
grep -E '^[0-9]+\.[0-9]+\.[0-9]+$'
```

This matches only stable versions like `2025.11.1` and excludes beta versions like `2025.11.0b1`.

## Requirements

For the workflow to work properly, ensure:

1. **Repository Secrets**: The workflow uses `GITHUB_TOKEN` (automatically provided)
2. **Write Permissions**: The workflow needs permission to:
   - Create pull requests
   - Build snaps (uses GitHub Actions runners)

Configure these in your repository settings under:
- Settings → Actions → General → Workflow permissions → "Allow GitHub Actions to create and approve pull requests"

## Testing Workflow

The snap build and testing happens **within the auto-update workflow**, not in a separate workflow:
- No need to wait for a separate `test-snap-can-build` workflow
- The snap is built, reviewed, and uploaded as an artifact before the PR is created
- PR is only created if the build succeeds

This approach uses `GITHUB_TOKEN` and doesn't require additional Personal Access Tokens.

## Monitoring

To monitor the workflow:

1. **GitHub Actions Tab**: Check the workflow runs and build logs
2. **Pull Requests**: Workflow creates PRs automatically when builds succeed
3. **Artifacts**: Download built snaps from successful workflow runs

## Version Channels

Remember that Home Assistant uses major version channels. After a successful automated build, you may want to:

1. Update the snap store channel information
2. Notify users about the new version
3. Test thoroughly before promoting to stable channels

## Related Files

- `.github/workflows/auto-update.yml` - Main workflow
- `snap/snapcraft.yaml` - Snap configuration
