# -*- coding: utf-8 -*-
"""
Created on Thu Sep 30 10:00:28 2021

@author: Gabriel

A script to talk to the Singlet AWG used for the AOM of the Rydberg excitation (borrowed from Heidelberg and from 
th website https://siglentna.com/application-note/programming-example-create-a-stair-step-waveform-using-python-and-pyvisa-using-lan-sdg1000x-sdg2000x-sdg6000x/).

Uses any of the 2 channels (C1 or C2, depending on index_channel).

Encoding of the Siglent AWG: Little endian, n-bit 2's complement
with n = 16 bit for SDG6000X and SDG2000X, and n = 14 bit data for SDG1000X

Note: here the AWG is set to the 'BURST' mode, which means that it should be triggered by an external signal (TTL).
"""
 
#import visa
import pyvisa as visa
#import time
import binascii
import numpy as np
import matplotlib.pyplot as plt

 
#Encoding of the Siglent AWG: Little endian, n-bit 2's complement
#with n = 16 bit for SDG6000X and SDG2000X, and n = 14 bit data for SDG1000X
n = 16 # number of bits for the encoding
LSB = -2**(n-1) # Least Significant Bit
MSB = 2**(n-1)-1 # Most Significant Bit
arb_mode = 'TARB' # arbitrary mode: 'DDS' for Direct RuntimeDevice Synthetizer or 'TARB' for True Arbitrary
sampling_rate = 2400 # sampling rate of the AWG (in MSa/s)
#Note: - in DDS mode, the sampling rate is only indicative, the real sampling rate being chosen by the AWG
#        (typically 1.2 GSa/s but it can be less if the number of samples is higher than 30000)
#      - in TARB mode, the sampling rate is the one set by the user, but it can only go up to 300 MSa/s
if arb_mode == 'TARB' and sampling_rate > 300:
    sampling_rate = 300
#    raise ValueError('In TARB mode, the sampling rate should be between 1µSa/s and 300Sa/s and it is now %.0f MSa/s' %(sampling_rate))

#==============================================================================
# ARBITRARY DATA (ANY SIGNAL YOU WANT)
#==============================================================================
name_data = "test_waveform" # name of the waveform
file_data = ".//" + name_data + ".bin" # name of the file where the waveform will be saved (must be a .bin file)

t_max = 1000.0 # duration of the waveform (µs)
#n_samples = int(max(192,np.round(t_max*sampling_rate/16)*16)) # ensure that the number of samples is >192 and a multiple of 16
n_samples = int(t_max*sampling_rate)
print("Number of samples in one pattern: ", n_samples)
#if arb_mode == 'DDS' and n_samples > 30000:
#    raise ValueError('In DDS mode, the number of samples should be smaller than 30000 but it is %.0f' %(n_samples))

time_list = np.linspace(0,t_max,n_samples) # list of times (µs)

A = 2.0 # half peak-to-peak amplitude (V)
V0 = 0.0 # offset (V)
f = 50.0 # frequency (MHz)
#data = A*np.sin(2*np.pi*f*time_list)*np.exp(-1*time_list/t_max) + V0 # voltage that we want to send to the AWG
data = A*np.sin(2*np.pi*f*time_list) # voltage that we want to send to the AWG

#time_list = np.linspace(0.0, t_max, n_samples)
#alpha = -0.1
#beta = 0.2/t_max
#data = alpha + beta*time_list

#time_list = np.linspace(0.0, t_max, n_samples)
#alpha = 0.1
#data = alpha * (np.array([i%2 for i in range(n_samples)])-0.5)


# =============================================================================
# PLOT THE DESIRED WAVEFORM
# =============================================================================
plt.figure()
plt.title('Initial waveform')
plt.plot(time_list, data,
         marker='o',markersize=1,markerfacecolor='b',markeredgecolor='b',
         linestyle='-',color='b',linewidth=0.5,
         label=r'data')
plt.xlabel(r'Time (µs)')
plt.ylabel(r'Voltage (V)')
plt.tight_layout() # to prevent from cropping the edges of the plot. If it does not work, try to add bbox_inches='tight' in plt.savefig
#plt.xlim([0.0, 10/f])
plt.grid()

# =============================================================================
# BASIC FUNCTIONS FOR THE AWG
# =============================================================================
def get_name_AWG(dev):
    '''resets the default parameters of the AWG'''
    
    dev.write('*IDN?')
    name_awg = dev.read()
    
    return name_awg

def reset_AWG(dev, index_channel):
    '''resets the default parameters of the AWG'''
    
    #reset instrument
    dev.write('*RST')                            # resets the parameters to the default mode
    dev.write('*CLS')                            # clears the data in memory
    dev.write('C'+index_channel+':OUTP ON')      # switches on channel 1 (if not done)
    dev.write('C'+index_channel+':OUTP LOAD,50') # sets the output load ('50' for 50 Ohms, 'HZ' for high impedance)

def send_sine_wave (dev, index_channel, steady_state_amp, steady_state_freq):
    '''
    Set the AWG to the usual setting (steady state parameters)
    - steady_state_amp is the peak-to-peak amplitude of the AWG (in V)
    - steady_state_freq is the frequency (in MHz)
    '''
    
    dev.write('C'+index_channel+':OUTP ON')                                    # switches on channel 1 (if not done)
    dev.write('C'+index_channel+':BSWV WVTP, SINE')                            # puts the wavetype to a sine
    dev.write('C'+index_channel+':BSWV AMP, ' + str(steady_state_amp))          # updates the amplitude of channel 1 to the wanted value (in V)
    dev.write('C'+index_channel+':BSWV FRQ, '+ str(steady_state_freq)+'e6')     # updates the frequency of channel 1 to the wanted value (in Hz)
    dev.write('C'+index_channel+':BSWV OFST, 0')                               # updates the offset of channel 1 to 0 V
    dev.write('C'+index_channel+':BSWV PHSE, 0')                               # updates the phase of channel 1 to 0 degrees


#==============================================================================
# CHANGING THE ENCODING OF THE DATA AND SENDING IT TO THE AWG
#==============================================================================
def create_wave_file(raw_data, file_waveform):
    """
    take in argument the waveform in 'raw_data', changes its encoding
    and create a file 'file_waveform' where the new-encoded waveform is saved (must be a .bin file)
    return the amplitude, offset and frequency of the AWG
    """
    Vmax = np.max(raw_data)
    Vmin = np.min(raw_data)
    amplitude_AWG = Vmax - Vmin
    offset_AWG = (Vmax + Vmin) / 2
    frequency_AWG = 1e6 / (time_list[-1] - time_list[0])
    
    wave_data = (MSB - LSB) * (raw_data - offset_AWG) / amplitude_AWG # homothety of the wanted voltage to match the range of readable values of the AWG
    wave_data = np.round(wave_data) # converting to integers
    wave_data = np.clip(wave_data, LSB, MSB) # making sure that the extreme values are MSB and LSB
    wave_data = wave_data.astype(np.uint16) # converting to hexadecimal encoding (big-endian)
    
    f = open(file_waveform, "wb")
    for a in wave_data:
        b = hex(a)    # change decimal integer a to hexadecimal integer b
        b = b[2:]    # removing the '0x' at the beginning of b
        len_b = len(b)
        if (0 == len_b):
            b = '0000'
        elif (1 == len_b):
            b = '000' + b
        elif (2 == len_b):
            b = '00' + b
        elif (3 == len_b):
            b = '0' + b
        b = b[2:4] + b[:2] # change big-endian to little-endian
        c = binascii.unhexlify(b)    # change hexadecimal integer b to ASCii encoded string c
        f.write(c)
    f.close()
    
    return amplitude_AWG, offset_AWG, frequency_AWG

 
def send_wave_data(dev, index_channel, arb_mode, file_waveform, amplitude_AWG, offset_AWG, frequency_AWG):
    """
    send the waveform in the file 'file_waveform' to the AWG 'dev'
    using the wanted amplitude, offset and frequency
    
    arb_mode is the mode of the AWG:
        'DDS' for Direct RuntimeDevice Synthetizer (automatic choice of the sampling rate, high bandwidth but risk of jitter)
        'TARB' for True Arbitrary waveform (the sampling rate is a parameter, but it cannot go higher than 3MSa/s)
        
    index_channel is the index of the output channel: '1' or '2'
    """
    
    dev.write('C'+index_channel+':OUTP ON')              # switches on channel 1 (if not done)
    dev.write('C'+index_channel+':BursTWaVe STATE,ON')   # puts the AWG in 'Burst' mode
    dev.write('C'+index_channel+':BursTWaVe TRSR,EXT')   # puts the trigger in external mode (trig by a TTL signal on the 'AUX IN/OUT' port)
    dev.write('C'+index_channel+':SRATE MODE,'+arb_mode) # sets the arbitrary waveform mode
    if arb_mode == 'TARB': # if True Arbitrary, we set the sampling rate
        dev.write('C'+index_channel+':SRATE VALUE,'+str(sampling_rate*1e3)+',INTER,LINE') # set the sampling rate and the interpolation to be linear
    
    f = open(file_waveform, "rb")
    data = f.read().decode("latin1") # waveform to be sent
    dev.write_termination = ''
    dev.write("C"+index_channel+":WVDT WVNM,%s,FREQ,%s,AMPL,%s,OFST,%s,PHASE,0.0,WAVEDATA,%s,TRSR,MAN"%(name_data, frequency_AWG, amplitude_AWG, offset_AWG*2, data),encoding='latin1')    #"X" series (SDG1000X/SDG2000X/SDG6000X/X-E)&amp;amp;lt;/pre&amp;amp;gt;
    dev.write("C"+index_channel+":ARWV NAME,%s"%(name_data))
    f.close()
    
    dev.write("C"+index_channel+":SRATE?")
    SR = dev.read()
    print("SR = ", SR)
    
    return data

  
def get_waveform(file_waveform, amplitude_AWG, offset_AWG, frequency_AWG):
    """
    get the waveform from the filename 'file_waveform' (must be a .bin file)
    and convert it into an array of floats
    """
    
    f = open(file_waveform, "rb")
    wave_data = f.read() # waveform to be decoded
    f.close()
    
    N_pts = len(wave_data)//2 # number of points of the waveform
    wave_data_decoded = np.zeros(N_pts)
    
    for i in range(N_pts):
        c_bis = wave_data[2*i:2*(i+1)]
        b_bis = binascii.hexlify(c_bis) # from ASCii encoded string c_bis to bytes-encoded hexadecimal integer b_bis
        b_bis = b_bis.decode("utf-8") # from bytes-encoded to string-encoded
        b_bis = b_bis[2:4] + b_bis[:2] # change little-endian to big-endian
        a_bis = int(float.fromhex('0x'+b_bis)) # from string-encoded hexadecimal integer b_bis to decimal integer a_bis
        
        wave_data_decoded[i] = a_bis
        
    # put back signed integers
    neg_ind = wave_data_decoded > MSB # indices where the values should be negative
    wave_data_decoded[neg_ind] = wave_data_decoded[neg_ind] - 2**n
    
    wave_data_decoded = wave_data_decoded.astype(np.float64) # from uint16 to float64 encoding
        
    raw_data_decoded = offset_AWG + wave_data_decoded * amplitude_AWG / (MSB - LSB) # back to V
    
    return raw_data_decoded


if __name__ == '__main__':
    
    rm = visa.ResourceManager() # the visa object of resource manager
    
    list_resources = rm.list_resources() # list all visa addresses
    device_resource = list_resources[0] # 'USB0::0xF4EC::0x1101::SDG6XEBC6R0173::INSTR' # visa address of the device that we want to connect to
    index_channel = '1' # index of the output channel: '1' or '2'
    
    device = rm.open_resource(device_resource, timeout=50000, chunk_size = 24*1024*1024) # open device
#    reset_AWG(device, index_channel) # reset the default paraeters for the AWG
    print("Name of the AWG = ", get_name_AWG(device))
    
#    # TO SEND A SINE WAVE
#    steady_state_amp = 1.0 # V
#    steady_state_freq = 1.0 # MHz
#    send_sine_wave (device, index_channel, steady_state_amp, steady_state_freq)
    
    # TO SEND AN ARBITRARY WAVEFORM
    amp_AWG, offs_AWG, freq_AWG = create_wave_file(data, file_data) # create waveform
    send = send_wave_data (device, index_channel, arb_mode, file_data, amp_AWG, offs_AWG, freq_AWG) # send waveform to the device
    
    # TO PLOT THE WAVEFORM
    data_decoded = get_waveform (file_data, amp_AWG, offs_AWG, freq_AWG)
    plt.figure()
    plt.title('Decoded waveform')
    plt.plot(time_list, data_decoded,
             marker='o',markersize=1,markerfacecolor='b',markeredgecolor='b',
             linestyle='-',color='b',linewidth=0.5,
             label=r'data')
    plt.xlabel(r'Time (µs)')
    plt.ylabel(r'Voltage (V)')
    plt.tight_layout() # to prevent from cropping the edges of the plot. If it does not work, try to add bbox_inches='tight' in plt.savefig
#    plt.xlim([0.0, 10/f])
    plt.grid()
    
    device.close() # close the AWG at the end
