#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from psychopy import gui
from psychopy import core, data, visual, event, monitors
from scipy.io.wavfile import write
import random
import glob, os, errno
import csv
import pyaudio
import wave
import pandas as pd


### RECORDING FUNCTION TAKEN FROM https://gist.github.com/sloria

class Recorder(object):
    def __init__(self, channels=1, rate=44100, frames_per_buffer=1024):
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer

    def open(self, fname, mode='wb'):
        return RecordingFile(fname, mode, self.channels, self.rate,
                            self.frames_per_buffer)

class RecordingFile(object):
    def __init__(self, fname, mode, channels,
                rate, frames_per_buffer):
        self.fname = fname
        self.mode = mode
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self.wavefile = self._prepare_file(self.fname, self.mode)
        self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, exception, value, traceback):
        self.close()

    def record(self, duration):
        # Use a stream with no callback function in blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer)
        for _ in range(int(self.rate / self.frames_per_buffer * duration)):
            audio = self._stream.read(self.frames_per_buffer)
            self.wavefile.writeframes(audio)
        return None

    def start_recording(self):
        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer,
                                        stream_callback=self.get_callback())
        self._stream.start_stream()
        return self

    def stop_recording(self):
        self._stream.stop_stream()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            self.wavefile.writeframes(in_data)
            return in_data, pyaudio.paContinue
        return callback


    def close(self):
        self._stream.close()
        self._pa.terminate()
        self.wavefile.close()

    def _prepare_file(self, fname, mode='wb'):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        wavefile.setframerate(self.rate)
        return wavefile

#################
### EXPERIMENT###
#################

def make_sure_path_exists(path):
    try:
        script_path = os.path.dirname(os.path.realpath(__file__))
        if script_path != os.getcwd():
            os.chdir(script_path)
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

myDlg = gui.Dlg(title="Word Probe Experiment")
myDlg.addField('Code:')
myDlg.addField('Age:')
myDlg.addField('Gender:', choices=["Female", "Male","Other"])
ok_data=myDlg.show()
if myDlg.OK:
    print(ok_data)
else:
    print('experiment is cancelled')

participant=ok_data[0]
age=ok_data[1]
gender=ok_data[2]

script_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_path)
test_path = 'test_results/'
make_sure_path_exists(test_path)
audio_path = 'audio_recordings/' + str(participant)
make_sure_path_exists(audio_path)

date = data.getDateStr()
filename = test_path + 'participant_{}_{}_{}_{}.csv'.format(participant,str(date),age,gender)
data_file = open(filename, 'a+')
writer = csv.writer(data_file)
writer.writerow(['trial', 'ITI','word','word timing', 'category','reaction time', 'respiration cycle'])

allow_keys = ['space', 'q']
categories= ['On-task focus --> 1', 'Distraction --> 2', 'Mind-wandering--> 3', 'Mind-blanking--> 4']
response_keys = ['1','2','3','4']
n_trial = 0
ITI=[30,35,40,45,50,55,60,65,70,75,80,85,90]*2
random.shuffle(ITI)
words=[]
stimuli=pd.read_csv("stimuli.csv", header=None, index_col=False)
for i in range(26):
    words.append(stimuli[0][i])
random.shuffle(words)

my_monitor = monitors.Monitor(name = 'mac')
my_monitor.setSizePix((2880,1800)) #1920 x 1080
my_monitor.setWidth(36)
my_monitor.setDistance(57)
my_monitor.saveMon()
win = visual.Window(fullscr=True, monitor=my_monitor, units="cm")
fixation = visual.GratingStim(win, color=1,
                                  tex=None, mask ='cross',
                                  size= 2)


consigne=u'In this experiment, you are asked to count in your head the number of respirations you had. At some point,you are going to see a target word. \n'
consigne += u'You will first tell us the words that the target makes you think of. \n'
consigne += u'You will then tell us your mental state and finally the number of respirations you counted \n'
consigne += u'Press space to start the experiment'
Show_consigne = visual.TextStim(win, text=consigne, height= 1, pos = (0,0))
Show_consigne.draw()
win.flip()
event.waitKeys(keyList= "space")

for dur in range(len(ITI)):
    txt = visual.TextStim(win, text=words[dur].decode('utf-8'), height= 3, units = 'cm', pos=(0,0))
    for i in range(int(ITI[dur] / (1/60))):
        fixation.draw()
        win.flip()
    txt.draw()
    time_audio = core.Clock()
    win.flip()
    audio_file = 'participant{}_trial{}.wav'.format(participant, dur+1)
    rec = Recorder(channels=2)
    with rec.open(audio_file, 'wb') as recfile2:
        recfile2.start_recording()
        rec_dur=event.waitKeys(keyList= "space", timeStamped=time_audio)
        recfile2.stop_recording()
    rec_time = rec_dur[0][1]

    pos_y = 1
    c = u'Which one of the following mental state categories correspond better to your mental state during the probe? \n\n'

    instruction_category = visual.TextStim(win, c, pos = (0, +5), height = 1)
    instruction_category.draw()

    for i in categories:
        thought_cat = visual.TextStim(win, text = i, pos = (0,pos_y), height= 1)
        thought_cat.draw()

        pos_y -= 1.5

    win.flip()
    time_choice = core.Clock()
    choice = event.waitKeys(keyList= response_keys, timeStamped=time_choice)
    category = choice[0][0]
    time_choice = choice[0][1]
    count = visual.TextStim(win, text='How many respiration cycles did you count?', height= 1, pos = (0,0))
    count.draw()
    win.flip()
    cycle = gui.Dlg(title="Respiration cycle")
    cycle.addField('How many respiration cycles did you count?:')
    cycle_nb=cycle.show()
    writer.writerow([dur+1,ITI[dur],words[dur],rec_time,category, time_choice, cycle_nb[0]])

over='The experiment is over, thank you for your participation!'
Show_over = visual.TextStim(win, text=over, height= 1, pos = (0,0))
Show_over.draw()
win.flip()
event.waitKeys(keyList= "space")
win.close()
