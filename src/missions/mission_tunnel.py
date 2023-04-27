#!/usr/bin/env python3
# noinspection PyUnresolvedReferences
import rospy
import time
import numpy as np
# noinspection PyUnresolvedReferences
from sensor_msgs.msg import LaserScan
# noinspection PyUnresolvedReferences
from geometry_msgs.msg import Twist


class mission_tunnel:
    def __init__(self):
        self.laser_sub = rospy.Subscriber('/scan', LaserScan, self.scan_callback, queue_size=1)
        self.sub_scan = []
        self.width = 0.77  # 차 폭 [m]
        # self.wheel_base = 0.75  # 차축 간 거리 [m]
        # self.length = 1.35  # 차 길이 [m]
        self.tunnel_width = 1.5  # 터널 폭 [m]
        self.max_dis = 10.0  # lidar 센서 최대 측정 범위 [m]

        self.tunnel_flag = False
        self.step = 0
        self.limit = 3.0

    def scan_callback(self, scan):
        sub_scan = np.array(scan.ranges[0:810 + 1:3])  # 0° ~ 270° 범위, 0.333° 간격의 811개 data 를 1° 간격의 361개 data 로 필터링
        self.sub_scan = np.where(sub_scan >= self.max_dis, self.max_dis, sub_scan)  # max_dis 를 넘는 값 or inf -> max_dis

    # noinspection PyMethodMayBeStatic
    def find_largest_second_largest(self, list_data):
        max_val = float('-inf')
        second_max_val = float('-inf')
        max_index = -1
        second_max_index = -1

        for i, val in enumerate(list_data):
            if val > max_val:
                second_max_val = max_val
                second_max_index = max_index
                max_val = val
                max_index = i
            elif val > second_max_val:
                second_max_val = val
                second_max_index = i
        return [max_index, second_max_index]

    def search_tunnel_entrance(self):
        scan_data = self.sub_scan[45:225 + 1]
        change_rate_list = np.array([abs(scan_data[i] - scan_data[i + 1]) for i in range(len(scan_data) - 1)])
        change_rate_list = np.where(change_rate_list >= self.limit, self.limit, change_rate_list)
        max_index, second_index = sorted(self.find_largest_second_largest(change_rate_list))
        center_angle = int(len(scan_data) * 0.5)
        first_angle, second_angle = max_index - center_angle, second_index - center_angle
        if first_angle >= 60 and second_angle <= -60:
        # if scan_data[first_angle] <= self.tunnel_width or scan_data[second_angle] <= self.tunnel_width:
            self.tunnel_flag = True
        return np.clip(-(first_angle + second_angle) * 0.5, -22, 22)

    def get_steer_in_tunnel(self):
        r_data, l_data = self.sub_scan[55:75+1:3], self.sub_scan[195:215+1:3]  # 정면 0° 기준 좌우 60° ~ 80° 범위 거리 데이터
        r_avg, l_avg = np.sum(r_data) / len(r_data), np.sum(l_data) / len(l_data)  # 60° ~ 80° 범위의 거리 값들의 평균
        steer = ((r_avg - l_avg) / (self.tunnel_width - self.width)) * 1.1 * 22  # (-1 ~ 1 로 정규화) * 1.1(가중치) * 22(steer)
        if r_avg >= self.tunnel_width and l_avg >= self.tunnel_width:
            self.tunnel_flag = False
        return np.clip(steer, -22, 22)

    def get_steer(self):
        if self.tunnel_flag is False:
            return self.search_tunnel_entrance()
        elif self.tunnel_flag is True:
            return self.get_steer_in_tunnel()


class PublishToErp:
    def __init__(self):
        self.erp_pub = rospy.Publisher("erp_write", Twist, queue_size=30)
        self.erp = Twist()

    def pub_erp(self, speed, steer):
        self.erp.linear.x = speed
        self.erp.angular.z = steer
        self.erp_pub.publish(self.erp)


# def main():
#     rospy.init_node('tunnel_node', anonymous=True)
#     Tunnel = mission_tunnel()
#     pub = PublishToErp()

#     while not rospy.is_shutdown():
#         time.sleep(0.1)
#         speed = 50
#         steer = Tunnel.get_steer()
#         pub.pub_erp(speed, steer)


# if __name__ == '__main__':
#     main()
