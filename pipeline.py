import sys
import os
import time
import argparse
import logging

import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from torch.autograd import Variable

import PIL
from PIL import Image

import cv2
from skimage import io
import numpy as np
import craft_utils
import test
import imgproc
import file_utils
import json
import zipfile
import pandas as pd

from craft import CRAFT

from collections import OrderedDict


logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(asctime)s) %(name)s: %(message)s')

PIL.Image.MAX_IMAGE_PIXELS = 933120000

#CRAFT
parser = argparse.ArgumentParser(description='CRAFT Text Detection')
parser.add_argument('--trained_model', default='weights/craft_mlt_25k.pth', type=str, help='pretrained model')
parser.add_argument('--text_threshold', default=0.7, type=float, help='text confidence threshold')
parser.add_argument('--low_text', default=0.4, type=float, help='text low-bound score')
parser.add_argument('--link_threshold', default=0.4, type=float, help='link confidence threshold')
#parser.add_argument('--cuda', default=True, type=str2bool, help='Use cuda for inference')
parser.add_argument('--cuda', default=False, type=test.str2bool, help='Use cuda for inference') # 위 코멘트에서 수정됨
#parser.add_argument('--canvas_size', default=1280, type=int, help='image size for inference')
parser.add_argument('--canvas_size', default=12800, type=int, help='image size for inference') # 위 코멘트에서 수정됨
parser.add_argument('--mag_ratio', default=1.5, type=float, help='image magnification ratio')
parser.add_argument('--poly', default=False, action='store_true', help='enable polygon type')
parser.add_argument('--show_time', default=False, action='store_true', help='show processing time')
parser.add_argument('--test_folder', default='/data/', type=str, help='folder path to input images')
parser.add_argument('--refine', default=False, action='store_true', help='enable link refiner')
parser.add_argument('--refiner_model', default='weights/craft_refiner_CTW1500.pth', type=str, help='pretrained refiner model')

args = parser.parse_args()

""" For test images in a folder """
image_list, _, _ = file_utils.get_files(args.test_folder)

result_folder = './pipeline/'
if not os.path.isdir(result_folder):
    os.mkdir(result_folder)

detected_image = set()
for image in image_list:
    name = image.rstrip().split('/')[-1].split('.')[0]
    if os.path.isfile('{}/res_{}.txt'.format(result_folder, name)):
        detected_image.add(image)
image_list = sorted(list(set(image_list) - detected_image))

#CUSTOMISE START
image_names = []
image_paths = []
start = args.test_folder

for num in range(len(image_list)):
  image_names.append(os.path.relpath(image_list[num], start))

if __name__ == '__main__':

    data=pd.DataFrame(columns=['image_name', 'word_bboxes', 'pred_words', 'align_text'])
    data['image_name'] = image_names

    # load net
    net = CRAFT()     # initialize

    logging.info('Loading weights from checkpoint (' + args.trained_model + ')')
    if args.cuda:
        net.load_state_dict(test.copyStateDict(torch.load(args.trained_model)))
    else:
        net.load_state_dict(test.copyStateDict(torch.load(args.trained_model, map_location='cpu')))

    if args.cuda:
        net = net.cuda()
        net = torch.nn.DataParallel(net)
        cudnn.benchmark = False

    net.eval()

    # LinkRefiner
    refine_net = None
    if args.refine:
        from refinenet import RefineNet
        refine_net = RefineNet()
        logging.info('Loading weights of refiner from checkpoint (' + args.refiner_model + ')')
        if args.cuda:
            refine_net.load_state_dict(copyStateDict(torch.load(args.refiner_model)))
            refine_net = refine_net.cuda()
            refine_net = torch.nn.DataParallel(refine_net)
        else:
            refine_net.load_state_dict(copyStateDict(torch.load(args.refiner_model, map_location='cpu')))

        refine_net.eval()
        args.poly = True

    t = time.time()

    # load data
    for k, image_path in enumerate(image_list):
        logging.info("Test image {:d}/{:d}: {:s}".format(k+1, len(image_list), image_path))
        image = imgproc.loadImage(image_path)

        bboxes, polys, score_text, det_scores = test.test_net(net, image, args.text_threshold, args.link_threshold, args.low_text, args.cuda, args.poly, args, refine_net)
        
        bbox_score={}

        for box_num in range(len(bboxes)):
          key = str (det_scores[box_num])
          item = bboxes[box_num]
          bbox_score[key]=item

        data['word_bboxes'][k]=bbox_score
        # save score text
        filename, file_ext = os.path.splitext(os.path.basename(image_path))
        mask_file = result_folder + "/res_" + filename + '_mask.jpg'
        cv2.imwrite(mask_file, score_text)

        file_utils.saveResult(image_path, image[:,:,::-1], polys, dirname=result_folder + '/')

        if k%10 == 0:
            data.to_csv(result_folder + '/bboxes.csv', sep = ',', na_rep='Unknown')

    data.to_csv(result_folder + '/bboxes.csv', sep = ',', na_rep='Unknown')
    logging.info("elapsed time : {}s".format(time.time() - t))
