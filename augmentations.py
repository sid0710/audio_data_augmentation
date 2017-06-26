#from pysndfx import AudioEffectsChain
import essentia.standard as es
import argparse
import random
import os
import numpy as np
import tempfile
from os.path import basename
import logging
import subprocess

#TODO: Add support for output directory choice, currently it writes the output file in the same directory

def tmp_path(ext=''):
    tf = tempfile.NamedTemporaryFile()
    return tf.name + ext

def random_cropping(infile, minLength = 1):
    """ Cropping the infile with a minimum duration of minLength

    Args:
        infile (str): Filename
        minLength (float) : Minimum duration for randomly cropped excerpt
    """
    loader = es.MonoLoader(filename = infile)
    x = loader()
    fs = 44100
    endTime = x.size * 1/fs
    if (endTime > minLength):
        st = random.uniform (0.0, endTime - minLength)
        end = random.uniform(st + minLength, endTime)
        slicer = es.Slicer(startTimes = [st], endTimes = [end])
        y = slicer(x)
        #Change the output file name to suit your requirements here
        outfile_name = infile.split(".")[0] + ("_randomCropped%s.wav" % minLength)
        #outfile = os.path.join(outfile_path, outfile_name)
        writer = es.MonoWriter(filename = outfile_name)
        writer(y[0])
    else :
        print "MinLength provided is greater than the duration of the song."

def add_noise(infile, noise_name, snr):
    """ Add noise to infile

    Args:
        infile (str): Filename
        noise_name (str): Name of noise (currently only 'white-noise')
        snr (float): SNR of output sound
    """
    loader1 = es.MonoLoader(filename = infile)
    x = loader1()
    noise_path = './sounds/%s.wav' % noise_name
    loader2 = es.MonoLoader(filename = noise_path)
    z = loader2()
    while z.shape[0] < x.shape[0]:
        z = np.concatenate((z, z), axis=0)
    z = z[0: x.shape[0]]
    rms_z = np.sqrt(np.mean(np.power(z, 2)))
    logging.debug("rms_z: %f" % rms_z)
    rms_x = np.sqrt(np.mean(np.power(x, 2)))
    logging.debug("rms_x: %f" % rms_x)
    snr_linear = 10 ** (snr / 20.0)
    logging.debug("snr , snr_linear: %f, %f" % (snr, snr_linear))
    noise_factor = rms_x / rms_z / snr_linear
    logging.debug("y = x  + z * %f" % noise_factor)
    y = x + z * noise_factor
    rms_y = np.sqrt(np.mean(np.power(y, 2)))
    y = y * rms_x / rms_y

    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_addedNoise%s.wav" % str(snr))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(y)

def convolve(infile, ir_name, level = 0.5):
    """ Apply convolution to infile using impulse response given

    Args:
        infile (str): Filename
        ir_name can be  'smartphone_mic' or 'classroom'
        level (float) : can be between 0 and 1, default value = 0.5
    """
    loader1 = es.MonoLoader(filename = infile)
    x = loader1()
    logging.info('Convolving with %s and level %f' % (ir_name, level))
    x = np.copy(x)
    #Change the path below for the sounds folder
    ir_path = './sounds/ir_{0}.wav'.format(ir_name)
    loader2 = es.MonoLoader(filename = ir_path)
    ir = loader2()
    y = np.convolve(x, ir, 'full')[0:x.shape[0]] * level + x * (1 - level)

    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_convolved%s.wav" % str(level))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(y)

def apply_gain(infile, gain):
    """ Apply gain to infile

    Args:
        infile (str): Filename
        gain (float) : gain in dB (both positive and negative)
    """
    loader = es.MonoLoader(filename = infile)
    x = loader()
    logging.info("Apply gain %f dB" % gain)
    x = np.copy(x)
    x = x * (10 ** (gain / 20.0))
    x = np.minimum(np.maximum(-1.0, x), 1.0)
    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_gain%s.wav" % str(gain))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(x)

def apply_rubberband(infile, time_stretching_ratio=1.0, pitch_shifting_ratio=1.0):
    """ Use rubberband tool to apply time stretching and pitch shifting

    Args:
        infile (str): Filename
        time_stretching_ratio (float): Ratio of time stretching
        pitch_shifting_ratio (float): Ratio of pitch shifting

        Ratios can be from -9.99 to 9.99
    """
    loader1 = es.MonoLoader(filename = infile)
    x = loader1()
    logging.info("Applying rubberband. ts_ratio={0}, ps_ratio={1}".format(
        time_stretching_ratio,
        pitch_shifting_ratio))
    tmp_file_1 = tmp_path()
    tmp_file_2 = tmp_path()
    writer = es.MonoWriter(filename = tmp_file_1)
    writer(x)
    cmd = "rubberband -c 1 -t {0} -f {1} {2} {3}".format(
        time_stretching_ratio,
        pitch_shifting_ratio,
        tmp_file_1,
        tmp_file_2)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"
    loader2 = es.MonoLoader(filename = tmp_file_2)
    y = loader2()
    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_timestr%s_pitchshift%s.wav" % (str(time_stretching_ratio),str(pitch_shifting_ratio)))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(y)

def apply_dr_compression(infile, degree):
    """ Apply dynamic range compression using SOX

    Args:
        infile (str): Filename
        degree (int): Can be only 1, 2, 3
    """
    loader1 = es.MonoLoader(filename = infile)
    x = loader1()
    tmpfile_1 = tmp_path('.wav')
    tmpfile_2 = tmp_path('.wav')
    writer = es.MonoWriter(filename = tmpfile_1)
    writer(x)
    if degree == 1:
        cmd = "sox {0} {1} compand 0.01,0.20 -40,-10,-30 5"
    elif degree == 2:
        cmd = "sox {0} {1} compand 0.01,0.20 -50,-50,-40,-30,-40,-10,-30 12"
    elif degree == 3:
        cmd = "sox {0} {1} compand 0.01,0.1 -70,-60,-70,-30,-70,0,-70 45"
    cmd = cmd.format(tmpfile_1, tmpfile_2)
    logging.info(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"
    loader2 = es.MonoLoader(filename = tmpfile_2)
    y = loader2()
    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_drCompression%s.wav" % str(degree))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(y)

def apply_eq(infile, value):
    """ Applying equalizer effects using SOX

    Args:
        infile (str): Filename
        value (three ';' separated values): freq_hz;bw_hz;gain_db (frequency/bandwidth/gain)
        
    From the SOX documentation (http://sox.sourceforge.net/sox.html) :
    Apply a two-pole peaking equalisation (EQ) filter. With this filter, the signal-level at and around 
    a selected frequency can be increased or decreased, whilst (unlike band-pass and band-reject filters) 
    that at all other frequencies is unchanged.
    Frequency gives the filter's central frequency in Hz, width the band-width, and gain the required gain or attenuation in dB
    Beware of Clipping when using a positive gain
    """

    loader1 = es.MonoLoader(filename = infile)
    x = loader1()
    freq, bw, gain = map(int, value.split(';'))
    logging.info("Equalizing. f=%f, bw=%f, gain=%f" % (freq, bw, gain))
    tmpfile_1 = tmp_path('.wav')
    tmpfile_2 = tmp_path('.wav')
    writer = es.MonoWriter(filename = tmpfile_1)
    writer(x)
    cmd = "sox {0} {1} equalizer {2} {3} {4}".format(
        tmpfile_1,
        tmpfile_2,
        freq,
        bw,
        gain)
    logging.info(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        print "ERROR!"
    loader2 = es.MonoLoader(filename = tmpfile_2)
    y = loader2()
    #Change the output file name to suit your requirements here
    outfile_name = infile.split(".")[0] + ("_eq%s.wav" % str(value))
    #outfile = os.path.join(outfile_path, outfile_name)
    writer = es.MonoWriter(filename = outfile_name)
    writer(y)

