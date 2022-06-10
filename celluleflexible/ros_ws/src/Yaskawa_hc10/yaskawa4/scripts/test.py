#!/usr/bin/env python3
import sys
import copy
from turtle import position
import rospy
import actionlib
import moveit_commander
from std_msgs.msg import Int32
from robots.msg import FinDeplacerPiece_Msg
from moveit_msgs.msg import MoveGroupSequenceActionResult, MoveGroupSequenceActionGoal, MoveGroupSequenceAction
from moveit_msgs.msg import MotionSequenceRequest, MotionSequenceItem, Constraints, JointConstraint
from sensor_msgs.msg import JointState

trajectoryErrorCode4 = 1 #Succes = 1 in error_code

#Callback de fin de la trajectoire de pick and place
def TrajectoryResultCallback(errormsg):
	global trajectoryErrorCode4
	trajectoryErrorCode4 = errormsg.result.response.error_code.val

#Callback de fin de trajectoire d'initialisation
# def InitializationCallback(errormsg):
# 	global trajectoryErrorCode4
# 	trajectoryErrorCode4 = errormsg.result.error_code.val

#Interface de gestion de l'erreur par l'utilisateur
def ErrorTrajectoryExecution():
	print("""What would you like to do? 
	1. Finish trajectory 
	2. Abort trajectory """)
	while(True):
		choice = input('Choice:')
		if(choice.isdigit() and int(choice) in range(1,3)):
			return int(choice)
		print("Invalid choice, try again")

#Cette fonction permet de faire revenir le robot en position home peut importe sa position actuelle en utilisant le planner ompl
# cette fonction permet de construire un séquence de points dont le plannifieur pilz calculera la trajectoire
def BuildSequenceRequest(armgroup):
	motionPlanItemInitialize_ = MotionSequenceItem()
	motionSequenceRequest_ = MotionSequenceRequest()
	constraints1_ = Constraints()	
	#le premier planning a besoin d'un start_state, les autres démarrent automatiquement au goal précédent
	motionPlanItemInitialize_.req.pipeline_id = "ompl"
	# PTP, CIR, LIN
	motionPlanItemInitialize_.req.max_velocity_scaling_factor = 1.0
	motionPlanItemInitialize_.blend_radius = 0.0
	motionPlanItemInitialize_.req.allowed_planning_time = 5.0
	motionPlanItemInitialize_.req.group_name = armgroup.get_name()
	#initialise start_state à la position dans laquelle se trouve le robot
	jointName_ = armgroup.get_active_joints()
	jointPosition_ = armgroup.get_current_joint_values()
	motionPlanItemInitialize_.req.start_state.joint_state = JointState(name=jointName_,position=jointPosition_)
	#on récupère le premier goal
	#récupère le nom des différentes positions définie dans le groupe du fichier srdf
	armgroup_name = armgroup.get_named_targets()
	#on récupère les noms et valeurs des joints de la première postion du groupe sous forme de dictionnaire
	dict_ = armgroup.get_named_target_values(armgroup_name[0])
	#on ajoute notre premier item a la sequence request
	for i in range(0,len(jointName_)):
		goalJointTemp_ = JointConstraint()
		goalJointTemp_.joint_name = jointName_[i]
		goalJointTemp_.position = dict_.get(jointName_[i])
		goalJointTemp_.tolerance_above = 1e-6
		goalJointTemp_.tolerance_below = 1e-6
		goalJointTemp_.weight = 1.0
		constraints1_.joint_constraints.append(goalJointTemp_)
	motionPlanItemInitialize_.req.goal_constraints.append(constraints1_)
	motionSequenceRequest_.items.append(motionPlanItemInitialize_)
	# #on ajoute les autres items a la sequence
	iter = 0
	while(iter<len(armgroup_name)):
		motionPlanItem_ = MotionSequenceItem()
		constraints2_ = Constraints()
		motionPlanItem_.req.pipeline_id = "ompl"
		motionPlanItem_.req.max_velocity_scaling_factor = 1.0
		motionPlanItem_.blend_radius = 0.0
		motionPlanItem_.req.allowed_planning_time = 5.0
		motionPlanItem_.req.group_name = armgroup.get_name()
		jointName_ = armgroup.get_active_joints()
		#on récupère le goal
		dict_ = armgroup.get_named_target_values(armgroup_name[iter])
		for i in range(0,len(jointName_)):
			goalJointTemp_ = JointConstraint()
			goalJointTemp_.joint_name = jointName_[i]
			goalJointTemp_.position = dict_.get(jointName_[i])
			goalJointTemp_.tolerance_above = 1e-6
			goalJointTemp_.tolerance_below = 1e-6
			goalJointTemp_.weight = 1.0
			constraints2_.joint_constraints.append(goalJointTemp_)
		#on ajoute notre item a la sequence request
		motionPlanItem_.req.goal_constraints.append(constraints2_)
		motionSequenceRequest_.items.append(motionPlanItem_)
		iter = iter+1
	# la ligne ci-dessous permet de tester si les types de message que l'on ajoute à la séquence sont bons
	# motionSequenceRequest._check_types()
	return motionSequenceRequest_

#Callback de DeplacerPiece si mode rviz ou atelier
def ControlCallback(pub_yaska4):
	#création d'un client actionlib
	clientSequence_ = actionlib.SimpleActionClient('/yaska4/sequence_move_group', MoveGroupSequenceAction)
	#attente de connexion
	clientSequence_.wait_for_server()
	# pub_motionSequenceRequest.publish(goal_)
	#on récupère la trajectoire a réaliser définie dans les groupes du fichier config/.srdf
	if pub_yaska4.data == 1:
		armgroup = moveit_commander.MoveGroupCommander("DN1P", robot_description="/yaska4/robot_description", ns="/yaska4")
	elif pub_yaska4.data == 2:
		armgroup = moveit_commander.MoveGroupCommander("DN2P", robot_description="/yaska4/robot_description", ns="/yaska4")
	elif pub_yaska4.data == 3:
		armgroup = moveit_commander.MoveGroupCommander("DPN1", robot_description="/yaska4/robot_description", ns="/yaska4")
	elif pub_yaska4.data == 4:
		armgroup = moveit_commander.MoveGroupCommander("DPN2", robot_description="/yaska4/robot_description", ns="/yaska4")
	else :
		print("Error callback control yaska4 \n")
		return
	# on récupère le groupe associé à la pince du robot
	handgroup = moveit_commander.MoveGroupCommander("yaskawa4_hand", robot_description="/yaska4/robot_description", ns="/yaska4")
	print(f"Deplacement is {armgroup.get_name()}")
	while(True):
		# Initialise la position du robot à "home"
		initialize_ = MoveGroupSequenceActionGoal()
		initialize_.goal.request = BuildSequenceRequest(armgroup)
		print("Initiating ...")
		clientSequence_.send_goal(initialize_.goal)
		finished_before_timeout = clientSequence_.wait_for_result(rospy.Duration(30))
		#Si l'initialisation s'est bien passé, on commence le pick and place
		if(finished_before_timeout & (trajectoryErrorCode4 == 1)):
			print("Initialization succeeded !")
			mymsgYaska4.FinDeplacerR4 = 1
			rospy.loginfo(mymsgYaska4)
			pub_fintache.publish(mymsgYaska4)
			rospy.sleep(1)
			mymsgYaska4.FinDeplacerR4 = 0
			pub_fintache.publish(mymsgYaska4)
			break
		else:
			print("Error during initialization")
			choice = ErrorTrajectoryExecution()
			if(choice == 2):
				print("Aborting trajectory")
				mymsgYaska4.FinDeplacerR4 = 1
				rospy.loginfo(mymsgYaska4)
				pub_fintache.publish(mymsgYaska4)
				rospy.sleep(1)
				mymsgYaska4.FinDeplacerR4 = 0
				pub_fintache.publish(mymsgYaska4)
				break

if __name__ == "__main__":
	moveit_commander.roscpp_initialize(sys.argv)
	rospy.init_node('execute_trajectory_yaska4',anonymous=True)
	mymsgYaska4 = FinDeplacerPiece_Msg()
	rospy.Subscriber('/control_robot_yaska4',Int32, ControlCallback)
	rospy.Subscriber('/yaska4/sequence_move_group/result', MoveGroupSequenceActionResult, TrajectoryResultCallback)
	pub_fintache = rospy.Publisher("/commande/Simulation/finTache", FinDeplacerPiece_Msg,  queue_size=1)
	# rospy.Subscriber('/yaska4/move_group/result', MoveGroupActionResult, InitializationCallback)
	# pub_motionSequenceRequest = rospy.Publisher( "/sequence_move_group/goal", MoveGroupSequenceActionGoal, queue_size=1)
	rospy.spin()
	moveit_commander.roscpp_shutdown()