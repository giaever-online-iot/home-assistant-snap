# home-assistant-snap

Snap (Snapcraft.yaml) recipe for the Open source home automation software that puts local control and privacy first.

Current Home Assistant version: 0.90.1

# Install
1. Make sure you have all [necessary tools](https://docs.snapcraft.io/installing-snapd/6735) to build a snap
2. Clone this repo ```git clone https://git.giaever.org/joachimmg/home-assistant-snap.git```
3. Go into the directoy ```cd home-assistant-snap``` and issue ``` snapcraft ``` to start building.

A file named ```home-assistant-snap[...].snap``` should now be in the folder and now you can install it with

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
