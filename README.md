# home-assistant-snap

Snap (Snapcraft.yaml) recipe for the Open source home automation software that puts local control and privacy first.

Current Home Assistant version: 0.90.1

# Build
1. Clone the repo ```git clone https://git.giaever.org/joachimmg/home-assistant-snap.git```.
2. Go into the directoy ```cd home-assistant-snap```.
3. Check out the latest tag. The versioning is following the version of Home Assistant (e.g 0.90.1) plus a letter describing revision, e.g ```0.90.1.b```.
4. To compile the snap you can use two options:
	1. Make sure you have all [necessary tools](https://docs.snapcraft.io/installing-snapd/6735) to build a snap, and issue the command ```snapcraft``` to build with multipass (VM).
	2. Run the script ```./bin/lxdbuild``` to build with a LXD container, which will install all necessary tools and remove them after completion. This is the preferred method during development of this recipe.

# Install
A file named ```home-assistant-snap[...].snap``` (e.g home-assistant_0+git.5bd544d_amd64.snap) should now be in the root-folder of the project and now you can install it with

```bash
snap install [file] --devmode
```

## Issues

For issues directly related to Home Assistant, please read their article on [Reporting Issues](https://www.home-assistant.io/help/reporting_issues/). 

Issues with building or issues that is caused by missing dependencies etc and therefore cause problems with the running software, use the [issue tracker](https://git.giaever.org/joachimmg/home-assistant-snap/issues).

### Known problems

The build process reports a dependency issue with Selenium/Webdriver.

```wiki
Unable to determine library dependencies for 'prime/selenium/webdriver/firefox/x86/x_ignore_nofocus.so'
Unable to determine library dependencies for 'prime/lib/python3.6/site-packages/selenium/webdriver/firefox/x86/x_ignore_nofocus.so'
```

Feel free  to help out solving it!
