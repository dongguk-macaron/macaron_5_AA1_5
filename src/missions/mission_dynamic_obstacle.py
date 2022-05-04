#!/usr/bin/env python
#-*-coding:utf-8-*-

## 전체 알고리즙 ##
# 1. 일단 동적 장애물 구간에서는 장애물회피가 아니라 e_stop 거는걸로
# . 스캔하는 것도 내 위치에서 일정 거리 이하의 인덱스만 해야 되지 않을까? -> 아니면 동적장애물 구간 경로만 따로 따놔도 될듯 -> 일단 이걸로 가자
# 2. 구간 2개 중에 어디서 나올 지 몰라서 내부에 state를 만들어서 두번 실행 되게 해야될듯?
# ->> 다른 미션 구간에 들어가면 자동으로 done 되게 해도 되지 않을까?

# Python packages
import rospy
import sys, os
import math
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))) + "/path_planning")

from path_planning_tracking import Path_Tracking
from mission_parking import two_dis, find_ind

# 파라미터
car_w_offset = 2.8 / 2.0
car_f_offset = 1.5
stop_dis = 4.0
restart_time = 1

stop_dis = stop_dis + car_f_offset

class mission_dynamic_obstacle():
    def __init__(self, where):
        if where == 1:
            self.mission_np = np.load(file = (os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))+"/path/npy_file/path/MH_straight.npy")
        else:
            self.mission_np = np.load(file = (os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))+"/path/npy_file/path/kcity_tryout_Dobs.npy")
        self.state = "go"

    def scan(self, pose, obs): # 장애물 상황을 스캔하는 함수
        global car_w_offset, stop_dis, restart_time
        for p in obs:
            n = find_ind(p, self.mission_np)
            if (two_dis(p, self.mission_np[n]) < car_w_offset) and (two_dis(pose, self.mission_np[n]) < stop_dis):
                self.state = "stop"
                return self.state
        if self.state == "stop":
            rospy.sleep(restart_time) # 멈춰있다가 출발시 딜레이를 줌
        self.state = "go"
        return self.state