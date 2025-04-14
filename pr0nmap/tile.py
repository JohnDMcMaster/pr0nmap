#!/usr/bin/python
'''
pr0ntile: IC die image stitching and tile generation
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

from pr0nmap import pimage
from pr0nmap import tile_name

import sys
import os.path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
# 2023-06-23: some large images require this
# Unclear if they are actually damaged, but life moves on with this set
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
import shutil
import math
import queue
import multiprocessing
import traceback
import time
import errno


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# needed for PNG support
# rarely used and PIL seems to have bugs
PALETTES = bool(os.getenv('PR0N_PALETTES', '0'))
'''
def get_fn(basedir, row, col, im_ext='.jpg'):
    return '%s/y%03d_x%03d%s' % (basedir, row, col, im_ext)

def get_fn_level(basedir, level, row, col, im_ext='.jpg'):
    return '%s/%d/y%03d_x%03d%s' % (basedir, level, row, col, im_ext)
'''


def calc_max_level_from_image(image, zoom_factor=None):
    return calc_max_level(image.height(), image.width(), zoom_factor)


def calc_max_level(height, width, zoom_factor=None):
    if zoom_factor is None:
        zoom_factor = 2
    '''
    Calculate such that max level is a nice screen size
    Lets be generous for small viewers...especially considering limitations of mobile devices
    Originally I was doing based on screen reoslution, but think XIV wants 2x2 max at min level
    '''
    ts = 250
    fit_width = ts * 2
    fit_height = ts * 2

    width_levels = math.ceil(
        math.log(width, zoom_factor) - math.log(fit_width, zoom_factor))
    height_levels = math.ceil(
        math.log(height, zoom_factor) - math.log(fit_height, zoom_factor))
    max_level = int(max(width_levels, height_levels, 0))
    # Take the number of zoom levels required to fit the entire thing on screen
    print(
        'Calc max zoom level for %d X %d screen: %d (wmax: %d lev / %d pix, hmax: %d lev / %d pix)'
        % (fit_width, fit_height, max_level, width_levels, width,
           height_levels, height))
    return max_level


'''
Take a single large image and break it into tiles
'''


class ImageTiler(object):
    def __init__(self,
                 pim,
                 level,
                 dst_dir,
                 tw=250,
                 th=250,
                 im_ext='.jpg',
                 get_tile_name=None):
        self.verbose = False
        self.pim = pim
        self.level = level
        self.get_tile_name = get_tile_name
        self.progress_inc = 0.10

        self.x0 = 0
        self.x1 = pim.width()
        self.y0 = 0
        self.y1 = pim.height()

        self.tw = tw
        self.th = th
        self.dst_dir = dst_dir

        self.im_ext = im_ext

    def make_tile(self, x, y, row, col):
        xmin = x
        ymin = y
        xmax = min(xmin + self.tw, self.x1)
        ymax = min(ymin + self.th, self.y1)
        nfn = self.get_tile_name(self.dst_dir, self.level, row, col,
                                 self.im_ext)

        #if self.verbose:
        #print '%s: (x %d:%d, y %d:%d)' % (nfn, xmin, xmax, ymin, ymax)

        im = self.pim.image.crop((xmin, ymin, xmax, ymax))

        if PALETTES and self.pim.image.palette:
            im.putpalette(self.pim.image.palette)
            # XXX: workaround for PIL bug
            im = pimage.im_reload(im)

        # w/o pad map stretches image
        if im.size != (self.tw, self.th):
            #print 'resizing', x, y
            #print im.size, self.tw, self.th
            im = pimage.resize(im, self.tw, self.th)
        im.save(nfn)

    def run(self):
        '''
        Namer is a function that accepts the following arguments and returns a string:
        namer(row, col)
    
        python can bind objects to functions so a user parameter isn't necessary?
        '''
        '''
        if namer is None:
            namer = google_namer
        '''

        col = 0
        next_progress = self.progress_inc
        processed = 0
        n_images = len(list(range(self.x0, self.x1, self.tw))) * len(
            list(range(self.y0, self.y1, self.th)))
        for x in range(self.x0, self.x1, self.tw):
            row = 0
            for y in range(self.y0, self.y1, self.th):
                self.make_tile(x, y, row, col)
                row += 1
                processed += 1
                if self.progress_inc:
                    cur_progress = 1.0 * processed / n_images
                    if cur_progress >= next_progress:
                        print('Progress: %02.2f%% %d / %d' %
                              (cur_progress * 100, processed, n_images))
                        next_progress += self.progress_inc
            col += 1


'''
Only support tiled workers since unclear if full image can/should be parallelized
'''


class TWorker(object):
    def __init__(
        self,
        ti,
        qo,
        im_ext,
        # tile width/height
        tw,
        th):
        self.process = multiprocessing.Process(target=self.run)
        self.ti = ti

        self.qi = multiprocessing.Queue()
        self.qo = qo
        self.running = multiprocessing.Event()

        self.im_ext = im_ext
        self.tw = tw
        self.th = th
        self.zoom = 2.0

    def submit(self, event, args):
        self.qi.put((event, args))

    def complete(self, event, args):
        self.qo.put((self.ti, event, args))

    def task_subtile(self, val):
        dst_basedir, dst_get_tile_name, dst_row, dst_cols, src_basedir, src_get_tile_name, src_level = val
        src_rowb = 2 * dst_row
        src_get_tile_name = tile_name.mk_get_tile_name(src_get_tile_name)
        dst_get_tile_name = tile_name.mk_get_tile_name(dst_get_tile_name)

        # Workers are given 1 output row (2 input rows) at a time
        for dst_col in range(dst_cols):
            src_colb = 2 * dst_col

            # Collapse 2x2
            # XXX: how much faster would it be to actually know?
            # Would we save anything given that occasionally I process broken sets?
            # Just guess based on fn existing since its most foolproof anyway
            # adjust to be more accurate if we have a reason to care
            src_img_fns = [
                [None, None],
                [None, None],
            ]
            for src_col in range(src_colb, src_colb + 2):
                for src_row in range(src_rowb, src_rowb + 2):
                    fn = src_get_tile_name(src_basedir, src_level, src_row,
                                           src_col, self.im_ext)
                    src_img_fns[src_row - src_rowb][
                        src_col -
                        src_colb] = fn if os.path.exists(fn) else None

            img_full = pimage.from_fns(src_img_fns, tw=self.tw, th=self.th)
            #img_full = pimage.im_reload(img_full)
            img_scaled = pimage.rescale(img_full, 0.5, filt=Image.Resampling.LANCZOS)
            dst_fn = dst_get_tile_name(dst_basedir, src_level - 1, dst_row,
                                       dst_col, self.im_ext)
            img_scaled.save(dst_fn)

    def start(self):
        self.process.start()
        # Prevents later join failure
        self.running.wait(1)

    def run(self):
        self.running.set()
        #print 'Worker starting'
        while self.running.is_set():
            try:
                task, args = self.qi.get(True, 0.1)
            except queue.Empty:
                continue

            def task_subtile(args):
                self.task_subtile(args)
                self.complete('done', args)

            taskers = {
                'subtile': task_subtile,
            }

            try:
                taskers[task](args)
            except Exception as e:
                print('WARNING: got exception trying supertile %s' % str(task))
                traceback.print_exc()
                estr = traceback.format_exc()
                self.complete('exception', (task, e, estr))


'''
Creates smaller tiles from source tiles
'''


class Tiler(object):
    def __init__(self,
                 rows,
                 cols,
                 src_dir,
                 max_level,
                 min_level=0,
                 dst_basedir=None,
                 threads=1,
                 pim=None,
                 tw=250,
                 th=250,
                 im_ext='.jpg',
                 get_tile_name=None):
        self.src_dir = src_dir
        self.pim = pim
        self.get_tile_name = get_tile_name

        self.verbose = False
        self.cp_lmax = True
        self.max_level = max_level
        self.min_level = min_level
        self.dst_basedir = dst_basedir
        self.zoom_factor = 2
        self.tw = tw
        self.th = th
        # JPEG quality level, 1-100 or something
        self.quality = 90
        # Fraction of 1 to print each progress level at
        # None to disable
        self.progress_inc = 0.10
        self.threads = threads
        self.im_ext = im_ext

        self.workers = None

        self.rcs = {}
        for level in range(self.max_level, self.min_level - 1, -1):
            if rows == 0 or cols == 0:
                raise Exception()
            self.rcs[level] = (rows, cols)

            def div_rnd(x):
                # 4 => 2
                # 3 => 2
                # 2 => 1
                if x % 2 == 0:
                    return x // 2
                else:
                    return x // 2 + 1

            rows = div_rnd(rows)
            cols = div_rnd(cols)

    def wstart(self):
        self.workers = []
        self.wopen = set()
        # Our input queue / worker output queue
        self.qi = multiprocessing.Queue()
        for wi in range(self.threads):
            if self.verbose:
                print('Bringing up W%02d' % wi)
            w = TWorker(wi,
                        self.qi,
                        im_ext=self.im_ext,
                        tw=self.tw,
                        th=self.th)
            self.workers.append(w)
            w.start()
            self.wopen.add(wi)

    def wkill(self):
        if self.workers is None:
            return

        if self.verbose:
            print('Shutting down workers')
        for worker in self.workers:
            worker.running.clear()
        if self.verbose:
            print('Waiting for workers to exit...')
        allw = True
        for wi, worker in enumerate(self.workers):
            if worker is None:
                continue
            worker.process.join(1)
            if worker.process.is_alive():
                print('  W%d: failed to join' % wi)
                allw = False
            else:
                if self.verbose:
                    print('  W%d: stopped' % wi)
                self.workers[wi] = None
                self.wopen.remove(wi)
        if allw:
            self.workers = None

    def subtile(self, dst_level, src_basedir, src_get_tile_name, dst_basedir,
                dst_get_tile_name):
        '''Subtile from previous level'''
        src_level = dst_level + 1

        # Prepare a new image coordinate map so we can form the next tile set
        src_rows, src_cols = self.rcs[dst_level + 1]
        dst_rows, dst_cols = self.rcs[dst_level]

        print('Shrink by %0.1f: cols %s => %s, rows %s => %s' %
              (self.zoom_factor, src_cols, dst_cols, src_rows, dst_rows))

        next_progress = self.progress_inc
        done = 0

        # AttributeError: 'xrange' object has no attribute 'next'
        def dst_row_genf():
            for x in range(dst_rows):
                yield x

        dst_row_gen = dst_row_genf()

        while True:
            idle = True

            # No more jobs to give and all workers are idle?
            if dst_row_gen is None and len(self.wopen) == len(self.workers):
                break

            # Scrub completed tasks
            while True:
                try:
                    wi, event, val = self.qi.get(False)
                except queue.Empty:
                    break
                if event != 'done':
                    print(event, val)
                    raise Exception()
                idle = False
                self.wopen.add(wi)

                done += 1
                progress = 1.0 * done / dst_rows
                if self.progress_inc and progress >= next_progress:
                    print('Progress: %02.2f%% %d / %d' %
                          (progress * 100, done, dst_rows))
                    next_progress += self.progress_inc

            # More tasks to give?
            if dst_row_gen and len(self.wopen):
                # Assign next task
                try:
                    dst_row = next(dst_row_gen)
                # Out of tasks?
                except StopIteration:
                    dst_row_gen = None
                    continue

                idle = False
                worker = self.workers[self.wopen.pop()]
                worker.submit('subtile',
                              (dst_basedir,
                               tile_name.str_get_tile_name(dst_get_tile_name),
                               dst_row, dst_cols, src_basedir,
                               tile_name.str_get_tile_name(src_get_tile_name),
                               src_level))

            if idle:
                # Couldn't find something to do
                time.sleep(0.05)

        # Next shrink will be on the previous tile set, not the original
        if self.verbose:
            print('Shrinking the world for future rounds')

    def get_tle_name_pr0nts(self, root_dir, row, col, im_ext):
        return os.path.join(root_dir, "y%03u_x%03u%s" % (row, col, im_ext))

    def copy_max_dir(self, dst_level):
        #assert 0, 'fixme: file name mismatch'
        rows, cols = self.rcs[dst_level]

        if self.cp_lmax:
            skips = set()
            print('Source: direct copy rejigger %s => %s' %
                  (self.src_dir, self.dst_basedir))
            # shutil.copytree(self.src_dir, self.dst_basedir)
            fnref = None
            for x in range(cols):
                for y in range(rows):
                    src_fn = self.get_tle_name_pr0nts(self.src_dir, y, x,
                                                      self.im_ext)
                    dst_fn = self.get_tile_name(self.dst_basedir, dst_level, y,
                                                x, self.im_ext)
                    mkdir_p(os.path.dirname(dst_fn))
                    try:
                        shutil.copyfile(src_fn, dst_fn)
                        if not fnref:
                            print(("Ex: %s => %s" % (src_fn, dst_fn)))
                        fnref = src_fn
                    except IOError as e:
                        skips.add((x, y, dst_fn))
            print(("Skip %s" % len(skips)))
            # must be done after as it may be hard to get a reference image
            if len(skips):
                print("Creating fill image...")
                imref = Image.open(fnref)
                width, height = imref.size
                imblank = Image.new(imref.mode, (imref.size))
                """
                # noise image
                for y in range(height):
                    for x in range(width):
                        c = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                        imblank.putpixel((x, y), c)
                """
                print("Applying fill...")
                for (x, y, dst_fn) in skips:
                    imblank.save(dst_fn)
                print("Filled missing images")
        else:
            # explicitly load and save images to clean dir, same jpg format
            # a bit more paranoid but questionable utility still
            raise Exception()

    def run_src_dir(self):
        for dst_level in range(self.max_level, self.min_level - 1, -1):
            print()
            print('************')
            print('Zoom level %d' % dst_level)

            # For the first level we may just copy things over
            if dst_level == self.max_level:
                self.copy_max_dir(dst_level)
            # Additional levels we take the image coordinate map and shrink
            else:
                print('Source: tiles')
                self.subtile(dst_level, self.dst_basedir, self.get_tile_name,
                             self.dst_basedir, self.get_tile_name)

    def run_pim(self):
        for dst_level in range(self.max_level, self.min_level - 1, -1):
            print()
            print('************')
            print('Zoom level %d' % dst_level)

            # For the first level slice up source
            # Used to do all levels but it would result in OOM crash on large images
            # Plus only base level needs needs quality
            if dst_level == self.max_level:
                print('Source: single image')
                pim = self.pim
                tiler = ImageTiler(pim,
                                   dst_level,
                                   self.dst_basedir,
                                   tw=self.tw,
                                   th=self.th,
                                   im_ext=self.im_ext,
                                   get_tile_name=self.get_tile_name)
                tiler.run()
            # Additional levels we take the image coordinate map and shrink
            else:
                print('Source: tiles')
                self.subtile(dst_level, self.dst_basedir, self.get_tile_name,
                             self.dst_basedir, self.get_tile_name)

    def run(self):
        try:
            self.wstart()

            if not os.path.exists(self.dst_basedir):
                os.mkdir(self.dst_basedir)

            if self.src_dir:
                self.run_src_dir()
            elif self.pim:
                self.run_pim()
            else:
                raise Exception()

        finally:
            self.wkill()

    def __del__(self):
        self.wkill()
