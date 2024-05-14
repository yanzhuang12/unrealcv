import time
from unrealcv.api import UnrealCv_API
from unrealcv.launcher import RunUnreal
from unrealcv.util import measure_fps
import argparse
'''
An example to show how to use the UnrealCV API to launch the game and run some functions
'''


def parse_res(res):  # parse the resolution string
    resolution = res.split('x')
    if len(resolution) != 2:
        parser.error('Resolution must be specified as WIDTHxHEIGHT')
    try:
        return (int(resolution[0]), int(resolution[1]))
    except ValueError:
        parser.error('WIDTH and HEIGHT must be integers')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-bin', default='/home/zfw/UnrealEnv/Collection_v4_linux/Collection/Binaries/Linux/Collection', help='The path to the UE4Editor binary')
    parser.add_argument('--env-map', default='Brass_Palace', help='The map to load')
    parser.add_argument('--use-docker', action='store_true', help='Run the game in a docker container')
    parser.add_argument('--resolution', '-res', default='640x480', help='The resolution in the unrealcv.ini file')
    parser.add_argument('--display', default=None, help='The display to use')
    parser.add_argument('--use-opengl', action='store_true', help='Use OpenGL for rendering')
    parser.add_argument('--offscreen', action='store_true', help='Use offscreen rendering')
    parser.add_argument('--nullrhi', action='store_true', help='Use the NullRHI')
    parser.add_argument('--show', action='store_true', help='show the get image result')
    parser.add_argument('--gpu-id', default=0, help='The GPU to use')
    args = parser.parse_args()
    env_bin = args.env_bin
    env_map = args.env_map

    ue_binary = RunUnreal(ENV_BIN=env_bin, ENV_MAP=env_map)
    env_ip, env_port = ue_binary.start(args.use_docker, parse_res(args.resolution), args.display, args.use_opengl, args.offscreen, args.nullrhi, str(args.gpu_id))
    unrealcv = UnrealCv_API(env_port, env_ip, ue_binary.path2env, parse_res(args.resolution), 'tcp')  # 'tcp' or 'unix', 'unix' is only for local machine in Linux
    # unrealcv.config_ue(parse_res(args.resolution))
    # unrealcv.set_map(env_map)

    # Test the API
    print(unrealcv.get_camera_num())
    print(unrealcv.camera_info())
    objects = unrealcv.get_objects()
    print(objects)
    t = time.time()
    unrealcv.build_color_dict(objects, batch=True)
    print(time.time() - t)

    unrealcv.get_obj_bboxes(unrealcv.get_image(1, 'seg'), objects)
    print(unrealcv.get_obj_pose(objects[0]))
    print(unrealcv.get_obj_location(objects[0]))
    print(unrealcv.get_obj_rotation(objects[0]))

    for cam_id in range(unrealcv.get_camera_num()):
        print(unrealcv.get_cam_location(cam_id))
        print(unrealcv.get_cam_rotation(cam_id))
        print(unrealcv.get_cam_pose(cam_id))
        for mode in ['lit', 'normal', 'seg', 'depth']:
            fps = measure_fps(unrealcv.get_image, cam_id, mode, show=args.show)
            print(f'FPS for cam {cam_id}, mode {mode}: {fps}')
    unrealcv.client.disconnect()
    ue_binary.close()

