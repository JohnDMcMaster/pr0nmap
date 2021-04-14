#!/usr/bin/python
'''
Generate a complete Google Map from pre-stitched input image(s)
pre-stitched means non-overlapping
They can be either a single large input image or the bottom level tiles
'''

from pr0nmap.map import ImageMapSource, TileMapSource
from pr0nmap.gmap import GMap
from pr0nmap.groupxiv import GroupXIV

import argparse
import multiprocessing
import os
import re


# Keep pr0nmap/main.py and sipr0n/img2doku.py in sync
def parse_image_name(fn):
    fnbase = os.path.basename(fn)
    m = re.match(r'([a-z0-9\-]+)_([a-z0-9\-]+)_(.*).jpg', fnbase)
    if not m:
        raise Exception(
            "Non-confirming file name (need vendor_chipid_flavor.jpg): %s" %
            (fn, ))
    vendor = m.group(1)
    chipid = m.group(2)
    flavor = m.group(3)
    return (fnbase, vendor, chipid, flavor)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generate Google Maps code from image file(s)')
    parser.add_argument('images_in', nargs='+', help='image file or dir in')
    parser.add_argument('--out', '-o', default=None, help='Output directory')
    parser.add_argument('--js-only',
                        action="store_true",
                        dest="js_only",
                        default=False,
                        help='No tiles, only JavaScript')
    parser.add_argument('--skip-missing',
                        action="store_true",
                        dest="skip_missing",
                        default=False,
                        help='Skip missing tiles')
    parser.add_argument(
        '--out-extension',
        default=None,
        help='Select output image extension (and type), .jpg, .png, .tif, etc')
    parser.add_argument('--name',
                        dest="title_name",
                        help='SiMap: <name> title')
    parser.add_argument('--title',
                        dest="title",
                        help='Set title.  Default: SiMap: <project name>')
    parser.add_argument('--copyright',
                        '-c',
                        help='Set copyright message (default: none)')
    parser.add_argument('--threads',
                        type=int,
                        default=multiprocessing.cpu_count())
    parser.add_argument('--target',
                        choices=['gmap', 'groupxiv'],
                        default='groupxiv',
                        help='')
    args = parser.parse_args()

    for image_in in args.images_in:
        im_ext = args.out_extension
        out_dir = args.out

        if os.path.isdir(image_in):
            print('Working on directory of max zoomed tiles')
            source = TileMapSource(image_in, threads=args.threads)
        else:
            print('Working on single input image %s' % image_in)
            # Do auto-magic renaming for standard named die on sipr0n
            if not out_dir:
                # keep in sync with sipr0n/simapper.py
                sparts = image_in.split("/")
                if len(sparts) > 1 and sparts[-2] == "single":
                    _fnbase, _vendor, _chipid, flavor = parse_image_name(
                        image_in)
                    # Normalize:
                    # vendor/chipid/single/blah.jpg
                    # single/blah.jpg
                    out_dir = os.path.join(os.path.dirname(os.path.dirname(image_in)), flavor)
                    print('Auto-naming output file for sipr0n: %s' % out_dir)
            if not im_ext:
                im_ext = '.' + image_in.split('.')[-1]
            source = ImageMapSource(image_in, threads=args.threads)

        if not out_dir:
            out_dir = "map"
        if not im_ext:
            im_ext = '.jpg'

        title = args.title
        if args.title_name:
            title = "SiMap: %s" % args.title_name

        if args.target == 'gmap':
            m = GMap(source, copyright=args.copyright)
        else:
            m = GroupXIV(source, copyright=args.copyright)

        m.set_title(title)
        m.set_js_only(args.js_only)
        m.set_skip_missing(args.skip_missing)
        m.set_out_dir(out_dir)
        m.set_im_ext(im_ext)

        m.run()
