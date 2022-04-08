import os
import math
import json
"""
TODO: provide clear documentation on how metadata is interpreted
I think some of these are actually used by GroupXIV, some of these are placeholders I added

Top level
m["name"]
    Becomes title bar on window
m["copyright"]
    Is this an error? Should be layer copyright?

Layer
l["name"])
    Shown in lower right before layer copyright
l["copyright"]
    Shown in lower right. Copyright (C) is added by GroupXIV

"""


def write_js_meta(
    fn,
    meta,
    url_base="https://siliconpr0n.org/lib/groupXIV/stable",
):
    assert len(meta["layers"]) == 1, len(meta["layers"])
    out = '''\
<!DOCTYPE html>
<html>
  <head>
    <title>Loading...</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script type="text/javascript" src="%s/groupxiv.js"></script>
    <link type="text/css" rel="stylesheet" href="%s/groupxiv.css">
</head>''' % (url_base, url_base)
    out += '''\
<body>
    <div id="viewer"></div>
    <script>
'''
    out += '''\
    initViewer(%s);
''' % json.dumps(meta)

    out += '''\
    </script>
</body>
</html>
'''
    open(fn, 'w').write(out)


class GroupXIV:
    def __init__(self, source, copyright=None):
        self.source = source
        self.copyright = copyright

        self.title = None
        self.out_dir = 'map'
        self.max_level = None
        self.min_level = 0
        self.image = None
        # don't error on missing tiles in grid
        self.skip_missing = False
        self.set_im_ext('.jpg')
        # GroupXIV default is 500, but pr0nmap was 250
        self.tile_size = 250
        self.js_only = False

    def set_title(self, titile):
        self.title = titile

    def set_js_only(self, js_only):
        self.js_only = js_only

    def set_skip_missing(self, skip_missing):
        self.skip_missing = skip_missing

    def set_out_dir(self, out_dir):
        self.out_dir = out_dir

    def set_im_ext(self, s):
        self.im_ext = s
        self.source.im_ext = s

    # FIXME / TODO: this isn't the google reccomended naming scheme, look into that more
    # part of it was that I wanted them to sort nicely in file list view
    @staticmethod
    def get_tile_name(dst_dir, level, row, col, im_ext):
        level += 1

        zoom_dir = '%s/%s' % (dst_dir, level)
        try:
            os.mkdir(zoom_dir)
        except OSError:
            pass

        x_dir = '%s/%u' % (zoom_dir, col)
        try:
            os.mkdir(x_dir)
        except OSError:
            pass

        return '%s/%u%s' % (x_dir, row, im_ext)

    def gen_js(self):
        # If it looks like there is old output and we are trying to re-generate js don't nuke it
        if os.path.exists(self.out_dir) and not self.js_only:
            os.system('rm -rf %s' % self.out_dir)
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)

        def calc_image_size(l):
            # Round up to next power 2 tile size on largest dimension
            tiles_max = float(max(l["width"], l["height"])) / l["tileSize"]
            square = int(math.ceil(math.log(tiles_max, 2)))
            l["imageSize"] = (2**square) * l["tileSize"]

        # Fix image pan parameters
        # This is the most visible problem
        meta = {
            'tilesAlignedTopLeft':
            True,
            'scale':
            None,
            'layers': [{
                'imageSize': None,
                'tileExt': '.jpg',
                'width': self.source.width(),
                'height': self.source.height(),
                'URL': 'l1',
                'tileSize': self.tile_size,
                'name': self.source.get_name()
            }],
            'name':
            self.source.get_name()
        }
        l1 = meta["layers"][0]
        if self.copyright:
            l1['copyright'] = self.copyright
        calc_image_size(meta["layers"][0])
        write_js_meta('%s/index.html' % self.out_dir, meta=meta)

    def run(self):
        '''
        It would be a good idea to check the tiles gnerated against what we are expecting
        '''
        if self.max_level is None:
            self.max_level = self.source.calc_max_level()

        # generate javascript
        self.gen_js()
        if not self.js_only:
            print()
            print()
            print()

            self.source.generate_tiles(self.max_level,
                                       self.min_level,
                                       self.get_tile_name,
                                       dst_basedir='%s/l1-tiles' %
                                       self.out_dir)
