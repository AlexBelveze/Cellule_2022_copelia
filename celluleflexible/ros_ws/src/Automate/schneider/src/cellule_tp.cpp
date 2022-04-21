#include "cellule_tp.h"
#include <ros/ros.h>
#include <std_msgs/String.h>
#include <schneider/Retour_cellule.h>
#include <string>
#include <thread> 
#include <chrono>
#include <iostream>
#include <math.h>
using namespace std;


Cellule_tp::Cellule_tp(ros::NodeHandle noeud)
{	
	cmd_aigGauche_cell=noeud.subscribe("/commande/Simulation/AiguillageGauche",100,&Cellule_tp::AigGaucheCallback,this);
	cmd_aigDroite_cell=noeud.subscribe("/commande/Simulation/AiguillageDroite",100,&Cellule_tp::AigDroiteCallback,this);
	cmd_PS=noeud.subscribe("/commande/Simulation/Actionneurs_stops", 100,&Cellule_tp::CmdPSCallback,this);
	robot=noeud.subscribe("/commande/Simulation/DeplacerPiece",10,&Cellule_tp::RobCallabck,this);
	choixMode = noeud.subscribe("/commande_locale/ChoixMode", 10,&Cellule_tp::TypeMode,this);
	pub_fintache = noeud.advertise<robots::FinDeplacerPiece_Msg>("/commande/Simulation/finTache", 1);
	pub = noeud.advertise<std_msgs::String>("/control_cellule", 1);
	cap = noeud.advertise<schneider::Msg_SensorState>("/commande/Simulation/Capteurs", 1);
	client = noeud.serviceClient<schneider::Retour_cellule>("retour_cellule");
	mode = 0;
	isKukaPhysical = 0;
}

Cellule_tp::~Cellule_tp()
{
}

void Cellule_tp::TypeMode(const commande_locale::Msg_ChoixMode::ConstPtr& msg1)
{
	mode = msg1->mode;
	isKukaPhysical = msg1->kuka;

}


void Cellule_tp::read()
{	
	srv.request.memoire = 1;
	std::this_thread::sleep_for (std::chrono::milliseconds(200));
	if (client.call(srv))
	{
		SensorState.id = 102;
		SensorState.PS[1] = srv.response.PS1;
		SensorState.PS[2] = srv.response.PS2;
		SensorState.PS[3] = srv.response.PS3;
		SensorState.PS[4] = srv.response.PS4;
		SensorState.PS[5] = srv.response.PS5;
		SensorState.PS[6] = srv.response.PS6;
		SensorState.PS[20] = srv.response.PS20;
		SensorState.PS[21] = srv.response.PS21;
		SensorState.PS[22] = srv.response.PS22;
		SensorState.PS[23] = srv.response.PS23;
		SensorState.PS[24] = srv.response.PS24;
		SensorState.DD[1] = srv.response.D1D;
		SensorState.DD[2]= srv.response.D2D;
		SensorState.DD[11] = srv.response.D11D;
		SensorState.DD[12] = srv.response.D12D;
		SensorState.DG[1] = srv.response.D1G;
		SensorState.DG[2] = srv.response.D2G;
		SensorState.DG[11] = srv.response.D11G;
		SensorState.DG[12] = srv.response.D12G;
		SensorState.CPI[1] = srv.response.CPI1;
		SensorState.CPI[2] = srv.response.CPI2;
		SensorState.CPI[7] = srv.response.CPI7;
		SensorState.CPI[8] = srv.response.CPI8;
		SensorState.CP[1] = srv.response.CP1;
		SensorState.CP[2] = srv.response.CP2;
		SensorState.CP[9] = srv.response.CP9;
		SensorState.CP[10] = srv.response.CP10;
		SensorRobots.FinDeplacerR1 = srv.response.INR1;
		if(mode==1){
			cap.publish(SensorState);
			pub_fintache.publish(SensorRobots);
		}


	}
	else
	{
		read();
	}
}


void Cellule_tp::write(vector<vector<int>> consigne)
{
	data = "";
	for (int i=0; i<consigne.size(); i=i+1){
        data += "," + to_string(consigne[i][0]) + "," + to_string(consigne[i][1]);
    }
	msg.data = data;
	cout<<"data="<<data<<endl;
    std::this_thread::sleep_for (std::chrono::milliseconds(100));
	pub.publish(msg);
}


void Cellule_tp::AigGaucheCallback(const std_msgs::Int32::ConstPtr& msg_aigs)
{
	if(mode==1){
		ROS_INFO("On bouge a gauche, aig numero %d", msg_aigs->data);
		//commande type {Dx, Vx, RxD, RxG}
		if (msg_aigs->data==1)
		{	
			this->write({{22, 1}, {26, 0},{10, 0},{14, 1}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==2)
		{	
			this->write({{23, 1}, {27, 0},{11, 0},{15, 1}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==11)
		{	
			this->write({{24, 1}, {28, 0},{12, 0},{16, 1}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==12)
		{	
			this->write({{25, 1}, {29, 0},{13, 0},{17, 1}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
	}
	
}

void Cellule_tp::AigDroiteCallback(const std_msgs::Int32::ConstPtr& msg_aigs)
{

	if(mode==1){
		ROS_INFO("On bouge a droite, aig numero %d", msg_aigs->data);
		//commande type {Dx, Vx, RxD, RxG}
		if (msg_aigs->data==1)
		{	
			this->write({{22, 1}, {26, 0},{10, 1},{14, 0}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==2)
		{	
			this->write({{23, 1}, {27, 0},{11, 1},{15, 0}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==11)
		{	
			this->write({{24, 1}, {28, 0},{12, 1},{16, 0}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
		if (msg_aigs->data==12)
		{	
			this->write({{25, 1}, {29, 0},{13, 1},{17, 0}});
			ros::Duration(2).sleep();
			this->write({{26, 1}, {27, 1}, {28, 1}, {29, 1}, {22, 0}, {23, 0}, {24, 0}, {25, 0} });
		}
	}
}


void Cellule_tp::CmdPSCallback(const commande_locale::Msg_StopControl actionneurs_simulation_Stop)
{
	if(mode==1){
		int i;
		const int tabPS[10]={1,2,3,4,5,20,21,22,23,24};
		for(i=0;i<10;i++){
			if(actionneurs_simulation_Stop.STOP[tabPS[i]]==1){
				this->write({{i, 0}});
			}
			else
			{
				this->write({{i, 1}});
			}
		}
		for(i=0;i<10;i++){
			if(actionneurs_simulation_Stop.GO[tabPS[i]]==1){
				if(tabPS[i] == 21){
					this->write({{20,0}});
				}
				else if(tabPS[i] == 22){
					this->write({{21,0}});
				}
				this->write({{i, 1}});
			}
			else
			{
				this->write({{i, 0}});
			}
		}
	}

}

void Cellule_tp::RobCallabck(const commande_locale::DeplacerPieceMsg msg)
{
	
	if (mode == 1 && msg.num_robot==1 && isKukaPhysical==1)
	{
		if (msg.positionA==3 || msg.positionB==3)
		{
			this->write({{21,1}});
		}
		if (msg.positionA==2 || msg.positionB==2)
		{
			this->write({{20,1}});
		}
		if(msg.positionA==3)
		{
			this->write({{36,1},{34,1}});
			ros::Duration(2).sleep();
			this->write({{36,0},{34,0}});
		}
		else if(msg.positionA==2)
		{
			this->write({{36,1},{35,1}});
			ros::Duration(2).sleep();
			this->write({{36,0},{35,0}});
		}
		else if (msg.positionB==3)
		{
			this->write({{37,1},{34,1}});
			ros::Duration(2).sleep();
			this->write({{37,0},{34,0}});
		}
		else if (msg.positionB==2)
		{
			this->write({{37,1},{35,1}});
			ros::Duration(2).sleep();
			this->write({{37,0},{35,0}});
		}

	}












}







