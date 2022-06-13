#!/usr/bin/env python3
import sys
import rospy
import actionlib
import moveit_commander
from std_msgs.msg import Int32
from robots.msg import FinDeplacerPiece_Msg
from moveit_msgs.msg import MoveGroupSequenceActionResult, MoveGroupSequenceActionGoal, MoveGroupSequenceAction, DisplayTrajectory
from moveit_msgs.msg import MotionSequenceRequest, MotionSequenceItem, Constraints, JointConstraint
from sensor_msgs.msg import JointState

trajectoryErrorCode2 = 1 #Succes = 1 in error_code

def DisplayTrajectoryCallback(traj):
	accel = []
	vel = []
	pos = []
	for points in traj.trajectory[0].joint_trajectory.points:
		if len(points.accelerations)==6:
			pos.append(points.positions)
			accel.append(points.accelerations)
			vel.append(points.velocities)
	fichierpos = open("./src/Kuka_kr6700/kuka_kr6_700sixx_moveit/scripts/pos.txt","a")
	fichiervel = open("./src/Kuka_kr6700/kuka_kr6_700sixx_moveit/scripts/vel.txt","a")
	fichieracc = open("./src/Kuka_kr6700/kuka_kr6_700sixx_moveit/scripts/acc.txt","a")
	for i in range(0,len(vel)):
		fichieracc.write(f"{accel[i][0]} {accel[i][1]} {accel[i][2]} {accel[i][3]} {accel[i][4]} {accel[i][5]}\n")
		fichiervel.write(f"{vel[i][0]} {vel[i][1]} {vel[i][2]} {vel[i][3]} {vel[i][4]} {vel[i][5]}\n")
		fichierpos.write(f"{pos[i][0]} {pos[i][1]} {pos[i][2]} {pos[i][3]} {pos[i][4]} {pos[i][5]}\n")
	fichierpos.close()
	fichiervel.close()
	fichieracc.close()
#Callback de fin de la trajectoire de pick and place
def TrajectoryResultCallback(errormsg):
	global trajectoryErrorCode2
	trajectoryErrorCode2 = errormsg.result.response.error_code.val

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
def Initialize(armgroup,handgroup):
	# print("Initiating ...")
	# group.set_planning_pipeline_id("ompl")
	# group.set_start_state_to_current_state()
	# group.set_joint_value_target(group.get_named_target_values("home"))
	# group.plan()
	# rospy.sleep(1)
	# group.go(wait=True)
	# group.stop()
	# rospy.sleep(1)

	motionSequenceRequest_ = MotionSequenceRequest()
	for i in range(0,2):
		motionPlanItemInitialize_ = MotionSequenceItem()
		constraints_ = Constraints()	
		#le premier planning a besoin d'un start_state, les autres démarrent automatiquement au goal précédent
		motionPlanItemInitialize_.req.pipeline_id = "ompl"
		motionPlanItemInitialize_.req.max_velocity_scaling_factor = 1.0
		motionPlanItemInitialize_.blend_radius = 0.0
		motionPlanItemInitialize_.req.allowed_planning_time = 5.0
		if(i==0):
			motionPlanItemInitialize_.req.group_name = armgroup.get_name()
			#initialise start_state à la position dans laquelle se trouve le robot
			jointName_ = armgroup.get_active_joints()
			jointPosition_ = armgroup.get_current_joint_values()
			motionPlanItemInitialize_.req.start_state.joint_state = JointState(name=jointName_,position=jointPosition_)
			#on récupère le goal
			dict_ = armgroup.get_named_target_values("home")
			for i in range(0,len(jointName_)):
				goalJointTemp_ = JointConstraint()
				goalJointTemp_.joint_name = jointName_[i]
				goalJointTemp_.position = dict_.get(jointName_[i])
				goalJointTemp_.tolerance_above = 1e-6
				goalJointTemp_.tolerance_below = 1e-6
				goalJointTemp_.weight = 1.0
				constraints_.joint_constraints.append(goalJointTemp_)
			#on ajoute notre premier item a la sequence request
			motionPlanItemInitialize_.req.goal_constraints.append(constraints_)
			motionSequenceRequest_.items.append(motionPlanItemInitialize_)
		else:
			motionPlanItemInitialize_.req.group_name = handgroup.get_name()
			#initialise start_state à la position dans laquelle se trouve la pince
			jointName_ = handgroup.get_active_joints()
			jointPosition_ = handgroup.get_current_joint_values()
			motionPlanItemInitialize_.req.start_state.joint_state = JointState(name=jointName_,position=jointPosition_)
			#on récupère le goal
			dict_ = handgroup.get_named_target_values("Open")
			for i in range(0,len(jointName_)):
				goalJointTemp_ = JointConstraint()
				goalJointTemp_.joint_name = jointName_[i]
				goalJointTemp_.position = dict_.get(jointName_[i])
				goalJointTemp_.tolerance_above = 1e-6
				goalJointTemp_.tolerance_below = 1e-6
				goalJointTemp_.weight = 1.0
				constraints_.joint_constraints.append(goalJointTemp_)
			#on ajoute notre second item a la sequence request
			motionPlanItemInitialize_.req.goal_constraints.append(constraints_)
			motionSequenceRequest_.items.append(motionPlanItemInitialize_)
	return motionSequenceRequest_


# cette fonction permet de construire un séquence de points dont le plannifieur pilz calculera la trajectoire
def BuildSequenceRequest(armgroup,handgroup):
	motionSequenceRequest_ = MotionSequenceRequest()
	armgroup_name = armgroup.get_named_targets()
	bool = True
	iter = 0
	while(iter<len(armgroup_name)):
		motionPlanItem_ = MotionSequenceItem()
		constraints2_ = Constraints()
		motionPlanItem_.req.pipeline_id = "pilz_industrial_motion_planner"
		motionPlanItem_.req.planner_id = "PTP"
		motionPlanItem_.req.max_velocity_scaling_factor = 1.0
		motionPlanItem_.req.max_acceleration_scaling_factor = 0.1
		motionPlanItem_.req.allowed_planning_time = 5.0
		#on est au dessus d'une navette ou d'un poste de travail on récupère une instuction pince
		if(iter==2 and bool):
			bool = False
			motionPlanItem_.blend_radius = 0.0
			motionPlanItem_.req.group_name = handgroup.get_name()
			#initialise start_state à la position dans laquelle se trouve la pince du srdf
			jointName_ = handgroup.get_active_joints()
			# jointPosition_ = handgroup.get_current_joint_values()
			# motionPlanItem_.req.start_state.joint_state = JointState(name=jointName_,position=jointPosition_)
			#on récupère le goal
			dict_ = handgroup.get_named_target_values("Close")
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
		#on est au dessus d'une navette ou d'un poste de travail on récupère une instuction pince du srdf
		elif(iter==6 and bool):
			bool = False
			motionPlanItem_.blend_radius = 0.0
			motionPlanItem_.req.group_name = handgroup.get_name()
			jointName_ = handgroup.get_active_joints()
			#on récupère le goal
			dict_ = handgroup.get_named_target_values("Open")
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
		#on récupère les instructions de la trajectoire de pick and place dans le fichier srdf
		else:
			#blend radius doit être égal à 0 pour le dernier point ainsi que lorsqu'on change de planning group
			if ((iter == len(armgroup_name)-1) or iter == 1 or iter == 5):
				motionPlanItem_.blend_radius == 0.0
			else:
				motionPlanItem_.blend_radius = 0.0
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
			bool = True
			iter = iter+1
	# la ligne ci-dessous permet de tester si les types de message que l'on ajoute à la séquence sont bons
	# motionSequenceRequest._check_types()
	return motionSequenceRequest_

#Callback de DeplacerPiece si mode rviz ou atelier
def ControlCallback(pub_yaska4):
	#création d'un client actionlib
	clientSequence_ = actionlib.SimpleActionClient('/kuka/sequence_move_group', MoveGroupSequenceAction)
	#attente de connexion
	clientSequence_.wait_for_server()
	# pub_motionSequenceRequest.publish(goal_)
	#on récupère la trajectoire a réaliser définie dans les groupes du fichier config/.srdf
	if pub_yaska4.data == 1:
		armgroup = moveit_commander.MoveGroupCommander("DN1P", robot_description="/kuka/robot_description", ns="/kuka")
	elif pub_yaska4.data == 2:
		armgroup = moveit_commander.MoveGroupCommander("DN2P", robot_description="/kuka/robot_description", ns="/kuka")
	elif pub_yaska4.data == 3:
		armgroup = moveit_commander.MoveGroupCommander("DPN1", robot_description="/kuka/robot_description", ns="/kuka")
	elif pub_yaska4.data == 4:
		armgroup = moveit_commander.MoveGroupCommander("DPN2", robot_description="/kuka/robot_description", ns="/kuka")
	else :
		print("Error callback control kuka \n")
		return
	# on récupère le groupe associé à la pince du robot
	handgroup = moveit_commander.MoveGroupCommander("kuka_hand", robot_description="/kuka/robot_description", ns="/kuka")
	print(f"Deplacement is {armgroup.get_name()}")
	while(True):
		# Initialise la position du robot à "home"
		initialize_ = MoveGroupSequenceActionGoal()
		initialize_.goal.request = Initialize(armgroup,handgroup)
		print("Initiating ...")
		clientSequence_.send_goal(initialize_.goal)
		finished_before_timeout = clientSequence_.wait_for_result(rospy.Duration(30))
		#Si l'initialisation s'est bien passé, on commence le pick and place
		if(finished_before_timeout & (trajectoryErrorCode2 == 1)):
			print("Initialization succeeded !")
			#construction de la séquence de point à envoyer
			# armgroup.set_start_state_to_current_state()
			goal_ = MoveGroupSequenceActionGoal()
			goal_.goal.request = BuildSequenceRequest(armgroup,handgroup)
			print("Executing Trajectory ...")
			clientSequence_.send_goal(goal_.goal)
			finished_before_timeout = clientSequence_.wait_for_result(rospy.Duration(1))
			rospy.sleep(1)
			if(finished_before_timeout & (trajectoryErrorCode2 == 1)):
				print("Trajectory completed !")
				rospy.loginfo(clientSequence_.get_goal_status_text())
				# print("Results: %s" %client_.action_client.ActionResult)
				#si tout s'est bien passé, on averti coppeliaSim de la fin d'execution du movement du robot
				mymsgKuka.FinDeplacerR4 = 1
				rospy.loginfo(mymsgKuka)
				pub_fintache.publish(mymsgKuka)
				rospy.sleep(1)
				mymsgKuka.FinDeplacerR4 = 0
				pub_fintache.publish(mymsgKuka)
				break
			else:
				print("Error during trajectory execution")
				choice = ErrorTrajectoryExecution()
				if(choice == 2):
					print("Aborting trajectory")
					mymsgKuka.FinDeplacerR4 = 1
					rospy.loginfo(mymsgKuka)
					pub_fintache.publish(mymsgKuka)
					rospy.sleep(1)
					mymsgKuka.FinDeplacerR4 = 0
					pub_fintache.publish(mymsgKuka)
					break
		else:
			print("Error during initialization")
			choice = ErrorTrajectoryExecution()
			if(choice == 2):
				print("Aborting trajectory")
				mymsgKuka.FinDeplacerR4 = 1
				rospy.loginfo(mymsgKuka)
				pub_fintache.publish(mymsgKuka)
				rospy.sleep(1)
				mymsgKuka.FinDeplacerR4 = 0
				pub_fintache.publish(mymsgKuka)
				break

if __name__ == "__main__":
	moveit_commander.roscpp_initialize(sys.argv)
	rospy.init_node('execute_trajectory_kuka',anonymous=True)
	mymsgKuka = FinDeplacerPiece_Msg()
	rospy.Subscriber('/control_robot_kuka',Int32, ControlCallback)
	rospy.Subscriber('/kuka/sequence_move_group/result', MoveGroupSequenceActionResult, TrajectoryResultCallback)
	pub_fintache = rospy.Publisher("/commande/Simulation/finTache", FinDeplacerPiece_Msg,  queue_size=1)
	# rospy.Subscriber('/yaska4/move_group/result', MoveGroupActionResult, InitializationCallback)
	# pub_motionSequenceRequest = rospy.Publisher( "/sequence_move_group/goal", MoveGroupSequenceActionGoal, queue_size=1)
	# rospy.Subscriber('kuka/move_group/display_planned_path', DisplayTrajectory, DisplayTrajectoryCallback)
	rospy.spin()
	moveit_commander.roscpp_shutdown()
