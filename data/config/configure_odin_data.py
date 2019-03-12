from odin_data.ipc_channel import IpcChannel, IpcChannelException
from odin_data.ipc_message import IpcMessage, IpcMessageException

import argparse
import json
import logging
import sys
import os
from distutils.command.config import config

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

class OdinDataClient(object):
    
    MESSAGE_ID_MAX = 2**32

    def __init__(self, args=None, prog_name=None, logger=None):

        if prog_name is None:
            prog_name = os.path.basename(sys.argv[0])
        
        # Parse command line arguments
        self.args = self._parse_arguments(prog_name, args)
        
        # Create logger if not specified
        if logger is None:
            
            self.logger = logging.getLogger(prog_name)
            self.logger.setLevel(logging.DEBUG)
            
            # create console handler and set level to debug
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            
            # create formatter
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
            
            # add formatter to ch
            ch.setFormatter(formatter)
            
            # add ch to logger
            self.logger.addHandler(ch)

        else:
            self.logger = logger
    
        # Create the appropriate IPC channels
        self.fr_ctrl_channel = IpcChannel(IpcChannel.CHANNEL_TYPE_DEALER)
        self.fr_ctrl_channel.connect(self.args.fr_ctrl_endpoint)
        self.fp_ctrl_channel = IpcChannel(IpcChannel.CHANNEL_TYPE_DEALER)
        self.fp_ctrl_channel.connect(self.args.fp_ctrl_endpoint)
        
        self.channels = [('receiver', self.fr_ctrl_channel), ('processor', self.fp_ctrl_channel)]
        
        # Create empty receiver and processor configuration parameter dicts
        self.fr_config = {}
        self.fp_config = {}
        self.fp_plugins = []

        # Set default number of frames, file path and name
        self.frames = 1
        self.file_path = '/tmp'
        self.file_name = 'test.hdf5'
        
        # Internal IpcMessage ID counter
        self._msg_id = 0
        
    def _next_msg_id(self):
        
        self._msg_id = (self._msg_id + 1) % self.MESSAGE_ID_MAX
        return self._msg_id
        
    def run(self):
        
        self.logger.info("Odin data client starting up")
        
        self.logger.debug("Frame receiver control IPC channel has identity {}".format(self.fr_ctrl_channel.identity))
        self.logger.debug("Frame processor control IPC channel has identity {}".format(self.fp_ctrl_channel.identity))
        
        if self.args.config_file is not None:
            self.load_config(self.args.config_file)

        if self.args.frames:
            self.set_num_frames(self.args.frames)
            
        if self.args.bitdepth:
            self.set_bitdepth(self.args.bitdepth)
            
        if self.args.file_path:
            self.set_file_path(self.args.file_path)
            
        if self.args.file_name:
            self.set_file_name(self.args.file_name)
        
        if self.args.config:
            self.do_config_cmd()
        
        if self.args.start:
            self.set_file_writing(True)
        elif self.args.stop:
            self.set_file_writing(False)
            
        if self.args.status:
            self.do_status_cmd()
            
        if self.args.getconfig:
            self.do_request_config_cmd()

        if self.args.shutdown:
            self.do_shutdown_cmd()
    
    def load_config(self, config_file):
        
        self.logger.debug("Parsing default configuration from file {}".format(config_file.name))
        try:
            config_params = json.load(config_file)

            if 'receiver_default_config' in config_params:
                self.fr_config = config_params['receiver_default_config']
                
            if 'processor_default_config' in config_params:
                self.fp_config = config_params['processor_default_config']
                
            if 'processor_plugins' in config_params:
                self.fp_plugins = config_params['processor_plugins']
                
        except JSONDecodeError as e:
            self.logger.error("Failed to parse configuration file: {}".format(e))
            
    def _ensure_config_section(self, config, section):
        
        if section not in config:
            config[section] = {}
            self.logger.debug("Created {} section in config params".format(section))
            
    def set_num_frames(self, frames):
        
        self.frames = frames
        
        self._ensure_config_section(self.fp_config, 'hdf')            
        self.fp_config['hdf']['frames'] = frames
        
    def set_file_path(self, file_path):
        
        self.file_path = file_path
        
        self._ensure_config_section(self.fp_config, 'hdf')
        self._ensure_config_section(self.fp_config['hdf'], 'file')
        self.fp_config['hdf']['file']['path'] = file_path
        
    def set_file_name(self, file_name):
        
        self.file_name = file_name
        
        self._ensure_config_section(self.fp_config, 'hdf')
        self._ensure_config_section(self.fp_config['hdf'], 'file')
        self.fp_config['hdf']['file']['name'] = file_name

    def set_bitdepth(self, bitdepth):
        
        bitdepth_str = '{:d}-bit'.format(bitdepth)
        
        self._ensure_config_section(self.fr_config, 'decoder_config')           
        self.fr_config['decoder_config']['bitdepth'] = bitdepth_str

        self._ensure_config_section(self.fp_config, 'excalibur')                       
        self.fp_config['excalibur']['bitdepth'] = bitdepth_str
        
        rdtype_map = {
            1:  0,
            6:  0,
            12: 1,
            24: 2,
        }
        rdtype = rdtype_map[bitdepth]
        
        self._ensure_config_section(self.fp_config, 'hdf')
        self._ensure_config_section(self.fp_config['hdf'], 'dataset')
        self._ensure_config_section(self.fp_config['hdf']['dataset'], 'data')
        self.fp_config['hdf']['dataset']['data']['datatype'] = rdtype
        
        #print(self.fp_config)
 
    def do_config_cmd(self):
        
        self.logger.info("Sending configuration command to frame receiver")
        self.send_config_cmd(self.fr_ctrl_channel, self.fr_config)
        
        if 'fr_setup' in self.fp_config:
            self.logger.info("Sending receiver plugin configuration command to frame processor")
            params = {'fr_setup' : self.fp_config['fr_setup']}
            self.send_config_cmd(self.fp_ctrl_channel, params)
            
        if len(self.fp_plugins):

            self.logger.info(
                "Sending {} plugin chain configuration commands to frame processor".format(
                len(self.fp_plugins)))
            for plugin in self.fp_plugins:
                self.send_config_cmd(self.fp_ctrl_channel, plugin)
                
        self.logger.info("Sending plugin parameter configuration command to frame processor")
        self.send_config_cmd(self.fp_ctrl_channel, self.fp_config)
                    
    def send_config_cmd(self, channel, params):
                
        config_msg = IpcMessage('cmd', 'configure', id=self._next_msg_id())
        config_msg.attrs['params'] = params
        channel.send(config_msg.encode())
        self.await_response(channel)
         
    def set_file_writing(self, enable):

        self.set_file_name(self.file_name)
        self.set_file_path(self.file_path)
        self.set_num_frames(self.frames)

        self.fp_config['hdf']['frames'] = self.frames
        self.fp_config['hdf']['write'] = enable

        # write_config = {}
        # if enable:
        #     write_config['file'] = {
        #                 "path": self.file_path,
        #                 "name": self.file_name,
        #             }
        #     write_config["frames"] =  self.frames

        # write_config["write"] = enable

        config_msg = IpcMessage('cmd', 'configure', id=self._next_msg_id())
        #config_msg.set_param('hdf', write_config)
        config_msg.attrs['params'] = {'hdf': self.fp_config['hdf']}

        print(config_msg)

        self.logger.info('Sending file writing {} command to frame processor'.format(
            'enable' if enable else 'disable'))
        
        self.fp_ctrl_channel.send(config_msg.encode())
        self.await_response(self.fp_ctrl_channel)
        
    def do_status_cmd(self):

        for (name, channel) in self.channels:
            self.logger.info("Sending status request to frame {}".format(name))
            reply = self.send_status_cmd(channel)
            if reply is not None:
                self.logger.info("Got response: {}".format(reply))

    def send_status_cmd(self, channel):
        
        status_msg =  IpcMessage('cmd', 'status', id=self._next_msg_id())
        channel.send(status_msg.encode())
        reply = self.await_response(channel)

        return reply
    
    def do_request_config_cmd(self):
        
        request_msg = IpcMessage('cmd', 'request_configuration', id=self._next_msg_id())
        
        for (name, channel) in self.channels:                        
            self.logger.info("Sending configuration request for frame {}".format(name))
            channel.send(request_msg.encode())
            reply = self.await_response(channel)
            if reply is not None:
                self.logger.info("Got response: {}".format(reply))
            
    def await_response(self, channel, timeout_ms=1000):

        reply = None
        pollevts = channel.poll(1000)
        if pollevts == IpcChannel.POLLIN:
            reply = IpcMessage(from_str=channel.recv())
        
        return reply
               
    def _parse_arguments(self, prog_name=sys.argv[0], args=None):
        
        parser = argparse.ArgumentParser(prog=prog_name, description='ODIN data client')
        parser.add_argument('--frctrl', type=str, default='tcp://127.0.0.1:5000', 
                            dest='fr_ctrl_endpoint',
                            help='Specify the frame recevier IPC control channel endpoint URL')
        parser.add_argument('--fpctrl', type=str, default='tcp://127.0.0.1:5004', 
                            dest='fp_ctrl_endpoint',
                            help='Specify the frame processor IPC control channel endpoint URL')
        parser.add_argument('--default', type=argparse.FileType('r'), dest='config_file', nargs='?',
                            default=None, const=sys.stdin, 
                            help='Specify JSON configuration file to parse for default config')
        parser.add_argument('--config', action='store_true',
                            help='Send a configuration command to the processes')
        parser.add_argument('--frames', type=int, dest='frames',
                            help='Override the number of frames in configuration')
        parser.add_argument('--bitdepth', type=int, dest='bitdepth', 
                            choices=[1, 6, 12, 24],
                            help='Override the bit depth param in configuration')
        
        file_writing = parser.add_mutually_exclusive_group()
        file_writing.add_argument('--start', action='store_true',
                            help='Start frame processor file writing')
        file_writing.add_argument('--stop', action='store_true',
                            help='Stop frame processor file writing')
        
        parser.add_argument('--path', type=str, dest='file_path',
                            help='Set file writing path')
        parser.add_argument('--file', type=str, dest='file_name',
                            help='Set file writing name')
        
        parser.add_argument('--status', action='store_true',
                            help='Request a status report from the processes')
        parser.add_argument('--getconfig', action='store_true',
                            help='Get the current configuration of the processes')
        parser.add_argument('--shutdown', action='store_true',
                            help='Instruct the processes to shut down')
        
        args = parser.parse_args(args)
        return args
    
    
def main():
    
    app = OdinDataClient()
    app.run()

if __name__ == '__main__':
    
    main()
    
