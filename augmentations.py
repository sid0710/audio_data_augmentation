import random
import os
import numpy as np
import tempfile
from os.path import basename
import subprocess
from scipy.io.wavfile import read,write
import math

#Change below to keep or delete the files
FILE_DELETION = False

#Output files directory (create if not already present)
outfile_path = "./output"
if not os.path.exists(outfile_path):
    os.makedirs(outfile_path)

def tmp_path(ext=''):
    tf = tempfile.NamedTemporaryFile()
    return tf.name + ext

#For reading wav files in mono
def monoWavRead(filename):
    fs, x = read(filename=filename)
    if (x.ndim==1):
        samples = x
    else:
        samples = x[:, 0]
    return fs, samples

def extractFeaturesAndDelete(filename):
    #Extract features or whatever else you want to do with the created augmented file before deletion here

    #Deletion
    os.unlink(filename)
    assert not os.path.exists(filename)

def random_cropping(infile, minLength = 1):
    """ Cropping the infile with a minimum duration of minLength

    Args:
        infile (str): Filename
        minLength (float) : Minimum duration for randomly cropped excerpt
    """
    fs, x = monoWavRead(filename = infile)
    endTime = x.size * 1/fs
    if (endTime > minLength):
        st = random.uniform(0.0, endTime - minLength)
        end = random.uniform(st + minLength, endTime)

        y = x[int(math.floor(st*fs)):int(math.ceil(end*fs))]

        #Change the output file name to suit your requirements here
        outfile_name = os.path.basename(infile).split(".")[0] + ("_randomCropped%s.wav" % minLength)
        outfile = os.path.join(outfile_path, outfile_name)
        write(filename = outfile, rate = fs, data = y)
        if (FILE_DELETION):
            extractFeaturesAndDelete(outfile)
    else :
        print "MinLength provided is greater than the duration of the song."
  
def add_noise(infile, noise_name, snr):
    """ Add noise to infile

    Args:
        infile (str): Filename
        noise_name (str): Name of noise (currently only 'white-noise')
        snr (float): SNR of output sound
    """
    fs1, x = monoWavRead(filename=infile)

    noise_path = './sounds/%s.wav' % noise_name
    fs2, z = monoWavRead(filename=noise_path)

    while z.shape[0] < x.shape[0]:
        z = np.concatenate((z, z), axis=0)
    z = z[0: x.shape[0]]
    rms_z = np.sqrt(np.mean(np.power(z, 2)))
    rms_x = np.sqrt(np.mean(np.power(x, 2)))
    snr_linear = 10 ** (snr / 20.0)
    noise_factor = rms_x / rms_z / snr_linear
    y = x + z * noise_factor
    rms_y = np.sqrt(np.mean(np.power(y, 2)))
    y = y * rms_x / rms_y

    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("_addedNoise%s.wav" % str(snr))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = y)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

def convolve(infile, ir_name, level = 0.5):
    """ Apply convolution to infile using impulse response given

    Args:
        infile (str): Filename
        ir_name can be  'smartphone_mic' or 'classroom'
        level (float) : can be between 0 and 1, default value = 0.5
    """
    fs1, x = monoWavRead(filename=infile)

    x = np.copy(x)
    #Change the path below for the sounds folder
    ir_path = './sounds/ir_{0}.wav'.format(ir_name)

    fs2, ir = monoWavRead(filename=ir_path)

    y = np.convolve(x, ir, 'full')[0:x.shape[0]] * level + x * (1 - level)

    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("{0}_convolved{1}.wav".format(ir_name, level))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = y)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

def apply_gain(infile, gain):
    """ Apply gain to infile

    Args:
        infile (str): Filename
        gain (float) : gain in dB (both positive and negative)
    """
    fs1, x = monoWavRead(filename=infile)

    x = np.copy(x)
    x = x * (10 ** (gain / 20.0))
    x = np.minimum(np.maximum(-1.0, x), 1.0)
    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("_gain%s.wav" % str(gain))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = x)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

def apply_rubberband(infile, time_stretching_ratio=1.0, pitch_shifting_semitones=1):
    """ Use rubberband tool to apply time stretching and pitch shifting

    Args:
        infile (str): Filename
        time_stretching_ratio (float): Ratio of time stretching (-9.99 to 9.99)
        pitch_shifting_semitones (int): Pitch shift in semitones

    """
    fs1, x = monoWavRead(filename=infile)

    tmp_file_1 = tmp_path()
    tmp_file_2 = tmp_path()
    write(filename = tmp_file_1, rate = fs1, data = x)
    cmd = "rubberband -c 1 -t {0} -p {1} {2} {3}".format(
        time_stretching_ratio,
        pitch_shifting_semitones,
        tmp_file_1,
        tmp_file_2)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"

    fs2, y = monoWavRead(filename=tmp_file_2)

    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("_timestr%s_pitchshift%s.wav" % (str(time_stretching_ratio),str(pitch_shifting_semitones)))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = y)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

def apply_dr_compression(infile, degree):
    """ Apply dynamic range compression using SOX

    Args:
        infile (str): Filename
        degree (int): Can be only 1, 2, 3
    """
    fs1, x = monoWavRead(filename = infile)

    tmpfile_1 = tmp_path('.wav')
    tmpfile_2 = tmp_path('.wav')

    write(filename = tmpfile_1, rate = fs1, data = x)
    if degree == 1:
        cmd = "sox {0} {1} compand 0.01,0.20 -40,-10,-30 5"
    elif degree == 2:
        cmd = "sox {0} {1} compand 0.01,0.20 -50,-50,-40,-30,-40,-10,-30 12"
    elif degree == 3:
        cmd = "sox {0} {1} compand 0.01,0.1 -70,-60,-70,-30,-70,0,-70 45"
    cmd = cmd.format(tmpfile_1, tmpfile_2)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"
    fs2, y = monoWavRead(filename = tmpfile_2)

    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("_drCompression%s.wav" % str(degree))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = y)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

def apply_eq(infile, value):
    """ Applying equalizer effects using SOX

    Args:
        infile (str): Filename
        value (three ';' separated values): freq_hz;bw_hz;gain_db (frequency;bandwidth;gain)
        
    From the SOX documentation (http://sox.sourceforge.net/sox.html) :
    Apply a two-pole peaking equalisation (EQ) filter. With this filter, the signal-level at and around 
    a selected frequency can be increased or decreased, whilst (unlike band-pass and band-reject filters) 
    that at all other frequencies is unchanged.
    Frequency gives the filter's central frequency in Hz, width the band-width, and gain the required gain or attenuation in dB
    Beware of Clipping when using a positive gain
    """

    fs1, x = monoWavRead(filename = infile)
    freq, bw, gain = map(int, value.split(';'))

    tmpfile_1 = tmp_path('.wav')
    tmpfile_2 = tmp_path('.wav')
    write(filename = tmpfile_1, rate = fs1, data = x)
    cmd = "sox {0} {1} equalizer {2} {3} {4}".format(
        tmpfile_1,
        tmpfile_2,
        freq,
        bw,
        gain)

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"
    fs2, y = monoWavRead(filename = tmpfile_2)
    #Change the output file name to suit your requirements here
    outfile_name = os.path.basename(infile).split(".")[0] + ("_eq%s.wav" % str(value))
    outfile = os.path.join(outfile_path, outfile_name)
    write(filename = outfile, rate = fs1, data = y)
    if (FILE_DELETION):
        extractFeaturesAndDelete(outfile)

