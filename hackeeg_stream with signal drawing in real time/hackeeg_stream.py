#!/usr/bin/python3

# Notes:
# To capture at 16,000 samples per second,
# the Arduino Due driver's SPI DMA must be on,
# and the driver communication mode must be set to MessagePack
# (--messagepack option)

import argparse
import uuid
import time
import sys
import select

from pylsl import StreamInfo, StreamOutlet

import hackeeg
from hackeeg import ads1299
from hackeeg.driver import SPEEDS, GAINS, Status

import pygame
import pygame.freetype
from pygame.locals import*

from playsound import playsound

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 50000


class HackEegTestApplicationException(Exception):
    pass


class NonBlockingConsole(object):

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def init(self):
        import tty
        import termios

    def get_data(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False


class WindowsNonBlockingConsole(object):
    def init(self):
        import msvcrt

    def get_data(self):
        if msvcrt.kbhit():
            char = msvcrt.getch()
            return char
        return False


class HackEegTestApplication:
    """HackEEG commandline tool."""

    def __init__(self):
        self.serial_port_name = None
        self.hackeeg = None
        self.debug = False
        self.channel_test = False
        self.quiet = False
        self.hex = False
        self.messagepack = False
        self.channels = 8
        self.samples_per_second = 500
        self.gain = 1
        self.max_samples = 5000
        self.lsl = False
        self.lsl_info = None
        self.lsl_outlet = None
        self.lsl_stream_name = "HackEEG"
        self.stream_id = str(uuid.uuid4())
        self.read_samples_continuously = True
        self.continuous_mode = False
        self.file_name = "Data.txt"
        self.SPI_data_file = "DataSPI.txt"
        self.beep = "beep-07a.wav"
        
        self.width=1000
        self.height=500
        self.Color_screen=(255,255,255)
        self.Color_line=(0,0,0)
        self.screen=pygame.display.set_mode((self.width,self.height))
        self.screen.fill(self.Color_screen)
        
        
        pygame.display.flip()
        pygame.display.set_caption('EOD')
        #pygame.draw.line(self.screen,self.Color_line,(60,80),(130,100))
        pygame.display.flip()
        
        
        self.running=False

        print(f"platform: {sys.platform}")
        if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
            self.non_blocking_console = NonBlockingConsole()
        elif sys.platform == "win32":
            self.non_blocking_console = WindowsNonBlockingConsole()
        self.non_blocking_console.init()
        # self.debug = True

    def find_dropped_samples(self, samples, number_of_samples):
        sample_numbers = {self.get_sample_number(sample): 1 for sample in samples}
        correct_sequence = {index: 1 for index in range(0, number_of_samples)}
        missing_samples = [sample_number for sample_number in correct_sequence.keys()
                           if sample_number not in sample_numbers]
        return len(missing_samples)

    def get_sample_number(self, sample):
        sample_number = sample.get('sample_number', -1)
        return sample_number

    def read_keyboard_input(self):
        char = self.non_blocking_console.get_data()
        if char:
            self.read_samples_continuously = False

    def setup(self, samples_per_second=500, gain=1, messagepack=False):
        if samples_per_second not in SPEEDS.keys():
            raise HackEegTestApplicationException("{} is not a valid speed; valid speeds are {}".format(
                samples_per_second, sorted(SPEEDS.keys())))
        if gain not in GAINS.keys():
            raise HackEegTestApplicationException("{} is not a valid gain; valid gains are {}".format(
                gain, sorted(GAINS.keys())))

        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.sdatac()
        self.hackeeg.blink_board_led()
        sample_mode = SPEEDS[samples_per_second] | ads1299.CONFIG1_const
        self.hackeeg.wreg(ads1299.CONFIG1, sample_mode)

        gain_setting = GAINS[gain]

        self.hackeeg.disable_all_channels()
        if self.channel_test:
            self.channel_config_test()
        else:
            self.channel_config_input(gain_setting)


        # Route reference electrode to SRB1: JP8:1-2, JP7:NC (not connected)
        # use this with humans to reduce noise
        ##self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1 | ads1299.MISC1_const)

        # Single-ended mode - setting SRB1 bit sends mid-supply voltage to the N inputs
        # use this with a signal generator
        ##self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1)

        # Dual-ended mode
        self.hackeeg.wreg(ads1299.MISC1, ads1299.MISC1_const)
        # add channels into bias generation
        #self.hackeeg.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)

        if messagepack:
            self.hackeeg.messagepack_mode()
        else:
            self.hackeeg.jsonlines_mode()
        self.hackeeg.start()
        self.hackeeg.rdatac()
        return

    def channel_config_input(self, gain_setting):
        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )

        # self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | gain_setting)
        # self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.INT_TEST_DC | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 8, ads1299.ELECTRODE_INPUT | gain_setting)

    def channel_config_test(self):
        # test_signal_mode = ads1299.INT_TEST_DC | ads1299.CONFIG2_const
        test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
        self.hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.SHORTED | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.MVDD | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.BIAS_DRN | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.BIAS_DRP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.TEMP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
        self.hackeeg.disable_channel(8)

        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )
        pass



    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("serial_port", help="serial port device path",
                            type=str)
        parser.add_argument("--debug", "-d", help="enable debugging output",
                            action="store_true")
        parser.add_argument("--samples", "-S", help="how many samples to capture",
                            default=DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE, type=int)
        parser.add_argument("--continuous", "-C", help="read data continuously (until <return> key is pressed)",
                            action="store_true")
        parser.add_argument("--sps", "-s",
                            help=f"ADS1299 samples per second setting- must be one of {sorted(list(SPEEDS.keys()))}, default is {self.samples_per_second}",
                            default=self.samples_per_second, type=int)
        parser.add_argument("--gain", "-g",
                            help=f"ADS1299 gain setting for all channels– must be one of {sorted(list(GAINS.keys()))}, default is {self.gain}",
                            default=self.gain, type=int)
        parser.add_argument("--lsl", "-L",
                            help=f"Send samples to an LSL stream instead of terminal",
                            action="store_true"),
        parser.add_argument("--lsl-stream-name", "-N",
                            help=f"Name of LSL stream to create",
                            default=self.lsl_stream_name, type=str),
        parser.add_argument("--file-name", "-F",
                            help=f"Name of file where to save data",
                            default=self.file_name, type=str),
        parser.add_argument("--messagepack", "-M",
                            help=f"MessagePack mode– use MessagePack format to send sample data to the host, rather than JSON Lines",
                            action="store_true")
        parser.add_argument("--channel-test", "-T",
                            help=f"set the channels to internal test settings for software testing",
                            action="store_true")
        parser.add_argument("--hex", "-H",
                            help=f"hex mode– output sample data in hexidecimal format for debugging",
                            action="store_true")
        parser.add_argument("--quiet", "-q",
                            help=f"quiet mode– do not print sample data (used for performance testing)",
                            action="store_true")
        args = parser.parse_args()
        if args.debug:
            self.debug = True
            print("debug mode on")
        self.samples_per_second = args.sps
        self.gain = args.gain

        if args.continuous:
            self.continuous_mode = True

        if args.lsl:
            self.lsl = True
            if args.lsl_stream_name:
                self.lsl_stream_name = args.lsl_stream_name
            self.lsl_info = StreamInfo(self.lsl_stream_name, 'EEG', self.channels, self.samples_per_second, 'int32',
                                       self.stream_id)
            self.lsl_outlet = StreamOutlet(self.lsl_info)

        self.serial_port_name = args.serial_port
        self.hackeeg = hackeeg.HackEEGBoard(self.serial_port_name, baudrate=2000000, debug=self.debug)
        self.max_samples = args.samples
        self.channel_test = args.channel_test
        self.quiet = args.quiet
        self.hex = args.hex
        self.messagepack = args.messagepack
        self.file_name = args.file_name
        self.hackeeg.connect()
        self.setup(samples_per_second=self.samples_per_second, gain=self.gain, messagepack=self.messagepack)

    def process_sample(self, result, samples):
        data = None
        channel_data = None
        if result:
            status_code = result.get(self.hackeeg.MpStatusCodeKey)
            data = result.get(self.hackeeg.MpDataKey)
            samples.append(result)
            if status_code == Status.Ok and data:
                if not self.quiet:
                    timestamp = result.get('timestamp')
                    sample_number = result.get('sample_number')
                    ads_gpio = result.get('ads_gpio')
                    loff_statp = result.get('loff_statp')
                    loff_statn = result.get('loff_statn')
                    channel_data = result.get('channel_data')
                    data_hex = result.get('data_hex')
                    if self.hex:
                        print(data_hex)
                    else:
                        for channel_number, sample in enumerate(channel_data):
                            #print(f"{channel_number + 1}:  {sample} ", end='')
                            if channel_number == 0:
                                sample1 = sample
                            if channel_number == 1:
                            	print(f"{sample1 - sample}")
                        print()
                if self.lsl and channel_data:
                    self.lsl_outlet.push_sample(channel_data)
            else:
                if not self.quiet:
                    print(data)
        else:
            print("no data to decode")
            print(f"result: {result}")



    def main(self):
        self.parse_args()

        samples = []
        pred_samples = []
        spi = []
        summ = 0
        s1 = 0
        s2 = 0
        s0 = 0
        s_1 =0
        x = 0
        y = 0
        sample_counter = 0
        signal_counter = 0
        self.running = True

        end_time = time.perf_counter()
        start_time = time.perf_counter()
        signal_time = time.perf_counter()
        
        
        with open(self.file_name, 'w') as f:
            while ((sample_counter < self.max_samples and not self.continuous_mode) or \
                   (self.read_samples_continuously and self.continuous_mode) or self.running):
            	#while (self.running == True):
            	
            	#zavreni grafickeho okna je jednou z podminek pro ukonceni programu
            	#neni osetreno chovani programu pri pridani maximalniho poctu samplu
            	#doporucuju pouzivat continuous mode
            	if self.running: 
            		for event in pygame.event.get():
            			if event.type == pygame.QUIT:
            				self.running = False
            				pygame.display.quit()
            				pygame.quit()
            				#pygame.display.flip()
            				
            	result = self.hackeeg.read_rdatac_response()
            	channel_data = result.get('channel_data')
            	for channel_number, sample in enumerate(channel_data):
            		#print(f"{channel_number + 1}:  {sample} ", end='')
            		if channel_number == 0:
            			#print(f"{sample}", file=f)
            			
            			#Odstraneni chybnych vzorku
            			if sample_counter>3 and ((sample-s0)<700 and (sample-s0)>-700) and ((sample-s_1)<700 and (sample-s_1)>-700):
            				if (s0-s1)>10000 or (s0-s1)<-10000:
            					s1=(s0+sample)/2
            					pred_samples[sample_counter-2]=s1
            			if sample_counter>2:
            				print(f"{s1}", file=f)	
            			s_1=s0
            			s0=s1
            			s1=s2
            			s2=sample
            			pred_samples.append(sample)
            			
            			#Derivace a druha mocnina
            			if sample_counter > 7:
            				x = ((-3) * pred_samples[sample_counter-2] + 4 * pred_samples[sample_counter - 4] - pred_samples[sample_counter - 6]) / 4
            				samples.append(x * x)
            				#print(f"{x}")
            				
            			#Prumerovani
            			if sample_counter > 17:
            				summ = samples[sample_counter - 9]+samples[sample_counter - 10]+samples[sample_counter - 11]+samples[sample_counter - 12]+samples[sample_counter - 13]+samples[sample_counter - 14]+samples[sample_counter - 15]+samples[sample_counter - 16]+samples[sample_counter - 17]+samples[sample_counter - 18]
            				#print(f"{summ/10}")
            				
            				#Detekce, sonifikace, mereni a zapis SPI
            				if (summ/10) > 1500000000 and (summ/10) < 12000000000 and y==0:
            					y=100
            					print(f"WoW {sample_counter}")
            					playsound(self.beep)
            					signal_counter+=1
            					spi.append((time.perf_counter())-signal_time)
            					signal_time = time.perf_counter()
	
            				y-=1
            				
            				#Kresleni detekovanych signalu
            				if (y==0) and (sample_counter>=200) and self.running:
            					a1 = 0
            					maxs = 500000
            					mins = -50000
            					b1 = ((pred_samples[sample_counter-200]-mins)/(maxs-mins))*(-self.height)+self.height
            					self.screen.fill(self.Color_screen)
            					for i in range(1, 200):
            						a=(i*self.width)/200
            						b=((pred_samples[sample_counter-200+i]-mins)/(maxs-mins))*(-self.height)+self.height				
            						pygame.draw.line(self.screen,self.Color_line,(int(a1),int(b1)),(int(a),int(b)))
            						pygame.display.flip()
            						a1=a
            						b1=b
            					
            				if y<0: y=0
            		
            
            	end_time = time.perf_counter()
            	sample_counter += 1
            	if self.continuous_mode:
                	self.read_keyboard_input()
            #self.process_sample(result, samples)
            with open(self.SPI_data_file, 'w') as s:
            	for k in spi:
            		print(f"{k}", file=s)
            duration = end_time - start_time
            self.hackeeg.stop_and_sdatac_messagepack()
            self.hackeeg.blink_board_led()

            print(f"duration in seconds: {duration}")
            samples_per_second = sample_counter / duration
            print(f"samples per second: {samples_per_second}")
            print(f"number of detected EOD: {signal_counter}")
            print(f"EOD per second: {signal_counter / duration}")
            #print(f"{samples_per_second}")
            print(f"{signal_counter}", file=f)
            print(f"{signal_counter / duration}", file=f)
            print(f"{samples_per_second}", file=f)
            #dropped_samples = self.find_dropped_samples(samples, sample_counter)
            #print(f"dropped samples: {dropped_samples}")


if __name__ == "__main__":
    HackEegTestApplication().main()
