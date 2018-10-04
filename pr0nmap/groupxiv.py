import os
import math

def write_js(fn,
             width, height, tile_size, layer_name, chip_name, chip_name_raw=None, copyright=None,
             tile_ext='.jpg',
             url_base="https://siliconpr0n.org/lib/groupXIV/36",
             image_size=None):
    if image_size is None:
        # Round up to next power 2 tile size on largest dimension
        tiles_max = float(max(width, height)) / tile_size
        square = int(math.ceil(math.log(tiles_max, 2)))
        image_size = (2**square) * tile_size
        if 0:
            print('tiles: %0.1f' % tiles_max)
            print('square:%u' % square)
            print('image_size:%u' % image_size)
            import sys; sys.exit(0)

    open(fn, 'w').write('''\
<!DOCTYPE html>
<html>
  <head>
    <title>Loading...</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script type="text/javascript" src="%s/public_html/bundle/groupxiv.js"></script>
    <link type="text/css" rel="stylesheet" href="%s/public_html/bundle/groupxiv.css">
</head>
<body>
    <div id="viewer"></div>
    <script>
    initViewer({"scale": null, "layers": [{"imageSize": %s, "tileExt": "%s", "width": %u, "height": %u, "URL": "l1", "tileSize": %u, "name": "%s"}], "name": "%s", "name_raw": "%s", "copyright": "%s"});
    </script>
</body>
</html>
''' % (url_base, url_base, image_size, tile_ext, width, height, tile_size, layer_name, chip_name, chip_name_raw, copyright))

class GroupXIV:
    def __init__(self, source, copyright_=None):
        self.source = source
        self.copyright = copyright_
        
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

        write_js('%s/index.html' % self.out_dir,
             width=self.source.width(), height=self.source.height(), tile_size=self.tile_size, layer_name='???', chip_name='???', copyright=None,
             tile_ext='.jpg')

    def run(self):
        '''
        It would be a good idea to check the tiles gnerated against what we are expecting
        '''
        if self.max_level is None:
            self.max_level = self.source.calc_max_level()

        # generate javascript
        self.gen_js()
        if not self.js_only:
            print
            print
            print

            self.source.generate_tiles(self.max_level, self.min_level, self.get_tile_name, dst_basedir='%s/l1-tiles' % self.out_dir)
