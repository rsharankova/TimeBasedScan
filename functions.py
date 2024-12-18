import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools

import time
import subprocess
import gssapi

import tkinter as tk
from tkinter import messagebox

import scipy.fft as spft
from sklearn.linear_model import LinearRegression


#### LOAD DATA ####
def fetch_data(file,datacols,cuts,setdevs):

    dataset = pd.read_csv(file)
    dataset.columns = dataset.columns.str.replace("[()]", "_",regex=True)

    cols = list(dataset.filter(regex='|'.join(datacols)))
    
    # for set points, keep _S_ and drop _R_ if available 
    # 26/02/2024: inverse the logic, keep the read and remove the set                                                                                                                                                                                                                                   
    setdevs = ['L:%s_'%d for d in setdevs]
    cols = [col for col in cols if col not in setdevs]

    subset = dataset.loc[:,cols]
    subset.columns = subset.columns.str.replace("_R_|_S_", "",regex=True)
    subset.drop(list(subset.filter(regex=r'\.1|Time|step|iter|stamp')),axis=1, inplace=True)

    # apply data quality cuts                                                                                                                                                                                                                                                              
    if len(cuts)>0:
        subset.query(cuts,inplace=True)

    subset.dropna(inplace=True)
    subset.head()
    
    return subset

def load_BPMphase_data_single(cavs,files,dropdevs,scan=True):
    dfs = []
    for i, file in enumerate(files):
        if scan:
            #26/02/2024: inverse the logic, keep the read and remove the set
            df = fetch_data(file,cavs+['BF','BPM','SQ'],'',['%s_S'%cavs[i][2:]])
        else:
            df = fetch_data(file,cavs+['BF','BPM','SQ'],'',[])
        try:
            df = df.drop(list(df.filter(regex=r'20|B:|SS|SQT')), axis=1)
            df = df.drop(list(df.filter(regex=r'|'.join(dropdevs))),axis=1)
        except:
            pass
            #print('No devices to drop')
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
###

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
            pass
            #print('No devices to drop')

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

###
def remove_noisy_bpm(dataset):
    json_file = open('./sensor_positions.json')
    if json_file:
        BPM_positions = json.load(json_file)
        
    BPM_list = list(BPM_positions.keys())
    devices_to_drop = []
    
    for bpm in BPM_list:
        if bpm in list(dataset.columns):
            if np.std(dataset[bpm])==0 or np.std(dataset[bpm])>80:
                devices_to_drop.append(bpm)

    
    for device in devices_to_drop:
        try:
            del BPM_positions[device]
        except:
            continue

    return BPM_positions
    
    
####
### FFT ###
def fft_array(array):
    fft_vals = spft.fft(array)
    N = len(array)
    freq = spft.fftfreq(N)
    return [freq, fft_vals]

####
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

###
def apply_FFT_filter(df,cavs,BPM_list,tolerance=0.0005):                                                                                                                                                                                                                                                                    
    ddfs2 = []

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
        ddfs2.append(current_df.apply(np.real))

    return ddfs2

####
# unfinished
def calc_errors(fft_data,devices,npt,nperiods):
    for dev in devices:
        idx_noise = np.where((fft_data['freq_%s'%dev]>0.1) & (fft_data['freq_%s'%dev]<0.2))
        noise = np.mean(fft_data[dev].iloc[idx_noise]).values[0]

#####
def calc_response_matrix(dfs,cavs):
    final_response_matrix = []

    for j in range(len(dfs)):
        slice_pos = np.argmax(dfs[j][cavs[j]])                         
        norm_val = dfs[j][cavs[j]][slice_pos]
    
        final_response_matrix.append(dfs[j].iloc[slice_pos]/norm_val)
        
    return final_response_matrix

#####
####  FITTING ###                                                                                                                                                                                                                                           
def linear_fit_to_basis(trajectory, b_vec_list, noise = None):
    X = np.column_stack(b_vec_list)

    if noise is not None:
        model = LinearRegression(fit_intercept=False)
        model.fit(X, trajectory, sample_weight = 1/noise)
    else:
        model = LinearRegression(fit_intercept=False)
        model.fit(X, trajectory)

    return model.coef_

def matrix_inversion(trajectory,response_df):
    pseudoinverse = pd.DataFrame(np.linalg.pinv(response_df,rcond=1e-20),columns=response_df.index, index=response_df.columns)
    coef = (pseudoinverse.dot(trajectory)).to_numpy(dtype=np.float64)
    #coef = list(itertools.chain(*coef))

    return coef
    
###  BASIS SELECTION ###
def select_basis(final_response_matrix,basis_choice_override=None):
                                                                                                                          
    possible_basis = list(itertools.combinations(range(len(final_response_matrix)), 2))
    e_normed_response = [response_matrix/np.linalg.norm(response_matrix) for response_matrix in final_response_matrix]
    overlaps = [np.dot(e_normed_response[b[0]], e_normed_response[b[1]]) for b in possible_basis]

    basis_choice = possible_basis[np.argmin(np.abs(overlaps))]

    if basis_choice_override != None: basis_choice = basis_choice_override
        
    return basis_choice


####  DIAGNOSTICS
def plot_fft(ax,fft_data,devices,npt,nperiods):
    for dev in devices:
        ax.stem(fft_data['freq_%s'%dev]*npt*nperiods,fft_data['%s'%dev]*2/(npt*nperiods),label='%s'%dev[2:],markerfmt='o')
        #markerline, stemlines, baseline = ax.stem(fft_data['freq_%s'%dev]*npt*nperiods,fft_data['%s'%dev]*2/(npt*nperiods),label='%s'%dev[2:],markerfmt='.')
        #plt.set(stemlines, 'color', plt.get(markerline,'color'))
        #plt.set(baseline, 'color', plt.get(markerline,'color'))
        #plt.set(stemlines, 'linestyle', 'dotted')

    ax.set_xlim(0,100)
    #ax.ylim(0,6)
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Amplitude (deg)')
    ax.grid()
    ax.legend(loc='upper right')

###
def show_basis_choices(response_matrix):
    possible_basis = list(itertools.combinations(range(len(response_matrix)), 2))
    e_normed_response = [rm/np.linalg.norm(rm) for rm in response_matrix]
    overlaps = [np.dot(e_normed_response[b[0]], e_normed_response[b[1]]) for b in possible_basis]

    for i in range(len(possible_basis)): print(possible_basis[i], overlaps[i])
    return None

####
def plot_fit_traj(ax,cavs,trajectory, basis, response_matrix,coefs,BPM_data,targetlbl=None):
    if targetlbl:
        target = str(targetlbl)
    else:
        target='Target trajectory'
        
    dist_data = list(BPM_data.values())
    BPM_list = list(BPM_data.keys())
    
    ax.plot(dist_data,trajectory.loc[BPM_list], label = target)# + str(target_index))
    ax.plot(dist_data,coefs[0] * response_matrix.iloc[:,basis[0]].loc[BPM_list] + coefs[1] * response_matrix.iloc[:,basis[1]].loc[BPM_list], label ='1' )#"%.3f * {cavs[basis[0]]} + %.3f * {cavs[basis[1]]}"%tuple(coefs))
    ax.set_ylabel(r"$ \Delta \phi_{BPM}$ (deg)")
    #plt.xticks(rotation = 90)
    ax.set_xlabel("Distance, m")
    ax.legend(loc='upper right')
    return None

####
def plot_basis_vectors(ax,response_matrix,dist_data,cavs,show):
    cavnames = ['Buncher','Tank 1','Tank 2','Tank 3','Tank 4','Tank 5','RFQ']
    e_normed_response = [response_matrix/np.linalg.norm(response_matrix) for response_matrix in response_matrix]
    for index in show:
        #plt.plot(dist_data, e_normed_response[index][:], label = '%s'%cavs[index])
        ax.plot(dist_data, response_matrix[index][:], label = '%s'%cavnames[index])
    ax.legend(loc='upper right',ncol=2)
    ax.set_xlabel("Distance, m")
    ax.set_ylabel(r"$ \Delta \phi_{BPM}$ (deg)")
    #plt.ylim(-0.45, 0.45)
    ax.set_ylim(-3.5,3.5)
    ax.grid()
    #ax.show()

    return None

##### CONTROLS ####
def get_ticket(username,password):

    server_name = gssapi.Name('krbtgt/FNAL.GOV@')
    
    user = gssapi.Name(base=username, name_type=gssapi.NameType.user)
    bpass = password.encode('utf-8')
    try:
        creds = gssapi.raw.acquire_cred_with_password(user, bpass, usage='initiate')
        creds = creds.creds
        #context = gssapi.SecurityContext(name=server_name, creds=creds, usage='initiate')
    except AttributeError:
        print("AttributeError")
    except gssapi.exceptions.GSSError as er:
        print(er)
        
    return None
###

# Function to validate the login
def validate_login(userid,password):
    #userid = username_entry.get()
    #password = password_entry.get()

    # Check for ticket
    has_ticket = subprocess.call(['klist', '-s'])
    if not has_ticket:
        subprocess.call(['kdestroy'])
        
    get_ticket(userid,password)
    has_ticket = subprocess.call(['klist', '-s'])
    if not has_ticket:
        messagebox.showinfo(message="Login Successful")
    else:
        messagebox.showerror(message="Login Failed")
    #parent.destroy()

####
def login_window():
    # Create the main window
    parent = tk.Tk()
    parent.title("Login Form")

    # Create and place the username label and entry
    username_label = tk.Label(parent, text="Userid:")
    username_label.pack()

    username_entry = tk.Entry(parent)
    username_entry.pack()

    # Create and place the password label and entry
    password_label = tk.Label(parent, text="Password:")
    password_label.pack()

    password_entry = tk.Entry(parent, show="*")  # Show asterisks for password
    password_entry.pack()

    # Create and place the login button
    #login_button = tk.Button(parent, text="Login", command=validate_login)
    login_button = tk.Button(parent, text="Login",command= lambda: validate_login(username_entry.get(),password_entry.get()))
    login_button.pack()

    # Start the Tkinter event loop
    parent.mainloop()

