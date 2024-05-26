import getpass
import subprocess
import atexit
import os
import docker
import time
import sys
import warnings
# api for launching UE4/5 binary


class RunUnreal():
    def __init__(self, ENV_BIN, ENV_MAP=None):
        if os.path.isabs(ENV_BIN):
            self.path2binary = os.path.abspath(ENV_BIN)
            self.path2env, self.env_bin = self.parse_path(ENV_BIN)
        else:
            self.path2env = self.get_path2UnrealEnv()  # get the path to UnrealEnv in gym-unrealcv
            self.env_bin = ENV_BIN
            self.path2binary = os.path.abspath(os.path.join(self.path2env, self.env_bin))
        self.env_map = ENV_MAP

        self.path2unrealcv = os.path.join(os.path.split(self.path2binary)[0], 'unrealcv.ini')
        assert os.path.exists(self.path2binary), \
            'Please load env binary in UnrealEnv and Check the env_bin in setting file!'

    def start(self, docker=False, resolution=(160, 160), display=None, opengl=False, offscreen=False,
              nullrhi=False, gpu_id=None, local_host=True, sleep_time=5):
        port = self.read_port()
        self.write_resolution(resolution)
        self.use_docker = docker

        if display is not None:
            display = {
                "DISPLAY": display}  # specify display "hostname:displaynumber.screennumber", E.G. "localhost:1.0"
        else:
            display = None  # use default display

        if local_host:
            env_ip = '127.0.0.1'
            while not self.isPortFree(env_ip, port):
                port += 1
                self.write_port(port)

        if self.use_docker:
            self.docker = RunDocker(self.path2env)
            options = self.set_ue_options([], opengl, offscreen, nullrhi, gpu_id)
            env_ip = self.docker.start(ENV_BIN=self.env_bin, options=' '.join(options), host_net=local_host)  # use local host ip
            print('Running nvidia-docker env')
        else:
            #self.modify_permission(self.path2env)
            cmd_exe = [os.path.abspath(self.path2binary)]
            self.set_ue_options(cmd_exe, opengl, offscreen, nullrhi, gpu_id)

            self.env = subprocess.Popen(cmd_exe, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, start_new_session=True, env=display)
            atexit.register(self.close)
            # signal.signal(signal.SIGTERM, self.signal_handler)
            # signal.signal(signal.SIGINT, self.signal_handler)
            print('Running docker-free env, pid:{}'.format(self.env.pid))

        print('Please wait for a while to launch env......')
        time.sleep(sleep_time)
        return env_ip, port

    def set_ue_options(self, cmd_exe=[], opengl=False, offscreen=False, nullrhi=False, gpu_id=None):
        "some options for running UE env"
        if self.env_map is not None:
            cmd_exe.append(self.env_map)
        if opengl:
            cmd_exe.append('-opengl')  # use opengl rendering
        if offscreen:
            cmd_exe.append('-RenderOffScreen')
        if nullrhi:
            cmd_exe.append('-nullrhi')  # the rendering process is not launched, so we can not get the image
        if gpu_id is not None:  # specify which gpu to use, if you have multiple gpus
            cmd_exe.append(f'-graphicsadapter={gpu_id}')
        return cmd_exe

    def get_path2UnrealEnv(self):  # get path to UnrealEnv
        import gym_unrealcv
        gympath = os.path.dirname(gym_unrealcv.__file__)
        return os.path.join(gympath, 'envs', 'UnrealEnv')

    def parse_path(self, path):
        # parse the path to get the root path and the relative path to binary
        part_path = path.split(os.sep)
        id_binaries = part_path.index('Binaries')
        if not part_path[0].startswith('/'):
            part_path[0] = '/' + part_path[0]
        root_path = os.path.join(*part_path[:id_binaries-2])
        binary_path = os.path.join(*part_path[id_binaries-2:])
        return root_path, binary_path

    def close(self):  # close env
        if self.use_docker:
            self.docker.close()
        else:
            self.env.terminate()
            self.env.wait()

    def signal_handler(self, signum, frame):
        self.close()

    def modify_permission(self, path):
        cmd = 'sudo chown {USER} {ENV_PATH} -R'
        username = getpass.getuser()
        os.system(cmd.format(USER=username, ENV_PATH=path))

    def read_port(self):  # read port number from unrealcv.ini
        if os.path.exists(self.path2unrealcv):  # check unrealcv.ini exist
            with open(self.path2unrealcv, 'r') as f:
                s = f.read()  # read unrealcv.ini
                ss = s.split()
            return int(ss[1][-4:])  # return port number
        else:
            return 9000 # default port number

    def write_port(self, port):  # write port number to unrealcv.ini
        with open(self.path2unrealcv, 'r') as f:
            s = f.read()
            ss = s.split('\n')
        with open(self.path2unrealcv, 'w') as f:
            print(ss[1])
            ss[1] = 'Port={port}'.format(port=port)
            d = '\n'
            s_new = d.join(ss)
            f.write(s_new)

    def write_resolution(self, resolution):  # set unrealcv camera resolution by writing unrealcv.ini
        if os.path.exists(self.path2unrealcv):
            with open(self.path2unrealcv, 'r') as f:
                s = f.read()
                ss = s.split('\n')
            with open(self.path2unrealcv, 'w') as f:
                ss[2] = 'Width={width}'.format(width=resolution[0])
                ss[3] = 'Height={height}'.format(height=resolution[1])
                d = '\n'
                s_new = d.join(ss)
                f.write(s_new)

    def isPortFree(self, ip, port):  # check port is free
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if 'linux' in sys.platform:
                sock.bind((ip, port))
            elif 'win' in sys.platform:
                sock.bind((ip, port))
                sock.connect((ip, port))
        except Exception as e:
            sock.close()
            return False
        sock.close()
        return True

# run binary in docker
class RunDocker():
    def __init__(self, path2env, image='zfw1226/unreal:latest'):
       self.docker_client = docker.from_env()
       self.check_image(target_images=image)
       os.system('xhost +')
       self.image = image
       self.path2env = path2env

    def start(self,
              ENV_BIN = '/RealisticRendering_RL/RealisticRendering/Binaries/Linux/RealisticRendering',
              ENV_DIR_DOCKER='/UnrealEnv',
              options='',
              host_net=False
              ):
        path2binary = os.path.join(self.path2env, ENV_BIN)
        print(path2binary)
        if not os.path.exists(path2binary):
            warnings.warn('Did not find unreal environment, Please move your binary file to env/UnrealEnv')
            sys.exit()

        client = docker.from_env()
        # network_settings = self.container.attrs['NetworkSettings']
        volumes = f'-v {self.path2env}:{ENV_DIR_DOCKER}:rw'

        ENV_DIR_BIN_DOCKER = os.path.join(ENV_DIR_DOCKER, ENV_BIN)
        exe_cmd = ENV_DIR_BIN_DOCKER + ' ' + options
        run_cmd = f'/bin/bash -c \"su user -c \'{exe_cmd}\'\"'

        docker_cmd = 'docker run --gpus all  -e DISPLAY=$DISPLAY -e SDL_VIDEODRIVER=x11' \
                     ' -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v /usr/share/vulkan/icd.d:/usr/share/vulkan/icd.d ' \
                     '-e QT_X11_NO_MITSHM=1 -e NVIDIA_DRIVER_CAPABILITIES=all --privileged -d -it'
        if host_net:
            docker_cmd += ' --net=host'
        cmd = docker_cmd + ' ' + volumes + ' ' + self.image + ' ' + run_cmd

        print(cmd)
        os.system(cmd)
        self.container = self.docker_client.containers.list()[0]

        return self.get_ip()

    def get_ip(self):
        # return '127.0.0.1'
        print(self.container.attrs['NetworkSettings']['IPAddress'])
        return self.container.attrs['NetworkSettings']['IPAddress']

    def get_path2UnrealEnv(self):
        import gym_unrealcv
        gympath = os.path.dirname(gym_unrealcv.__file__)
        return os.path.join(gympath, 'envs/UnrealEnv')

    def close(self):
        self.container.remove(force=True)

    def check_image(self, target_images='zfw1226/unreal:latest'):
        # Check the existence of image
        images = self.docker_client.images.list()
        found_img = False
        for i in range(len(images)):
            if images[i].tags.count(target_images) > 0:
                found_img = True
        # Download image
        if found_img == False:
            warnings.warn('Do not found images, Downloading')
            self.docker_client.images.pull(target_images)
        else:
            print('Found images')





