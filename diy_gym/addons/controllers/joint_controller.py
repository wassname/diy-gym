import pybullet as p

from gym import spaces
import numpy as np
from diy_gym.addons.addon import Addon


class JointController(Addon):
    """
    JointController

    Desired position or velocity or torque
    """
    def __init__(self, parent, config):
        super(JointController, self).__init__(parent, config)

        self.uid = parent.uid

        self.position_gain = config.get('position_gain', 0.015)
        self.velocity_gain = config.get('velocity_gain', 1.0)

        self.control_mode = {
            'position': p.POSITION_CONTROL,
            'velocity': p.VELOCITY_CONTROL,
            'torque': p.TORQUE_CONTROL
        }[config.get('control_mode', 'velocity')]

        joint_info = [p.getJointInfo(self.uid, i) for i in range(p.getNumJoints(self.uid))]

        if 'joint' in config:
            joints = [config.get('joint')]
        elif 'joints' in config:
            joints = config.get('joints')
        else:
            joints = [info[1].decode('UTF-8') for info in joint_info]

        self.joint_ids = [info[0] for info in joint_info if info[1].decode('UTF-8') in joints and info[3] > -1]
        self.rest_position = config.get('rest_position', [0] * len(self.joint_ids))

        self.torque_limit = np.array([p.getJointInfo(self.uid, joint_id)[10] for joint_id in self.joint_ids])
        self.vel_limit = np.array([p.getJointInfo(self.uid, joint_id)[11] for joint_id in self.joint_ids])
        

        self.joined = config.get('joined', False)

        # # TODO get from upp and lower post in post mode?
        # if self.joined:
        #     max_action = np.array(config.get('max_action', [1]))
        # else:
        #     max_action = np.array(config.get('max_action', [1] * len(self.joint_ids)))

        if self.control_mode == p.TORQUE_CONTROL:
            self.action_space = spaces.Box(-self.torque_limit, self.torque_limit, dtype='float32')
        elif self.control_mode == p.VELOCITY_CONTROL:
            self.action_space = spaces.Box(-self.vel_limit, self.vel_limit, dtype='float32')
        else:
            low = np.array([p.getJointInfo(self.uid, joint_id)[8] for joint_id in self.joint_ids])
            high = np.array([p.getJointInfo(self.uid, joint_id)[9] for joint_id in self.joint_ids])
            self.action_space = spaces.Box(-low, high, shape=(len(low), ), dtype='float32')
        self.torque_limit

        self.random_reset = config.get('reset_range', [0.] * len(self.joint_ids))

    def reset(self):        
        random_delta = np.random.random(len(self.joint_ids)) * self.random_reset
        for joint_id, angle, d_angle in zip(self.joint_ids, self.rest_position, random_delta):
            p.resetJointState(self.uid, joint_id, angle + d_angle)

    def update(self, action):
        if self.joined:
            action = list(action) * len(self.joint_ids)
        kwargs = {}

        if self.control_mode == p.POSITION_CONTROL:
            kwargs['targetPositions'] = action
            kwargs['targetVelocities'] = [0.0] * len(action)
            kwargs['forces'] = self.torque_limit
        elif self.control_mode == p.VELOCITY_CONTROL:
            kwargs['targetVelocities'] = action
            kwargs['forces'] = self.torque_limit
        else:
            kwargs['forces'] = action

        p.setJointMotorControlArray(self.uid,
                                    self.joint_ids,
                                    self.control_mode,
                                    positionGains=[self.position_gain] * len(action),
                                    velocityGains=[self.velocity_gain] * len(action),
                                    **kwargs)
