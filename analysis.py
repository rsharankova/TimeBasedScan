import gssapi
import time
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools
import scipy.fft as spft
from sklearn.linear_model import LinearRegression


### Kerberos
def get_ticket(username,password):

    server_name = gssapi.Name('krbtgt/FNAL.GOV@')
    
    user = gssapi.Name(base=username, name_type=gssapi.NameType.user)
    bpass = password.encode('utf-8')
    try:
        creds = gssapi.raw.acquire_cred_with_password(user, bpass, usage='initiate')
        #creds = creds.creds
        #context = gssapi.SecurityContext(name=server_name, creds=creds, usage='initiate')
    except AttributeError:
        print("AttributeError")
    except gssapi.exceptions.GSSError as er:
        print(er)


    return None

#### Analysis
def fetch_data(file,datacols,cuts,setdevs):
    dataset = pd.read_csv(file)
    dataset.columns = dataset.columns.str.replace("[()]", "_",regex=True)
    cols = list(dataset.filter(regex='|'.join(datacols)))

    # keep (R) and remove (S) for driving devices
    setdevs = ['L:%s_'%d for d in setdevs]
    cols = [col for col in cols if col not in setdevs]
    subset = dataset.loc[:,cols]
    subset.columns = subset.columns.str.replace("_R_|_S_", "",regex=True)
    subset.drop(list(subset.filter(regex=r'\.1|Time|step|iter|stamp')),axis=1, inplace=True)

    # apply cuts
    if len(cuts)>0:
        subset.query(cuts,inplace=True)

    subset.dropna(inplace=True)

    return subset

def load_BPMphase_data_multi(cavs,files,dropdevs,scan=True):
    dfs = []
    for i, file in enumerate(files):
        if scan:
            # 26/02/2024: inverse the logic, keep the read and remove the set
            df = fetch_data(file,cavs+['BF','BPM','SQ'],'',['%s_S'%cav[2:] for cav in cavs])
        else:
            df = fetch_data(file,cavs+['BF','BPM','SQ'],'',[])
        try:
            df = df.drop(list(df.filter(regex=r'20|B:|SS|SQT')), axis=1)
            df = df.drop(list(df.filter(regex=r'|'.join(dropdevs))),axis=1)
        except:
            continue

        #deal with phase jumps at +-180
        for col in df.columns:
            if abs(df[col].min()-df[col].max())>350:
                #df[col] = np.unwrap(df[col],period=360)
                if np.sign(df[col]).mean() <0:
                    df[col] = df[col].apply(lambda x : x if x < 0 else x -360)
                else:
                    df[col] = df[col].apply(lambda x : x if x > 0 else x +360)


        dfs.append(df)

    return dfs

def fft_array(array):
    fft_vals = spft.fft(array)
    N = len(array)
    freq = spft.fftfreq(N)
    return [freq, fft_vals]


def apply_FFT(ddfs):                                                                                                                                                                                                                                                                    
    raw_ffts=[]

    for j in range(len(ddfs)):
        fft_df = ddfs[j].copy(deep=True)

        for current_device in ddfs[j].columns:
            freq, fft_vals = fft_array(list(ddfs[j][current_device]))

            fft_df[current_device] = np.abs(fft_vals)
            fft_df['freq_%s'%current_device] = freq
        
        raw_ffts.append(fft_df)#.apply(np.real))
        
    return raw_ffts


def apply_FFT_filter(df,cavs,BPM_list,tolerance=0.0005):                                                                                                                                                                                                                                                                    
    ffts = []

    BPMs = list(set(BPM_list).intersection(set(list(df.columns))))
    for j in range(len(cavs)):
        current_df = df.copy(deep = True)
        freq_driving, fft_vals_driving = fft_array(list(df[cavs[j]]))
        filter_freqs = freq_driving[np.argmax(np.abs(fft_vals_driving))]
        for current_device in BPMs:
            freq, fft_vals = fft_array(list(df[current_device]))
            fft_vals2 = np.zeros_like(fft_vals)

            for i in range(len(fft_vals)):
                if np.any(np.abs(np.abs(freq[i]) - filter_freqs) < tolerance):
                    fft_vals2[i] = fft_vals[i]
                else:
                    fft_vals2[i] = 0

            current_df[current_device] = spft.ifft(fft_vals2)
        ffts.append(current_df.apply(np.real))

    return ffts
            
def plot_fft(fft_data,devices,npt,nperiods):
    for dev in devices:
        plt.stem(fft_data['freq_%s'%dev]*npt*nperiods,fft_data['%s'%dev]*2/(npt*nperiods),label='%s'%dev[2:],linefmt='-',markerfmt="o", basefmt="-")

    plt.xlim(20,100)
    plt.ylim(0,5)
    plt.xlabel('Frequency')
    plt.ylabel('Amplitude (deg)')
    plt.grid()
    plt.legend(loc='upper right')
    plt.show()


