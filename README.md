# home-assistant-snap

Snap (Snapcraft.yaml) recipe for the Open source home automation software that puts local control and privacy first.

Current Home Assistant version: 0.90.1

# Build
Simply

1. ##### Clone repo over HTTPS

```
git clone https://git.giaever.org/joachimmg/home-assistant-snap.git
```

2. ##### Change directory into the cloned repository

```
$ cd ~/home-assistant-snap/
```

and checkout the latest tag (e.g `$ git checkout 0.112.3`) as the master branch might not be functioning.

3. ##### Build & install
3.1 Make sure you have snapcraft installed: 

```
sudo snap install snapcraft --classic && hash -r
```

3.2 Build with 

```
$ snapcraft
```

3.3 Install with (change «packagename» to filename of the produced snap).

```
$ ls -al | grep .snap
$ snap install --devmode --dangerous <packagename>.snap
``` 

4. #### Notes on building on a Raspberry Pi

Snapcraft will try to install multipass for you, but on *Raspberry Pi* it will fail. You will have to use an LXD container, before any of the previous steps.

4.1 Install LXD on the Pi:

```
$ snap install lxd
```

4.2 Create a container

```
$ sudo lxd init
```

4.3 Make sure your user is a member of lxd-group

```
sudo adduser $USER lxd
```

_(it might tell that you already are...)_

4.4 Launche a Ubuntu 20.04 container instance
```
lxc launch ubuntu:20.04 home-assistant-container
```

4.5 Go into the shell of the container

```
lxc exec -- home-assistant-container /bin/bash
```

4.6 Continue with *step 1*, but replace *step 3.2* with the following:

```
SNAPCRAFT_BUILD_ENVIRONMENT=host snapcraft
```

as we have to build within the LXD container itself and not through multipass.
