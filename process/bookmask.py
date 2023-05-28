#!/usr/bin/python

#
# bookmask
#
# Take an image of a book against a known background and hand model
# and create a mask of the book without either background or hands.
#

import argparse, cv2, numpy

import handmodel, lasers

version = '0.1'

disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))

def create(source, background, model, angle=0):
  hand_mask = make_hand_mask(source, model)
  background_mask = make_background_mask(source, background, hand_mask)
  return background_mask

def make_hand_mask(source, histogram):
  hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
  cv2.normalize(histogram, histogram, 0, 255, cv2.NORM_MINMAX)
  probability = cv2.calcBackProject([hsv], [0, 1], histogram,
                                    [0, 180, 0, 256], 1)
  cv2.erode(probability, disk, probability, (-1, -1), 2)
  #cv2.imwrite('ghost.png', probability)
  retval, result = cv2.threshold(probability, 1, 255, cv2.THRESH_BINARY)
  #cv2.imwrite('threshold.png', result)
  cv2.dilate(result, disk, result, (-1, -1), 6)
  mask = numpy.zeros((source.shape[0] + 4, source.shape[1] + 4), numpy.uint8)
  big = cv2.copyMakeBorder(result, 1, 1, 1, 1, cv2.BORDER_CONSTANT, 0)
  cv2.floodFill(big, mask, (0, 0), 128, 0, 0, cv2.FLOODFILL_FIXED_RANGE)
  result = big[1:-1, 1:-1]
  result = numpy.where(result == 0, 255, result)
  retval, result = cv2.threshold(result, 254, 255, cv2.THRESH_BINARY)
  #cv2.imwrite('hand.png', result)
  result = cut_hands(result)
  #cv2.imwrite('masked_hand.png', result)
  return cv2.merge((result, result, result))

def cut_hands(mask):
  result = numpy.copy(mask)
  result[0:-1,0:-1] = 0
  contours, hierarchy = cv2.findContours(numpy.copy(mask),
                                         cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
  contourList = list(contours)
  contourList.sort(key = cv2.contourArea)
  for contour in contourList[-2:]:
    left = contour[contour[:,:,0].argmin()][0][0]
    right = contour[contour[:,:,0].argmax()][0][0]
    result[0:-1,left:right] = 255
  return result

def make_background_mask(source, background, hand_mask):
  size = source.shape
  image = cv2.subtract(source, hand_mask)
  cv2.subtract(image, background, image)
  #cv2.imwrite('subtracted.png', source)
  mask = numpy.zeros((size[0] + 4, size[1] + 4), numpy.uint8)
  big = cv2.copyMakeBorder(image, 1, 1, 1, 1, cv2.BORDER_CONSTANT, (0, 0, 0))
  cv2.floodFill(big, mask, (0, 0), (0, 0, 0), (50,50,50), (5,5,5),
                cv2.FLOODFILL_FIXED_RANGE)
  channels = cv2.split(big[1:-1, 1:-1])
  retval, blue = cv2.threshold(channels[0], 1, 255, cv2.THRESH_BINARY)
  retval, green = cv2.threshold(channels[1], 1, 255, cv2.THRESH_BINARY)
  retval, red = cv2.threshold(channels[2], 1, 255, cv2.THRESH_BINARY)
  result = cv2.bitwise_or(cv2.bitwise_or(blue, green), red)
  contours, hierarchy = cv2.findContours(result,
                                         cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
  contourList = list(contours)
  contourList.sort(key = cv2.contourArea)
  result[:,:] = 255
  cv2.drawContours(result, [contourList[-1]], 0, 0, thickness=cv2.cv.CV_FILLED)
  cv2.filter2D(result, -1, disk, result)
  return result

def main():
  parser = argparse.ArgumentParser(
      description='%(prog)s finds the book in an image, excluding the background and your hands or fingers. It must be callibrated with one or more background images and uses a hand model previously created with handmodel.py.')
  parser.add_argument('--version', action='version',
                      version='%(prog)s Version ' + version,
                      help='Get version information')
  parser.add_argument('--background', dest='background_path',
                      default='background.png',
                      help='Path to a background image. This image must be a photo taken of your background without any obtructions and under the same lighting conditions of your hands and book scans.')
  parser.add_argument('--hand', dest='hand_path',
                      default='hand.png',
                      help='An image with two hands in front of the background')
  parser.add_argument('--callibration', dest='callibration_path',
                      default='callibration.png',
                      help='An image of the lasers on the background for callibration')
  parser.add_argument('input_path',
                      help='Path to a document image')
  parser.add_argument('output_path',
                      help='A mask image with the document piece black and the background and any hands or fingers in white')
  options = parser.parse_args()
  callibration = cv2.imread(options.callibration_path)
  angle = 180 - lasers.findLaserAngle(callibration)
  background = lasers.rotate(cv2.imread(options.background_path), angle)
  #  hand = numpy.loadtxt(options.hand_path)
  hand = lasers.rotate(cv2.imread(options.hand_path), angle)
  source = lasers.rotate(cv2.imread(options.input_path), angle)
  model = handmodel.create(background, [hand])
  result = create(source, background, model)
  cv2.imwrite(options.output_path, result)

if __name__ == '__main__':
  main()
