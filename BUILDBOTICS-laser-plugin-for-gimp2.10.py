#!/usr/bin/env python2

from gimpfu import *
import gtk

import math
from array import *

gettext.install("gimp20-python", gimp.locale_directory, unicode=True)

def laser_power(min, max, pixel, threshold, intensity):
  if 255 - pixel < threshold: return 0
  return min + (max - min) * (255 - pixel) * intensity / 25500


def distance(x1, y1, x2, y2):
  return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))
  

def image_to_gcode(timg, drawable, useM106, outWidth, pixSize, feedRate, travelRate,
                   minPower, maxPower, minRapid, threshold, intensity) :
  
  dlg = gtk.FileChooserDialog("Pick a file", None,
                              gtk.FILE_CHOOSER_ACTION_SAVE,
                              (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
  dlg.set_do_overwrite_confirmation(True)
  ok = dlg.run()
  filename = dlg.get_filename()
  dlg.destroy()  
  
  width = int(outWidth / pixSize)
  height = int(timg.height * width / timg.width)

  timg = pdb.gimp_image_duplicate(timg)
  pdb.gimp_image_scale(timg, width, height)

  # Flatten image so that we handle alpha channel correctly
  pdb.gimp_context_push()
  pdb.gimp_context_set_background((255, 255, 255))
  pdb.gimp_image_flatten(timg)
  pdb.gimp_context_pop()

  if pdb.gimp_image_base_type(timg) != GRAY: pdb.gimp_image_convert_grayscale(timg)

  drawable = pdb.gimp_image_get_active_drawable(timg)
  pixels = drawable.get_pixel_rgn(0, 0, width, height)
  pixels = array('B', pixels[0:width, 0:height])

  pdb.gimp_progress_init('Generating GCode...', None)

  with open(filename, 'w+') as f:
  
    if useM106==False:
      f.write('G21G90\nM3F%d\n' % feedRate)
    else:
      f.write('G21\n')
      f.write('G90\n')
    
    forward = True
    lastX = lastY = None

    for row in range(height):
      y = row
      lastPower = None

      pdb.gimp_progress_update(float(row) / height)

      for col in range(width):
        x = col if forward else (width - col - 1)
        pixel = pixels[width * (height - y - 1) + x]
        power = laser_power(minPower, maxPower, pixel, threshold, intensity)
        end = col == width - 1
        
        #only add command if changes occur
        if col and power != lastPower or end:
          rapid = lastPower == 0

          if not end or not rapid:
            if rapid and lastX is not None:
              dist = distance(x, y, lastX, lastY) * pixSize
              if dist < minRapid: rapid = False

            lastX = x
            lastY = y
            
            if useM106==False:
              f.write('G%dX%0.2fY%0.2fS%d\n' % (
                0 if rapid else 1, x * pixSize, y * pixSize, lastPower))
            else:            
              if rapid:
                f.write('M106 S0\n')
                f.write('G0 F%0.2f X%0.2f Y%0.2f\n'%(travelRate, x * pixSize, y * pixSize))
              else:
                f.write('M106 S%d\n'%(lastPower))
                f.write('G1 F%d X%0.2f Y%0.2f\n'%(feedRate, x*pixSize, y*pixSize))
        lastPower = power

      forward = not forward
    if useM106==False:
        f.write('M5S0\n')
    else:
        f.write('M106 S0\n')

    pdb.gimp_image_delete(timg)
    pdb.gimp_progress_end()


register(
  'BUILDBOTICS-laser-plugin',
  N_('Laser engraving by Buildbotics\nCheck us out at buildbotics.com!'),
  'Export image to g-code for laser engraving',
  'Doug Coffland',
  'Doug Coffland',
  '2018,2019',
  N_('Export g-code for laser engraving...'),
  '*',
  [
    (PF_IMAGE, "timg",       "Input image", None),
    (PF_DRAWABLE, "drawable","Input drawable", None),
    (PF_BOOL,   'useM106',   'Use M106 instead', True),
    (PF_FLOAT,  'outWidth',  'Output image width (mm)', 100),
    (PF_FLOAT,  'pixSize',   'Size of one output pixel (mm)', 0.15),
    (PF_FLOAT,  'feedRate',  'Feed rate in mm/minute', 600),
    (PF_FLOAT,  'travelRate','Travel rate in mm/minute', 3000),
    (PF_INT,    'minPower',  'Mimimum LASER S-value', 0),
    (PF_INT,    'maxPower',  'Maximum LASER S-value', 255),
    (PF_FLOAT,  'minRapid',  'Minimum rapid distance (mm)', 5),
    (PF_INT,    'threshold', 'Minimum pixel value', 20),
    (PF_SLIDER, 'intensity', 'Laser intensity (%)', 100, [0, 100, 1]),
  ],
  [],
  image_to_gcode,
  menu="<Image>/File/Export",
  domain=("gimp20-python", gimp.locale_directory)
  )

main()
