# Home Assistant (snap)

Snap (Snapcraft.yaml) recipe for the Open source home automation software, [Home Assistant](https://www.home-assistant.io/) that puts local control and privacy first. Powered by a worldwide community of tinkerers and DIY enthusiasts. Perfect to run on a Raspberry Pi or a local server.

This page will only include specific information about the snap-version of Home Assistant. For general Home Assistant questions, see their official [Help page](https://www.home-assistant.io/help/) and [Community Forum](https://community.home-assistant.io/).

Our tagging is reflecting the Home Assistant version numbers, but we might not release a tag for each version of Home Assistant.

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/home-assistant-snap)
[![Donate with PayPal](https://giaever.online/paypal-donate-button.png)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=69NA8SXXFBDBN&source=https://git.giaever.org/joachimmg/home-assistant-snap)

## About this project

This snap-version of Home Assistant was made with the intention of running a home automation system on multiple remote location. Snap was choosen as it is an transactional, self updating package manager, which will let us not have to travel to the location(s) to do updates on each system.

Based on this intention we have choosen a strict confinement, which should work out of the box on the [Ubuntu Core](https://ubuntu.com/core) operating system and similar. As changes to the snap on these systems are limited we have also built several other snaps that will integrate with this version or help manage devices remotely.

* [Home Assistant Community Store](https://git.giaever.org/joachimmg/home-assistant-hacs)-integration gives you a powerful UI to handle downloads of all your custom needs.
* [HASS Configurator](https://git.giaever.org/joachimmg/home-assistant-configurator)-integration to allow easy configuration of Home Assistant.
* [acme.sh](https://git.giaever.org/joachimmg/acme-sh) (SSL): probably the easiest & smartest shell script to automatically issue & renew the free certificates from Let's Encrypt.
* [ddclient](https://git.giaever.org/joachimmg/ddclient-snap): client used to update dynamic DNS entries for accounts on many dynamic DNS services.

We're also working on a solution to extend the installation further so you can add additional libaries (curl, wget, ssh) that you will need to be able to build your system as you want.

Please file all issues using the main git-repository found at [git.giaever.org](https://git.giaever.org/joachimmg/home-assistant-snap/issues).

## Frequently asked questions

* **How do I configure Home Assistant from this snap**
    * If your using Home Assistant on a desktop or server edition you will be able to use your favourite text editor. The configurations files is store in `/var/snap/home-assistant-snap/current`. You will need to have root access.
    * If you can't locate the configuration files (it may differ on some distributions), log into the daemon' shell with `sudo snap run --shell home-assistant-snap` and execute `echo $SNAP_DATA`. This should return a path similar that is mentioned above, but containing a digit (the revision number of the current running version). When you have figured out the path, it's wise to exchange the `revision number` with `current`, as this number will change frequently and `current` will always be linked to the currently used revision.
    * If you don't have root access or want to be able to update the configurations through a web solution, have a look at the [home-assistant-configurator](https://git.giaever.org/joachimmg/home-assistant-configurator). 
* **How can I secure my Home Assistant with SSL (HTTPS)?**
    * Install [acme-sh](https://git.giaever.org/joachimmg/acme-sh) and connect `acme-sh`'s and home-assistant-snap's slot/plug with `snap connect acme-sh:certs home-assistant-snap:certs`. 
    * After you have issued the certificate, you'll find the decrypted files in `/var/snap/home-assistant-snap/current/.ssl`. You'll then add a [http-entry](https://www.home-assistant.io/integrations/http/) in your configuration file.
    * Home Assistant is configured to scan for updated certificates, replace them and to restart to use the new version. 
* **How do I use dynamic DNS?**
    * Use `ddclient-snap`, see: [cclient-snap](https://git.giaever.org/joachimmg/ddclient-snap)

## Build and installation
### Install from The Snap Store (Recommended)

Make sure you have Snapd installed on your system. See [Installing snapd](https://snapcraft.io/docs/installing-snapd) for a list of distributions with and without snap pre-installed, including installation instructions for those that have not.

```bash
$ snap install home-assistant-snap
```

### Build this snap from source

We recommend that your download a pre-built version of this snap from [The Snap Store](https://snapcraft.io/home-assistant-snap), or at least make sure that you checkout the latest tag, as the master tag might contain faulty code during development.

1. **Clone this repo and checkout the latest tag**

```bash
$ git clone https://git.giaever.org/joachimmg/home-assistant-snap.git

# Go into directory
$ cd ./home-assistant-snap

# Checkout tag
$ git checkout <tag>
```
_**NOTE**: You can find the latest tag with `git ls-remote --tags origin`_

2. **Build and install**

Make sure you have snapd (see [Installing snapd](https://snapcraft.io/docs/installing-snapd)) and latest version of Snapcraft. Install Snapcraft with

```bash
$ sudo snap install snapcraft --classic
```

Or update with

```bash
$ sudo snap refresh snapcraft
```

2.2 **With multipass**

From the «home-assistant-snap»-directory, run

```bash
$ snapcraft
```

Multipass will be installed and a virtual machine will boot up and build your snap. The final snap will be located in the same directory.

2.3 **With LXD** (*required* for Raspberry Pie)

Snapcraft will try to install multiplass and build the snap for you, but on *Raspberry Pi* it will fail. You will have to use an LXD container.

Install LXD and create a container

```bash
$ snap install lxd
$ snap lxd init
```

Make sure your user is a member of lxd-group

```bash
$ sudo adduser $USER lxd
```

Launch an Ubuntu 20.04 container instance

```bash
$ lxc launch ubuntu:20.04 home-assistant-snap
```

Make sure you're in the «home-assistant-snap»-directory and go into the shell of your newly created container

```bash
$ lxc exec -- home-assistant-snap /bin/bash
```

and run

```bash
$ SNAPCRAFT_BUILD_ENVIRONMENT=host snapcraft
```

when the build is complete, you'll have to exit the shell and pull the snap-file from the container. See `lxc file pull --help`.

3. **Install new built snap**

```
$ sudo snap install ./home-assistant-snap_<source-tag>.snap --dangerous
```
