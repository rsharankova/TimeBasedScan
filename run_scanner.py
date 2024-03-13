from scanner import scanner
import os
import argparse
import time
import numpy as np

def parse_args(args_dict):
    parser = argparse.ArgumentParser(description="usage: %prog [options] \n")
    parser.add_argument ('--readfile',  dest='readfile', default='Reading_devices.csv',
                         help="Reading device list file name. (default: Reading_devices.csv)")
    parser.add_argument ('--devlist',  dest='devlist', default=['Z:CUBE_Z'],
                         help="List of devices to scan. (default: Z:CUBE devices")
    parser.add_argument ('--event',  dest='event', default='@e,1d,e,0',
                         help="Event or periodic frequency. (default: '@p,1000')")
    parser.add_argument ('--role',  dest='role', default='testing',
                         help="Setting role. (default: 'testing')")
    
    
    options  = parser.parse_args()

    #assume files are in workdir
    args_dict['readfile'] = os.path.join(os.getcwd(),options.readfile)
    args_dict['event']    = options.event
    args_dict['dev_list'] = options.devlist
    args_dict['role']     = options.role

    
def make_ramplist(sc,device_list):
    nominals = sc.get_settings_once(device_list)

    ramplist = []

    [ramplist.append(sum([[dev,float(nom)+i] for dev,nom in zip(device_list,nominals)],['1'])) for i in range(-3,4)]
    ramplist[0][0]='0'

    print(ramplist)
    return ramplist

    
def run(sc,read_list,ramp_list,role,Nmeas,event):
    set_list = ['%s%s'%(s.replace(':','_'),event) for s in ramp_list[0] if str(s).find(':')!=-1] if len(ramp_list)>0 else []
    drf_list = set_list+['%s%s'%(l,event) for l in read_list if len(read_list)!=0]

    thread = 'scanner'

    timeout = 30 #seconds?

    
    try:
        sc.start_thread('%s'%thread,timeout,drf_list,ramp_list,role,Nmeas)
        
    except Exception as e:
        print('Scan failed',e)


def main():

    args_dict = {'readfile':'', 'event':'', 'dev_list':[],'role':''}
    parse_args(args_dict)
    
    sc = scanner()

    read_list = args_dict['dev_list'] + sc.readList(args_dict['readfile'])
    ramp_list = make_ramplist(sc,args_dict['dev_list'])
    #ramp_list=[]
    Nmeas = 1 # number of measurements to be taken at every setting
    devs = ['Z:CUBE_Z']
    nominals = sc.get_settings_once(devs)
    print(nominals)
    
    run(sc,read_list,ramp_list,args_dict['role'],Nmeas,args_dict['event'])

    sc.apply_settings_once(devs,np.add(nominals,-20),args_dict['role'])

    
if __name__ == "__main__":
    main()
