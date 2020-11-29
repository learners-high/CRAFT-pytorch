from glob import glob
import shutil


for f in sorted(glob('crop_image_exploded/*_epi_1_*')):
   shutil.copy(f, 'crop_image_exploded_epi_1/')
