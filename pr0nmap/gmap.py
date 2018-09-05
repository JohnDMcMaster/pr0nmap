import os

class GMap:
    def __init__(self, source, copyright_=None):
        self.source = source
        self.copyright = copyright_
        
        self.page_title = None
        # Consider mangling this pased on the image name
        self.id = 'si_canvas'
        self.out_dir = 'map'
        self.max_level = None
        self.min_level = 0
        self.image = None
        # don't error on missing tiles in grid
        self.skip_missing = False
        self.set_im_ext('.jpg')
        self.tw = 250
        self.th = 250

    def set_title(self, titile):
        self.page_title = titile

    def set_js_only(self, js_only):
        self.js_only = js_only

    def set_skip_missing(self, skip_missing):
        self.skip_missing = skip_missing

    def set_out_dir(self, out_dir):
        self.out_dir = out_dir

    def set_im_ext(self, s):
        self.im_ext = s
        self.source.im_ext = s
        self.out_format = s.replace('.', '')
        if self.out_format == 'png':
            self.is_png_str = 'isPng: true,'
        else:
            self.is_png_str = ''
    
    def header(self):
        # Note: fixed to v3.31 after v3.32 started mirroring
        return '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<!-- Generated by pr0nmap 1.0 --> 
<html>
<head>
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />  
<title>%s</title>
<script type="text/javascript" src="https://maps.google.com/maps/api/js?v=3.31&sensor=false"></script>
<style type="text/css">
  html { height: 100%% }
  body { height: 100%%; margin: 0; padding: 0 }
  #%s { height: 100%% }
</style>

</head>
<body>
''' % (self.page_title, self.id);

    def get_js(self):
        ret = ''
        ret += self.header()
        ret += self.div()
        ret += self.script()
        ret += self.footer()
        return ret

    def div(self):
        return '''
<div id="%s"></div>
''' % self.id;

    def script(self):
        ret = ''
        ret += self.script_header()
        ret += self.SiProjection_ctor()
        ret += self.fromLatLngToPoint()
        ret += self.fromPointToLatLng()
        ret += self.create_map()
        ret += self.script_footer()
        return ret
        
    def width(self):
        return self.source.width()
    def height(self):
        return self.source.height()
        
    def SI_MAX_ZOOM(self):
        return self.max_level
        
    def SI_RANGE_X(self):
        return self.width() / (2**self.SI_MAX_ZOOM())
    
    def SI_RANGE_Y(self):
        return self.height() / (2**self.SI_MAX_ZOOM())
    
    def script_header(self):
            return '''
<script>
//WARNING: this page is automatically generated by pr0nmap
var options = {
  scrollwheel: true,
  //FIXME: look into
  //scaleControl: true,
  mapTypeControlOptions: {style: google.maps.MapTypeControlStyle.DROPDOWN_MENU},
  streetViewControl: false
}
''';

    def SiProjection_ctor(self):
        return '''
function SiProjection() {
  // Using the base map tile, denote the lat/lon of the equatorial origin.
  this.worldOrigin_ = new google.maps.Point(%d / 2, %d / 2);

  // This projection has equidistant meridians, so each longitude
  // degree is a linear mapping.
  this.worldCoordinatePerLonDegree_ = %d / 360;
  this.worldCoordinatePerLatDegree_ = %d / 360;
};
''' % (self.SI_RANGE_X(), self.SI_RANGE_Y(), self.SI_RANGE_X(), self.SI_RANGE_Y());

    def fromLatLngToPoint(self):
        return '''
SiProjection.prototype.fromLatLngToPoint = function(latLng) {
    var origin = this.worldOrigin_;
    var x = origin.x + this.worldCoordinatePerLonDegree_ * latLng.lng();
    var y = origin.y + this.worldCoordinatePerLatDegree_ * latLng.lat();
    return new google.maps.Point(x, y);
};
''';

    def fromPointToLatLng(self):
        return '''
SiProjection.prototype.fromPointToLatLng = function(point, noWrap) {
  var y = point.y;
  var x = point.x;

  if (x < 0) {
    x = 0;
  }
  if (x >= %d) {
    x = %d;
  }
  if (y < 0) {
    y = 0;
  }
  if (y >= %d) {
    y = %d;
  }

  var origin = this.worldOrigin_;
  var lng = (x - origin.x) / this.worldCoordinatePerLonDegree_;
  var lat = (y - origin.y) / this.worldCoordinatePerLatDegree_;
  return new google.maps.LatLng(lat, lng, noWrap);
};
''' % (self.SI_RANGE_X(), self.SI_RANGE_X(), self.SI_RANGE_Y(), self.SI_RANGE_Y());

    def create_map(self):
        return ('''
var siMap = new google.maps.Map(document.getElementById("si_canvas"), options);
siMap.setCenter(new google.maps.LatLng(1, 1));
siMap.setZoom(%d);

var %s = new google.maps.ImageMapType({
  getTileUrl: function(ll, z) {
      //TODO: consider not 0 padding if this is going to be a performance issue
      //it does make organizing them easier though
    return "tiles_out/" + z + "/y" + String("00" + ll.y).slice(-3) + "_x" + String("00" + ll.x).slice(-3) + "%s"; 
  },
  format:"%s",
  tileSize: new google.maps.Size(''' + str(self.tw) + ', ' + str(self.th) + '''),
  %s
  maxZoom: %d,
  name: "SM",
  alt: "IC map"
});
''') % (self.min_level, self.type_obj_name(), self.im_ext, self.out_format, self.is_png_str, self.SI_MAX_ZOOM())

    def type_obj_name(self):
        #return 'mos6522NoMetal'
        return 'ICImageMapType'

    def map_type(self):
        #return 'mos6522'
        return 'ICImageMapType'

    def script_footer(self):
        ret = '''
%s.projection = new SiProjection();


siMap.mapTypes.set('%s', %s);
siMap.setMapTypeId('%s');
''' % (self.type_obj_name(), self.type_obj_name(), self.type_obj_name(), self.type_obj_name())
        if self.copyright:
            ret += '''
// Create div for showing copyrights.
var copyrightNode;
copyrightNode = document.createElement('div');
copyrightNode.id = 'copyright-control';
copyrightNode.style.fontSize = '11px';
copyrightNode.style.fontFamily = 'Arial, sans-serif';
copyrightNode.style.margin = '0 2px 2px 0';
copyrightNode.style.whiteSpace = 'nowrap';
copyrightNode.index = 0;
copyrightNode.innerHTML = "%s";
siMap.controls[google.maps.ControlPosition.BOTTOM_RIGHT].push(copyrightNode);
''' % self.copyright

        ret += '''
siMap.setOptions({
  mapTypeControlOptions: {
    mapTypeIds: [
      '%s'
    ],
    style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
  },
  streetViewControl: false
});


</script>
''' % (self.map_type(),)
        return ret

    def footer(self):
        return '''
</body>
</html>
''';

    def zoom_factor(self):
        return 2

    def calc_max_level(self):
        self.max_level = self.source.calc_max_level()

    def gen_js(self):
        if self.page_title is None:
            self.page_title = 'SiMap: %s' % self.source.get_name()
    
        # If it looks like there is old output and we are trying to re-generate js don't nuke it
        if os.path.exists(self.out_dir) and not self.js_only:
            os.system('rm -rf %s' % self.out_dir)
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)

        if self.max_level is None:
            self.calc_max_level()
        js = self.get_js()
        js_filename = '%s/index.html' % self.out_dir
        print 'Writing javascript to %s' % js_filename
        open(js_filename, 'w').write(js)
        
        self.image = None

    # FIXME / TODO: this isn't the google reccomended naming scheme, look into that more    
    # part of it was that I wanted them to sort nicely in file list view
    @staticmethod
    def get_tile_name(dst_dir, level, row, col, im_ext):
        zoom_dir = '%s/%s' % (dst_dir, level + 1)
        if not os.path.exists(zoom_dir):
            os.mkdir(zoom_dir)
        return '%s/y%03d_x%03d%s' % (zoom_dir, row, col, im_ext)

    def run(self):
        '''
        It would be a good idea to check the tiles gnerated against what we are expecting
        '''
        # generate javascript
        self.gen_js()
        if not self.js_only:
            print
            print
            print

            self.source.generate_tiles(self.max_level, self.min_level, self.get_tile_name, dst_basedir='%s/tiles_out' % self.out_dir)
