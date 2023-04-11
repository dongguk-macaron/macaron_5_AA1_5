#!/usr/bin/env python
# -- coding: utf-8 --

# basic package
import rospy
import time
from math import pi

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))) + "/src/sensor")

# message file
from jeju.msg import erp_read
from jeju.msg import erp_write
from std_msgs.msg import Float64
from std_msgs.msg import Int16, Int32
from geometry_msgs.msg import Twist

# 곡률에따른 속도제어
MAX__SPEED = 100
MIN___SPEED = 80 # 평상시

# MODE 1이면 곡률제어, 2이면 yaw값 비교 제어
MODE = 2
#track
#MODE = 1

# 초기값
MIN__SPEED = 60

class Integral_control():
    def __init__(self, time):
        self.I_value = 0
        self.Ki = 0.25
        #self.Ki = 0.5
        self.time = time
    
    def I_control(self, error):
        
        self.I_value += error * self.time
        if error <= 0:
            self.I_value = 0
        if self.I_value >= 80:
            self.I_value = 80
            #self.I_value = 40

        return self.Ki * self.I_value



class speed_planner():
    def __init__(self):
        self.Kp = 3.5           # Speed PID control에서 Proportional 계수
        #self.Kp = 2.0 
        self.Kp_brake = 2     # Brake PID control에서 Proportional 계수
        self.Kp_reverse = 4   # 후진 Proportional 계수
        
        self.current_speed = 0
        self.target_speed = 0
        self.static_brake = 0
        self.steer = 0

        self.max_curvature = 0
        self.max_speed = 0  #??
        self.min_speed = 100 ##??
        self.min_time = 0
        
        self.brake_flag = 0

        self.PID_I = Integral_control(0.1)

        self.sub_speed_steer = rospy.Subscriber('speed_planner', Twist, self.spd_str_callback, queue_size=30)
        self.erp_sub= rospy.Subscriber('erp_read', erp_read, self.erp_callback, queue_size=30)
        # self.erp_sub_speed= rospy.Subscriber('speed_read', Int16, self.erp_callback_speed, queue_size=1)
        # self.erp_sub_steer= rospy.Subscriber('steer_read', Int32, self.erp_callback_steer, queue_size=1)
        self.curvature_sub= rospy.Subscriber('curvature', Float64, self.curvature_callback, queue_size=30)

        
        self.erp_pub = rospy.Publisher('erp_write', erp_write, queue_size=10)
        # self.erp_pub_speed = rospy.Publisher("speed_write", Int16, queue_size=1)
        # self.erp_pub_steer = rospy.Publisher("steer_write", Int32, queue_size=1)
        # self.erp_pubb_speed = erp_write().write_speed
        # self.erp_pubb_steer = erp_write().write_steer
        self.erp = erp_write()

    def spd_str_callback(self, data):
        self.max_speed = data.linear.x
        self.steer = data.angular.z

        if (self.max_speed >= -100) and (self.max_speed <= 100):
            self.target_speed = self.det_target_speed(self.max_speed)
        else:
            self.target_speed = self.max_speed

        if self.steer >= 30:
            self.steer = 30
        elif self.steer <= -30:
            self.steer = -30

    def erp_callback(self, data):
        self.current_speed = data.linear.x
        # self.erp_sub_speed = data
        # self.current_speed = self.erp_sub_speed
        # self.erp_ENC = data.read_ENC
        # if data.read_gear == 2 and self.current_speed > 0:
        #     self.current_speed *= -1

    # def erp_callback_steer(self, data):
    #     self.erp_sub_steer = data



    def curvature_callback(self, value):
        alpha = 0.5 # 직전 값을 얼마나 반영할건지
        if MODE == 1:
            if value.data > 2.0:
                #value.data > 1.5
                pass
            else:
                # low pass filter
                self.max_curvature = self.max_curvature * alpha + (1 - alpha) * value.data
        elif MODE == 2:
            self.max_curvature = self.max_curvature * alpha + (1 - alpha) * value.data

    def pub_serial(self, speed): #gear removed
        speed, self.steer = speed, self.steer
        # if brake <= 1:
        #     brake = 1
        # elif brake >= 200:
        #     brake = 200



        self.erp.write_speed = speed
        self.erp.write_steer = int(self.steer)
        # self.erp_pubb_speed = speed
        # self.erp_pubb_steer = self.steer
        # self.erp.write_brake = brake
        # self.erp.write_gear = gear

        self.erp_pub.publish(self.erp)
        # self.erp_pub_speed.publish(self.erp)
        # self.erp_pub_steer.publish(self.erp)
        # self.erp_pub_speed.publish(self.erp_pubb_speed)
        # self.erp_pub_steer.publish(self.erp_pubb_steer)

    def det_target_speed(self, max_spd):
        global MIN__SPEED, MIN___SPEED, STATIC_MIN___SPEED
        max_speed = abs(max_spd)
        # 정적 장애물
        if max_spd == 80:
            MIN__SPEED = STATIC_MIN___SPEED
        else:
            MIN__SPEED = MIN___SPEED


        if MODE == 1:        
            if self.max_curvature <= 0.3:
                target_speed = MAX__SPEED
            elif self.max_curvature >= 0.8:
                target_speed = MIN__SPEED
            else:
                target_speed = float(((MIN__SPEED - MAX__SPEED)/(0.8 - 0.3)) * (self.max_curvature - 0.3) + MAX__SPEED)
        elif MODE == 2:
            if self.max_curvature <= 20 * pi / 180:
                target_speed = MAX__SPEED
            elif self.max_curvature >= 70 * pi / 180:
                #self.max_curvature >= 60 * pi / 180:
                target_speed = MIN__SPEED
            else:
                target_speed = float(((MIN__SPEED - MAX__SPEED)/(70*pi/180 - 20*pi/180)) * (self.max_curvature - 20*pi/180) + MAX__SPEED)

        if target_speed >= 100:
            target_speed = 100
        elif target_speed <= 0:
            target_speed = 0

        # 1.5초동안 저속 유지
        if max_spd > 0 and self.min_speed > target_speed:
            self.min_speed = target_speed
            self.min_time = time.time() + 2.0

        # 일정 시간 저속 유지 2
        if max_spd > 0 and self.min_time > time.time():
            target_speed = self.min_speed
        else:
            self.min_speed = 80

        if target_speed >= max_speed:
            target_speed = max_speed

        if max_spd < 0:
            target_speed = -target_speed

        return target_speed

    def speed_planner(self):
        speed, brake = 0, 1 #gear removed

        # 주행 상황
        if self.target_speed > 0:
            P_speed = self.Kp * (self.target_speed - self.current_speed) + self.current_speed
            if self.current_speed == 0 or abs(self.current_speed - self.target_speed) <= 7 :
                I_speed = self.PID_I.I_control(0)    
            else:
                I_speed = self.PID_I.I_control(self.target_speed - self.current_speed)
            speed = I_speed + P_speed
            print(I_speed,"I_speed")
            # 속도를 많이 줄여야 한다면
            if self.target_speed - self.current_speed < -20:
                brake_1 = 63 + 0.25 * abs(self.current_speed) - 10
                brake_2 = ((15 / (100 - 20)) * (self.current_speed - self.target_speed) - 20) - 15
                if brake_2 >= 0:
                    brake_2 = 0
                elif brake_2 <= -15:
                    brake_2 = -15
                brake = brake_1 + brake_2
                
            self.brake_flag = 0

        # 정지 상황
        elif self.target_speed == 0:
            if self.brake_flag == 0:
                self.static_brake = 63 + 0.25 * abs(self.current_speed) + 2
                brake = self.static_brake
                self.brake_flag = 1
            else:
                brake = self.static_brake

            if self.current_speed == 0:
                brake = 100

        # 급정지 상황
        elif self.target_speed == -201:
            brake = 110 # 동적 장애물 코스에서 속도가 50이라서
            #brake = 80
            self.brake_flag = 0

        # 후진 상황
        else:
            P_speed = self.Kp_reverse * (self.current_speed - self.target_speed) + -(self.current_speed)
            if self.current_speed == 0 or abs(self.current_speed - self.target_speed) <= 7:
                I_speed = self.PID_I.I_control(0)
            else:
                I_speed = self.PID_I.I_control(self.current_speed - self.target_speed)
            speed = I_speed + P_speed
            
            # 속도를 많이 줄여야 한다면
            if self.target_speed - self.current_speed > 10:
                brake = self.Kp_brake * (self.target_speed - self.current_speed)
            # gear = 2
            self.brake_flag = 0

        if speed >= 100:
            speed = 100
        elif speed <= 0:
            speed = 0
        
        if brake >= 200:
            brake = 0 #200
        elif brake <= 1:
            brake = 0 #1

        return speed, brake #gear removed

###########################################
# 주행 할때는 끄고 함수만 호출되는거임.
def main():
    rospy.init_node("speed_planner", anonymous=True)

    rate = rospy.Rate(1)

    sp = speed_planner()
    while not rospy.is_shutdown():
        speed, brake = sp.speed_planner() #gear removed
        
        sp.pub_serial(speed)
        
        print("cu, max, target, brake, steer",sp.current_speed, sp.max_speed, sp.target_speed, brake, sp.steer)
        if MODE == 1:
            print(sp.max_curvature)
        elif MODE == 2:
            print(sp.max_curvature*180/pi)

        rate.sleep()


if __name__ == '__main__':
    main()