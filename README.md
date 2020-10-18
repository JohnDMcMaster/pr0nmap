# pr0nmap

Creates a web page that allows the user to zoom and pan on a very high resolution image.
Intended to help users view high resolution die photos on siliconpr0n.org

It can ingest either large .jpg files or a directory containing tiles

## .jpg quick start

For Ubuntu 16.04

```
sudo apt-get install python-pil
```

Get a .jpg. If you need inspiration:

```
wget https://siliconpr0n.org/map/macom/maam-011167/single/macom_maam-011167_mz_mit20x.jpg
```

Then run main.py on it:

```
./main.py macom_maam-011167_mz_mit20x.jpg
```

This will write a directory called "map".
Open map/index.html in your favorite browser and you should be able to pan and zoom.

As of Oct 2020 its still python2 and needs to be converted


## tile input quick start

TODO: add instructions

These are typically generated from xystitch (https://github.com/JohnDMcMaster/xystitch)

## .png quick start
This works but is hacky. TODO: add instructions


## GroupXIV support
This is the default rendering engine.

Library is more or less hard coded to use siliconpr0n.org.
However, if you are deploying your own large site or need offline use this can be fixed.

For setting up your own instance see https://github.com/whitequark/groupXIV

## Google maps support
This has been largely discontinued due to:
* Monetization changes
* Unstable API (non-map usage broke often)

The original version was Google maps but most sites have been converted off at this point.
The code hasn't been tested for a while and likely no longer works

TODO: consider removing entirely


## File name magic for directory "single"

Since this tool was primarily intended for siliconpr0n.org use, it has a magic rule that can match if point it to a file in a directory named "single". Images are expected to be named $vendor_$chipname_$stuff and this simplifies the output name to $stuff. 

