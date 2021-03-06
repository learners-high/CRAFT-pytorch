import os
import shutil


os.makedirs('./crop_image_exploded', exist_ok=True)

for d in os.listdir('./crop_image'):
    if d == '.DS_Store':
        continue

    for f in os.listdir('./crop_image/{}'.format(d)):
        if f == '.DS_Store':
            continue
        shutil.copy('./crop_image/{}/{}'.format(d, f), './crop_image_exploded/{}'.format(f))
