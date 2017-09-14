from augmentations import *
import os

#Below test has been written to take all the files in a directory and apply all types of degradations 
#on them and create relevantly named files in the same directory. You can also apply them on single files

path = '/path/to/data/directory'
for file in os.listdir(path):
    current_file = os.path.join(path, file)
    print "current file - - - - -> " + current_file
    #The below line is to ignore the DS_Store file on a Mac (if not working on other environments, please delete it)
    if current_file!= "/path/to/data/directory/.DS_Store":
        random_cropping(current_file, 2)
        add_noise(current_file, 'white-noise', 20)
        convolve(current_file, 'classroom', 0.5)
        convolve(current_file, 'smartphone_mic', 0.5)
        apply_gain(current_file, 20)
        apply_rubberband(current_file, time_stretching_ratio=0.5)
        apply_rubberband(current_file, pitch_shifting_semitones=2)
        apply_dr_compression(current_file, 2)
        apply_eq(current_file, '500;50;30')
