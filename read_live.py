import sys
import acsys.dpm
import pandas as pd
import argparse
from datetime import date
from functools import reduce

'''
request_list = [
    'L:RFQPAH@e,1d,e,0',
    'L:RFBPAH@e,1d,e,0',
    'L:V5QSET@e,1d,e,0',
    'L:D7LMSM@e,1d,e,0',
    'L:TO1IN@e,1d,e,0',
    'L:TO3IN@e,1d,e,0',
    'L:TO5OUT@e,1d,e,0',
    'L:D7TOR@e,1d,e,0',
    'L:D00LM@e,1d,e,0',
    
]
for a in range(1,8):
    for b in range(1,5):
        request_list.append('L:D%s%sLM@e,1d,e,0'%(a,b))

'''
request_list  =[
    'Z:CUBE_X@e,1d,e,0',
    'Z:CUBE_Y@e,1d,e,0',
    'Z:CUBE_Z@e,1d,e,0',
]
    

############
# User input
############
parser = argparse.ArgumentParser(description='Phase scan')
parser.add_argument("-d", "--device",
                    type=str,
                    required=True,
                    help="Device to scan: RFQ, RFB, V5Q")
parser.add_argument("-min", "--minimum",
                    type=float,
                    required=True,
                    help="Lower bound of scan")
parser.add_argument("-max", "--maximum",
                    type=float,
                    required=True,
                    help="Upper bound of scan")
parser.add_argument("-s", "--step",
                    type=float,
                    required=True,
                    help="Scan step size")

args = parser.parse_args()
device = args.device
minval = args.minimum
maxval = args.maximum
step = args.step

print(minval, maxval, step, device)

if device=='RFQ':
    request_list.insert(0,'L:RFQPAH.SETTING@e,1d,e,0')
    request_list.remove('L:RFQPAH@e,1d,e,0')
elif device=='RFB':
    request_list.insert(0,'L:RFBPAH.SETTING@e,1d,e,0')
    request_list.remove('L:RFBPAH@e,1d,e,0')
elif device=='V5Q':
    request_list.insert(0,'L:V5QSET.SETTING@e,1d,e,0')
    request_list.remove('L:V5QSET@e,1d,e,0')
elif device=='CUBE_Z':
    request_list.insert(0,'Z:CUBE_Z.SETTING@e,1d,e,0')
    request_list.remove('Z:CUBE_Z@e,1d,e,0')
else:
    print('Unknown device name')
    exit(0)

print(request_list)    

data =[]


def fill_dataframe(data):
    df = pd.DataFrame.from_records(data)
    devlist = df.name.unique()
    dflist=[]
    for dev in devlist:
        dfdev= df[df.name==dev][['stamp','data']]
        dfdev['stamp']= pd.to_datetime(dfdev['stamp'])
        dfdev['TS']=dfdev['stamp']
        dfdev.rename(columns={'data':dev, 'TS':'%s Timestamp'%dev},inplace=True)
        dfdev.set_index('stamp').reset_index(drop=False, inplace=True)
        dflist.append(dfdev)        
        
    ddf = reduce(lambda  left,right: pd.merge_asof(left,right,on=['stamp'],direction='nearest',tolerance=pd.Timedelta('10ms')), dflist)
    ddf.drop(columns=['stamp'], inplace=True)
    print( ddf.head() )
    return ddf

def save_dataframe(df, device):
    today = date.today().isoformat()
    df.to_csv('%s_%s.csv'%(today,device),index_label='idx')

async def my_app(con):

    initial_setting = None
    # Setup context
    async with acsys.dpm.DPMContext(con) as dpm:
        # Check kerberos credentials and enable settings
        #await dpm.enable_settings(role='linac_daily_rf_tuning')
		await dpm.enable_settings(role='testing')

        # Add acquisition requests
        await dpm.add_entries(list(enumerate(request_list)))

        # Start acquisition
        await dpm.start()

        # Process incoming data
        async for evt_res in dpm:

            if evt_res.isReadingFor(0):
                print(f'Device 0 {evt_res}')
                data.append({'tag':evt_res.tag, 'stamp':evt_res.stamp,'data': evt_res.data,'name':evt_res.meta['name'],'di':evt_res.meta['di']})
                # Calculate new setting
                new_setting = evt_res.data - step

                # Cache the initial setting
                if initial_setting is None:
                    initial_setting = evt_res.data
                    # Override the new_setting to star the scan
                    new_setting = maxval
                # First reading is already cached
                else:
                    # Exit condition when the min value is reached
                    if evt_res.data <= minval:
                        print(f'Min value reached')
                        break

                print(f'{new_setting=}')
                await dpm.apply_settings([(0, new_setting)])

            elif evt_res.isReadingFor(*list(range(1, len(request_list)))):
                print(f'Other devices: {evt_res}')
                data.append({'tag':evt_res.tag, 'stamp':evt_res.stamp,'data': evt_res.data,'name':evt_res.meta['name']})
                
            else:
                print(f'Status: {evt_res}')

        if initial_setting:
            print(f'Re-Setting to {initial_setting}')
            await dpm.apply_settings([(0, initial_setting)])

    # Save queries in dataframe
    df =fill_dataframe(data)
    save_dataframe(df,device)
                
acsys.run_client(my_app)
