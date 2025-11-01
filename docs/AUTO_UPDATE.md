# Automated Update Workflow

This repository includes an automated workflow that monitors the [Home Assistant Core repository](https://github.com/home-assistant/core) for new releases and automatically updates the snap.

## How It Works

The workflow (`.github/workflows/auto-update.yml`) performs the following steps:

1. **Check for New Releases** (every 12 hours)
   - Fetches the latest tags from home-assistant/core
   - Filters out beta versions (tags ending in `b<number>`)
   - Compares with the current version in `snap/snapcraft.yaml`

2. **Update Version**
   - Updates the `version` field in `snapcraft.yaml` to the new version

3. **Create Pull Request**
   - Creates a pull request with the version update
   - Assigns the PR to the repository owner for review
   - Adds labels: `auto-update` and `version-update`

## Manual Trigger

You can manually trigger the workflow for a specific version:

```bash
# Using GitHub CLI
gh workflow run auto-update.yml -f tag=2025.11.1

# Or through the GitHub UI
# Actions → Auto Update from Home Assistant Core → Run workflow
```

## Pull Request Review Process

When a new version is successfully built, the workflow creates a pull request for manual review. The PR includes:

- **Version update** in `snapcraft.yaml`
- **Build artifact** attached to the workflow run (downloadable snap file)
- **Links** to Home Assistant release notes
- **Review checklist** to help with the review process
- **Labels**: `auto-update` and `version-update`

### Reviewing a PR

1. **Check the PR details**: Review the version number and changelog link
2. **Download and test** (optional): Download the snap artifact from the workflow run
3. **Review the changes**: Verify only the version field changed in `snapcraft.yaml`
4. **Check for breaking changes**: Review Home Assistant's release notes
5. **Merge when ready**: Merge the PR to accept the update

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

The workflow runs every 6 hours by default. You can adjust this in the workflow file:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Change to your preference
```

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

Configure these in your repository settings under:
- Settings → Actions → General → Workflow permissions → "Allow GitHub Actions to create and approve pull requests"

## Monitoring

To monitor the workflow:

1. **GitHub Actions Tab**: Check the workflow runs
2. **Pull Requests**: Workflow creates PRs automatically

## Version Channels

Remember that Home Assistant uses major version channels. After a successful automated build, you may want to:

1. Update the snap store channel information
2. Notify users about the new version
3. Test thoroughly before promoting to stable channels

## Related Files

- `.github/workflows/auto-update.yml` - Main workflow
- `snap/snapcraft.yaml` - Snap configuration
